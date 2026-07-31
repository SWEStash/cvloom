"""End-to-end checks on what a PDF's text layer actually contains.

Every defect this file guards against was invisible in the rendered page and in
the HTML, and each was found only by selecting the text: a date emitted after its
own entry's bullets and welded to the next entry's title, a name welded to the
headline, a skill category welded to its first skill. Unit tests over the HTML
cannot see any of them, because the HTML was never wrong.

So these build real PDFs and read them back with every extractor installed.
They are slower than the rest of the suite and they are worth it.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pytest

from cvloom import builder
from cvloom import extract as extract_mod

pytest.importorskip("weasyprint")

_ENGINES = extract_mod.available_engines()

# The five single-column templates. `cv/sidebar-compact` is excluded on purpose:
# it is rated unsafe because its two columns interleave, and asserting otherwise
# would be asserting a bug is absent when it is documented as present.
_TEMPLATES = [
    "cv/ats-clean",
    "cv/academic",
    "cv/modern-single",
    "cv/timeline-clean",
    "cv/executive-dark",
]

_NAME = "Testname Uniquesurname"
_HEADLINE = "Headline Engineer"


def _write_project(root: Path) -> None:
    (root / "data").mkdir()
    (root / "private").mkdir()
    (root / "profiles").mkdir()
    (root / "private" / "contact.yaml").write_text(
        f'name: {_NAME}\nemail: "t@example.com"\nlocation: "Somewhere"\n'
    )
    (root / "data" / "basics.yaml").write_text(
        f'headline: "{_HEADLINE}"\n'
        'summary: "A summary sentence of adequate length here."\nlinks: []\n'
    )
    # Enough entries, with enough bullets, to run past a page break — the last
    # entry on a page is the one a right-aligned date used to corrupt.
    work = []
    for i in range(9):
        bullets = "\n".join(
            f'    - "BULLET{i:02d}X{j} a line of text long enough to occupy most of a row."'
            for j in range((i % 4) + 1)
        )
        work.append(
            f'- company: "COMPANY{i:02d}"\n'
            f'  title: "TITLE{i:02d} Engineer"\n'
            f'  location: "Remote"\n'
            f'  start_date: "20{10 + i}-01"\n'
            f'  end_date: "20{11 + i}-02"\n'
            f"  highlights:\n{bullets}\n"
        )
    (root / "data" / "work.yaml").write_text("".join(work))
    (root / "data" / "education.yaml").write_text(
        '- institution: "SCHOOL00"\n  degree: "DEGREE00"\n  field: "CS"\n'
        '  start_date: "2004"\n  end_date: "2008"\n'
    )
    # Mixed label widths: a label that fills its column used to weld to its first
    # value, which a short label never did.
    (root / "data" / "skills.yaml").write_text(
        '- category: "NET"\n  items: ["SKILLA0", "SKILLA1"]\n'
        '- category: "AVeryLongCategoryLabelHere"\n  items: ["SKILLB0", "SKILLB1"]\n'
    )


@functools.cache
def _build(root: Path, template: str) -> Path:
    """Build once per (project, template).

    Every test here reads the same PDF through a different engine, and rendering is
    the expensive part — without this the file rebuilt the same document 75 times.
    """
    slug = template.replace("/", "-")
    (root / "profiles" / f"{slug}.yaml").write_text(
        f"template: {template}\noutput_filename: {slug}\n"
    )
    result = builder.build_project(root, output_dir=root / "dist", profile_name=slug, public=False)
    assert result.pdf_path is not None
    return result.pdf_path


@functools.cache
def _text(root: Path, template: str, engine: str) -> str:
    return extract_mod.extract(_build(root, template), engine).text


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("fidelity")
    _write_project(root)
    return root


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_name_is_not_welded_to_the_headline(project: Path, template: str, engine: str) -> None:
    """The worst field on the page to corrupt, and it was corrupted.

    pypdf decides where a line ends from the vertical delta between text runs; the
    2px under the name was below its threshold, so every template emitted
    "Testname UniquesurnameHeadline Engineer" as one token.
    """
    text = _text(project, template, engine)
    assert _NAME in text
    assert f"{_NAME}{_HEADLINE}" not in text


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_every_date_stays_with_its_own_entry(project: Path, template: str, engine: str) -> None:
    """No date may be emitted after its entry's bullets, or welded to anything.

    Right-aligning the date made it a text column, and poppler flushes a column
    when the *page* ends: the last entry on each page had its date land after its
    own bullets, fused to the next entry's title.
    """
    text = _text(project, template, engine)
    tokens = re.findall(
        r"TITLE\d\d|COMPANY\d\d|BULLET\d\dX\d|20\d\d-\d\d [-\u2013] 20\d\d-\d\d", text
    )
    for i in range(9):
        # Templates order the header differently — `cv/executive-dark` leads with the
        # company, the rest with the title — so the assertion is that the entry's
        # three identifying fields form one contiguous run, in whatever order, with
        # no bullet in between. That is what "the date stayed with its entry" means
        # independently of the design.
        want = {f"TITLE{i:02d}", f"COMPANY{i:02d}"}
        positions = [k for k, t in enumerate(tokens) if t in want]
        assert len(positions) == 2, f"entry {i:02d} incomplete under {engine}: {positions}"
        lo, hi = min(positions), max(positions)
        window = tokens[lo : hi + 1]
        dates = [t for t in window if re.fullmatch(r"20\d\d-\d\d [-\u2013] 20\d\d-\d\d", t)]
        bullets = [t for t in window if t.startswith("BULLET")]
        assert dates, f"entry {i:02d}: no date beside it under {engine}; window={window}"
        assert not bullets, f"entry {i:02d}: bullet inside its header run under {engine}"


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_nothing_is_welded_to_a_date(project: Path, template: str, engine: str) -> None:
    text = _text(project, template, engine)
    welded = re.findall(
        r"[A-Za-z]20\d\d-\d\d - 20\d\d-\d\d|20\d\d-\d\d - 20\d\d-\d\d[A-Za-z]", text
    )
    assert not welded, f"{template}/{engine}: {welded[:3]}"


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_skill_categories_do_not_weld_to_their_values(
    project: Path, template: str, engine: str
) -> None:
    """A label that fills its column had no character between it and its first value."""
    text = _text(project, template, engine)
    for label in ("NET", "AVeryLongCategoryLabelHere"):
        assert not re.search(rf"{label}SKILL", text), f"{template}/{engine}: {label} welded"


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_no_content_is_lost(project: Path, template: str, engine: str) -> None:
    text = _text(project, template, engine)
    missing = [f"COMPANY{i:02d}" for i in range(9) if f"COMPANY{i:02d}" not in text]
    missing += [
        f"BULLET{i:02d}X{j}"
        for i in range(9)
        for j in range((i % 4) + 1)
        if f"BULLET{i:02d}X{j}" not in text
    ]
    assert not missing, f"{template}/{engine} lost {missing[:4]}"


# Kerning is the subtlest of the lot: WeasyPrint emits a kerned pair as two
# positioned runs, and an extractor reads a big enough jump as a word break, so
# the space lands *inside* a word. "PAYPAL" came out "P AYP AL". These names are
# chosen for exactly the pairs that trigger it.
_KERN_TRAPS = ["PAYPAL", "AVATAR", "WAVE", "TAWNY", "VOLKS"]


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("template", _TEMPLATES)
@pytest.mark.parametrize("engine", _ENGINES)
def test_kern_pairs_do_not_split_words(
    tmp_path_factory: pytest.TempPathFactory, template: str, engine: str
) -> None:
    root = tmp_path_factory.mktemp("kern")
    _write_project(root)
    companies = "".join(
        f'- company: "{name}"\n  title: "Engineer"\n  start_date: "2020-01"\n'
        f'  end_date: "2021-01"\n  highlights:\n    - "Did the work described here plainly."\n'
        for name in _KERN_TRAPS
    )
    (root / "data" / "work.yaml").write_text(companies)
    text = _text(root, template, engine)
    split = [n for n in _KERN_TRAPS if n not in text]
    assert not split, f"{template}/{engine} split {split} across a kern pair"
