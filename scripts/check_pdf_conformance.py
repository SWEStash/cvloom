#!/usr/bin/env python
"""Build every template under every declared PDF variant and validate the result.

`cvloom.yaml`'s `pdf.variant` lets a project declare a conformance level. Writing
the metadata is not the same as meeting the standard, and the difference is
invisible from the file: a PDF that says `pdfaid:part=2` and fails validation
looks exactly like one that passes. Only a validator can tell them apart, so
every value the schema offers is checked here against one.

veraPDF is a Java CLI. It cannot be a dev dependency, so this runs in CI rather
than in the pytest suite — see the `conformance` job in
`.github/workflows/build.yml`. The half that *can* live in the suite does:
`tests/test_extraction_fidelity.py` asserts the identifier reaches the XMP and
that declaring a variant moves no glyph.

Run locally with an installed veraPDF:

    uv run python scripts/check_pdf_conformance.py --verapdf ~/verapdf/verapdf
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvloom import builder, renderer, schema  # noqa: E402

# veraPDF names its profiles by conformance level alone, so the config's variant
# string has to be mapped onto one. Two WeasyPrint variants are absent from the
# schema and so from this table, both because they were measured and failed:
# `pdf/a-4u`, which WeasyPrint writes with a `pdfaid:conformance` entry PDF/A-4
# forbids outside 4e and 4f, and `pdf/a-1b`, whose 2005 ban on transparency
# rules out `cv/timeline-clean`'s radial shadings and `cv/sidebar-compact`'s
# soft masks.
_FLAVOURS = {
    "pdf/ua-1": "ua1",
    "pdf/a-2b": "2b",
    "pdf/a-2u": "2u",
    "pdf/a-3b": "3b",
    "pdf/a-3u": "3u",
}


def _declared_variants() -> list[str]:
    """The variants `cvloom.yaml` accepts, read from the schema itself.

    Derived rather than listed so a variant added to the schema cannot ship
    without a conformance run behind it.
    """
    doc = json.loads((Path(schema.__file__).parent / "schemas" / "project-config.json").read_text())
    return list(doc["properties"]["pdf"]["properties"]["variant"]["enum"])


def _write_project(root: Path, variant: str) -> None:
    for name in ("data", "private", "profiles"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "cvloom.yaml").write_text(f"pdf:\n  variant: {variant}\n")
    (root / "private" / "contact.yaml").write_text(
        'name: "Jane Smith"\n'
        'email: "jane@example.com"\n'
        'phone: "+44 7700 900000"\n'
        'location: "Somewhere"\n'
    )
    # Links matter: they become PDF annotations, and PDF/A has its own rules
    # about those. A fixture without them would validate a document the templates
    # never actually produce.
    (root / "data" / "basics.yaml").write_text(
        'headline: "Engineer"\n'
        'summary: "A summary sentence of adequate length here."\n'
        "links:\n"
        '  - {label: "LinkedIn", url: "https://linkedin.com/in/janesmith"}\n'
        '  - {label: "GitHub", url: "https://github.com/janesmith"}\n'
        '  - {label: "Site", url: "https://example.com"}\n'
    )
    (root / "data" / "work.yaml").write_text(
        "".join(
            f'- company: "COMPANY{i:02d}"\n'
            f'  title: "TITLE{i:02d} Engineer"\n'
            f'  location: "Remote"\n'
            f'  start_date: "20{10 + i}-01"\n'
            f'  end_date: "20{11 + i}-02"\n'
            "  highlights:\n"
            f'    - "BULLET{i}A a line of text long enough to occupy most of a row."\n'
            f'    - "BULLET{i}B another line of text of a similar useful length."\n'
            for i in range(6)
        )
    )
    (root / "data" / "education.yaml").write_text(
        '- institution: "SCHOOL"\n  degree: "BSc"\n  field: "CS"\n'
        '  start_date: "2004"\n  end_date: "2008"\n'
    )
    (root / "data" / "skills.yaml").write_text(
        '- category: "CloudOps"\n  items: ["AWS", "Azure"]\n- category: "NET"\n  items: ["TCP"]\n'
    )


def _cv_templates() -> list[str]:
    """Every shipped CV template, including the ones rated caution or unsafe.

    An ATS rating is about text extraction and conformance is about the file
    format; a template being a poor choice for a portal says nothing about
    whether its PDF is well-formed, so all of them are validated.
    """
    return sorted(t for t in renderer.list_templates() if t.startswith("cv/"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verapdf", required=True, help="path to the veraPDF CLI")
    args = parser.parse_args()

    verapdf = Path(args.verapdf).expanduser()
    if not verapdf.exists():
        print(f"veraPDF not found at {verapdf}", file=sys.stderr)
        return 2

    templates = _cv_templates()
    failures: list[str] = []

    for variant in _declared_variants():
        flavour = _FLAVOURS.get(variant)
        if flavour is None:
            failures.append(f"{variant}: offered by the schema but mapped to no veraPDF flavour")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_project(root, variant)
            pdfs: list[Path] = []
            for template in templates:
                slug = template.replace("/", "-")
                (root / "profiles" / f"{slug}.yaml").write_text(
                    f"template: {template}\noutput_filename: {slug}\n"
                )
                result = builder.build_project(root, output_dir=root / "dist", profile_name=slug)
                assert result.pdf_path is not None
                pdfs.append(result.pdf_path)

            proc = subprocess.run(
                [str(verapdf), "--flavour", flavour, "--format", "text", *map(str, pdfs)],
                capture_output=True,
                text=True,
            )
            for line in proc.stdout.splitlines():
                status, _, path = line.partition(" ")
                if status == "PASS":
                    print(f"  PASS  {variant}  {Path(path.split()[0]).name}")
                else:
                    print(f"  FAIL  {variant}  {line}")
                    failures.append(f"{variant}: {line}")

    if failures:
        print(f"\n{len(failures)} conformance failure(s):", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(f"\nAll {len(templates)} templates conform under every declared variant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
