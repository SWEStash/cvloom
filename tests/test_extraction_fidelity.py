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

# Work entries in the fixture; enough that every template runs to several pages.
_ENTRIES = 16


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
    # entry on a page is the one a right-aligned date can corrupt. The page count
    # is asserted in `test_the_fixture_spans_several_pages`, because an earlier
    # version of this fixture fitted on one page and silently tested nothing.
    work = []
    for i in range(_ENTRIES):
        bullets = "\n".join(
            f'    - "BULLET{i:02d}X{j} a line of text long enough to occupy most of a row."'
            for j in range((i % 4) + 2)
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


@pytest.mark.parametrize("template", _TEMPLATES)
def test_the_fixture_spans_several_pages(project: Path, template: str) -> None:
    """The page break is the interesting case, so the fixture has to reach one.

    Counted off the built PDF, not `BuildResult.pages` — that one is a word-count
    estimate and would let a single-page fixture pass.
    """
    pypdf = pytest.importorskip("pypdf")
    pages = len(pypdf.PdfReader(str(_build(project, template))).pages)
    assert pages >= 2, f"{template} fits on {pages} page(s); fixture too small"


@pytest.mark.parametrize("template", _TEMPLATES + ["cv/sidebar-compact"])
def test_headings_reach_the_structure_tree(template: str, project: Path) -> None:
    """Section titles and entry titles must be real headings, not styled divs.

    Headings are the anchors a parser segments a CV on. A `div.section-title`
    looks identical on the page and arrives in the structure tree as an anonymous
    `/Div`, which is worth nothing to anything reading the document semantically.
    """
    pypdf = pytest.importorskip("pypdf")
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

    reader = pypdf.PdfReader(str(_build(project, template)))
    kinds: set[str] = set()
    seen: set[int] = set()

    def walk(node: object) -> None:
        if isinstance(node, IndirectObject):
            if node.idnum in seen:
                return
            seen.add(node.idnum)
            node = node.get_object()
        if isinstance(node, (ArrayObject, list)):
            for kid in node:
                walk(kid)
        elif isinstance(node, DictionaryObject):
            if node.get("/S"):
                kinds.add(str(node["/S"]))
            if node.get("/K") is not None:
                walk(node["/K"])

    walk(reader.trailer["/Root"]["/StructTreeRoot"])
    for want in ("/H1", "/H2", "/H3"):
        assert want in kinds, f"{template} emits no {want}; found {sorted(kinds)}"


@pytest.mark.parametrize("template", _TEMPLATES)
def test_built_pdfs_carry_a_structure_tree(project: Path, template: str) -> None:
    """Tagged output is what makes the right-aligned date's reading order explicit."""
    pypdf = pytest.importorskip("pypdf")
    root = pypdf.PdfReader(str(_build(project, template))).trailer["/Root"]
    assert "/StructTreeRoot" in root, f"{template} built an untagged PDF"
    assert bool(root.get("/MarkInfo", {}).get("/Marked")), f"{template} is not marked"


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

    The date runs inline on the entry's meta line. This is the test that says it
    reads back inside its own entry in every reading order, including across page
    breaks, whatever the user's bullets look like. See docs/dev/architecture.md.
    """
    text = _text(project, template, engine)
    tokens = re.findall(r"TITLE\d\d|COMPANY\d\d|BULLET\d\dX\d|20\d\d-\d\d [-–] 20\d\d-\d\d", text)
    for i in range(_ENTRIES):
        # An entry's header region runs from its first identifying token to its own
        # first bullet. Requiring the date to fall *between* the title and the
        # company would assert a house style instead: engines legitimately order
        # those three differently, and `cv/executive-dark` leads with the company.
        # The defect being guarded is the date escaping the header region — emitted
        # after its own bullets, welded to whatever entry came next.
        anchors = [k for k, t in enumerate(tokens) if t in {f"TITLE{i:02d}", f"COMPANY{i:02d}"}]
        assert len(anchors) == 2, f"entry {i:02d} incomplete under {engine}: {anchors}"
        start = min(anchors)
        bullets = [k for k, t in enumerate(tokens) if t.startswith(f"BULLET{i:02d}")]
        end = min((k for k in bullets if k > start), default=len(tokens))
        header = tokens[start:end]
        # Templates differ on the range separator, hyphen or en dash.
        want = re.compile(rf"20{10 + i}-01 [-\u2013] 20{11 + i}-02")
        assert any(want.fullmatch(t) for t in header), (
            f"entry {i:02d}: date left its header under {engine}; header={header}"
        )
        assert max(anchors) < end, f"entry {i:02d}: a bullet splits its header under {engine}"


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
    missing = [f"COMPANY{i:02d}" for i in range(_ENTRIES) if f"COMPANY{i:02d}" not in text]
    missing += [
        f"BULLET{i:02d}X{j}"
        for i in range(_ENTRIES)
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
