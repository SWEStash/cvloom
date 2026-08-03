"""Every template's declared ATS rating, checked against a measurement.

`templates_meta` states a rating per template. Nothing stopped that rating from
drifting away from what the templates actually do — the ratings were prose until
now, and prose does not fail a build.

The rule is mechanical:

* no engine finds a defect  -> safe
* some engines do, some do not -> caution
* every engine finds one    -> unsafe

so the rating can be derived rather than asserted, and the derived value compared
with the declared one. A template that quietly improves fails this test as loudly
as one that regresses, because a rating that is too pessimistic sends users to a
worse-looking CV for no reason.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cvloom import builder, templates_meta
from cvloom import extract as extract_mod

pytest.importorskip("weasyprint")

_ENGINES = extract_mod.available_engines()
_ENTRIES = 10
_NAME = "Testname Uniquesurname"
_HEADLINE = "Headline Engineer"
# Distinctive strings for content that lives outside the work history, so that
# content landing *inside* it is detectable.
_ELSEWHERE = ("SKILLONE", "SIDEMAIL", "SIDELOC")


def _write_project(root: Path) -> None:
    for name in ("data", "private", "profiles"):
        (root / name).mkdir()
    (root / "private" / "contact.yaml").write_text(
        f'name: {_NAME}\nemail: "SIDEMAIL@example.com"\nlocation: "SIDELOC"\n'
    )
    (root / "data" / "basics.yaml").write_text(
        f'headline: "{_HEADLINE}"\nsummary: "A summary sentence here."\nlinks: []\n'
    )
    (root / "data" / "skills.yaml").write_text(
        '- category: "SKILLCAT"\n  items: ["SKILLONE", "SKILLTWO"]\n'
        '- category: "AVeryLongCategoryLabelHere"\n  items: ["SKILLB0", "SKILLB1"]\n'
    )
    (root / "data" / "education.yaml").write_text(
        '- institution: "SCH"\n  degree: "DEG"\n  start_date: "2004"\n  end_date: "2008"\n'
    )
    # Short titles and short bullets: the worst case, because they leave the
    # widest empty bands for a column detector to find.
    (root / "data" / "work.yaml").write_text(
        "".join(
            f'- company: "CO{i:02d}"\n  title: "TITLE{i:02d}"\n  location: "Remote"\n'
            f'  start_date: "20{10 + i}-01"\n  end_date: "20{11 + i}-02"\n  highlights:\n'
            f'    - "BULLET{i:02d}X0 short line."\n    - "BULLET{i:02d}X1 short line."\n'
            for i in range(_ENTRIES)
        )
    )


def _defects(text: str) -> list[str]:
    """Every way this document is wrong when read by one engine."""
    found: list[str] = []
    flat = " ".join(text.split())
    tokens = re.findall(r"TITLE\d\d|CO\d\d|BULLET\d\dX\d|20\d\d-\d\d - 20\d\d-\d\d", text)

    for i in range(_ENTRIES):
        anchors = [k for k, t in enumerate(tokens) if t in {f"TITLE{i:02d}", f"CO{i:02d}"}]
        if len(anchors) != 2:
            found.append("entry-incomplete")
            break
        start = min(anchors)
        bullets = [k for k, t in enumerate(tokens) if t.startswith(f"BULLET{i:02d}")]
        end = min((k for k in bullets if k > start), default=len(tokens))
        want = re.compile(rf"20{10 + i}-01 - 20{11 + i}-02")
        if not any(want.fullmatch(t) for t in tokens[start:end]):
            found.append("date-left-entry")
            break

    first, last = flat.find("TITLE00"), flat.find(f"TITLE{_ENTRIES - 1:02d}")
    if first >= 0 and last > first:
        if any(first < flat.find(m) < last for m in _ELSEWHERE if flat.find(m) >= 0):
            found.append("columns-interleave")

    if f"{_NAME}{_HEADLINE}" in flat:
        found.append("name-welded")
    if "SKILLCATSKILLONE" in flat or "AVeryLongCategoryLabelHereSKILLB0" in flat:
        found.append("skills-welded")
    if any(f"CO{i:02d}" not in flat for i in range(_ENTRIES)):
        found.append("content-lost")
    return found


def _measured_rating(pdf: Path) -> tuple[str, dict[str, list[str]]]:
    per_engine = {e: _defects(extract_mod.extract(pdf, e).text) for e in _ENGINES}
    flagged = sum(1 for defects in per_engine.values() if defects)
    if flagged == 0:
        rating = templates_meta.ATS_SAFE
    elif flagged == len(_ENGINES):
        rating = templates_meta.ATS_UNSAFE
    else:
        rating = templates_meta.ATS_CAUTION
    return rating, per_engine


@pytest.mark.skipif(len(_ENGINES) < 2, reason="rating needs more than one engine to disagree")
@pytest.mark.parametrize("template", sorted(templates_meta.TEMPLATES))
def test_declared_rating_matches_measurement(
    tmp_path_factory: pytest.TempPathFactory, template: str
) -> None:
    root = tmp_path_factory.mktemp("rating")
    _write_project(root)
    slug = template.replace("/", "-")
    (root / "profiles" / f"{slug}.yaml").write_text(f"template: {template}\n")
    result = builder.build_project(root, output_dir=root / "dist", profile_name=slug)
    assert result.pdf_path is not None

    measured, per_engine = _measured_rating(result.pdf_path)
    declared = templates_meta.TEMPLATES[template].ats
    assert measured == declared, (
        f"{template} is declared {declared!r} but measures {measured!r}. "
        f"Per engine: { {k: v for k, v in per_engine.items() if v} }"
    )


@pytest.mark.parametrize("template", sorted(templates_meta.TEMPLATES))
def test_only_safe_templates_omit_a_caveat(template: str) -> None:
    """Anything not rated safe has to say what is wrong with it, in prose."""
    info = templates_meta.TEMPLATES[template]
    if info.ats == templates_meta.ATS_SAFE:
        return
    assert info.caveat, f"{template} is rated {info.ats} with no caveat to show the user"
