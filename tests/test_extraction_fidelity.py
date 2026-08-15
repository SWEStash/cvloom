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

# The contact line, in distinctive values that can be located in an extracted
# page. The fixture carried `links: []` and a line short enough never to wrap
# until contact icons were added, so nothing here measured the contact line at
# all — see `test_contact_fields_survive_extraction_intact`.
_LINKS = ("linkhandlealpha", "linkhandlebravo", "linkhandlecharlie")
# Templates whose contact fields all read back before the first work entry. Once
# `cv/executive-dark` carries icons, poppler emits one of them after `COMPANY00`
# instead. Dropping the flex row from its header does not fix that — it only
# changes which field moves — so it is the gap each icon opens, not the layout.
# The values stay whole, which is the bar; position is asserted where it holds.
_HEADER_LOCAL = [t for t in _TEMPLATES if t != "cv/executive-dark"]
_EMAIL = "firstname.lastname@example.com"
_PHONE = "+1 (555) 000-0000"
_LOCATION = "Someplace City, Some Country"


def _write_project(root: Path) -> None:
    (root / "data").mkdir()
    (root / "private").mkdir()
    (root / "profiles").mkdir()
    (root / "private" / "contact.yaml").write_text(
        f'name: {_NAME}\nemail: "{_EMAIL}"\nphone: "{_PHONE}"\nlocation: "{_LOCATION}"\n'
    )
    (root / "data" / "basics.yaml").write_text(
        f'headline: "{_HEADLINE}"\n'
        'summary: "A summary sentence of adequate length here."\n'
        "links:\n"
        f'  - {{label: "LinkedIn", url: "https://linkedin.com/in/{_LINKS[0]}"}}\n'
        f'  - {{label: "GitHub", url: "https://github.com/{_LINKS[1]}"}}\n'
        f'  - {{label: "Site", url: "https://{_LINKS[2]}.dev"}}\n'
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


def _struct_kinds(pdf_path: Path) -> list[str]:
    """Every `/S` in the structure tree, in the order the tree is walked.

    Ordered rather than a set because two callers want different things from it:
    one asks which kinds exist, the other compares two whole trees for equality,
    and a set would let a reordered tree pass as unchanged.
    """
    pypdf = pytest.importorskip("pypdf")
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

    kinds: list[str] = []
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
                kinds.append(str(node["/S"]))
            if node.get("/K") is not None:
                walk(node["/K"])

    walk(pypdf.PdfReader(str(pdf_path)).trailer["/Root"]["/StructTreeRoot"])
    return kinds


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
    kinds = set(_struct_kinds(_build(project, template)))
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
def test_contact_fields_survive_extraction_intact(
    project: Path, template: str, engine: str
) -> None:
    """Every contact field reads back whole, and inside the header.

    This is the line that contact icons are allowed to cost nothing against. Each
    icon opens ~1.25em of blank space, pdfminer and poppler read a gap that size as
    a box boundary, and the contact line therefore comes back as several boxes —
    sometimes in a different order than it was written. That is accepted: an ATS
    matches on the address, and grouping is not the address.

    What is *not* accepted is a field arriving broken. A gap wide enough to split a
    box is a gap wide enough to split a token, which is how `PAYPAL` became
    `P AYP AL` elsewhere in this suite — so each address is asserted as one
    uninterrupted substring, and asserted to land in the header rather than adrift
    in the work history. Order is deliberately not asserted.

    The fixture carried `links: []` until icons were added, so none of this was
    measured and a contact-line regression passed every engine in silence.
    """
    text = _text(project, template, engine)
    first_entry = text.index("COMPANY00")
    for field in (*_LINKS, _EMAIL, _PHONE, _LOCATION):
        assert field in text, f"{template}/{engine} lost or split {field!r}"
        if template in _HEADER_LOCAL:
            assert text.index(field) < first_entry, (
                f"{template}/{engine} put {field!r} outside the header"
            )


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


# A conformance variant is metadata. The claim this rests on is that declaring one
# changes nothing a parser reads — otherwise `pdf.variant` would be a parseability
# setting in disguise, and the docs say plainly that it is not.
_VARIANTS = ["pdf/ua-1", "pdf/a-2b"]


@pytest.mark.skipif(not _ENGINES, reason="no PDF text extractor installed")
@pytest.mark.parametrize("variant", _VARIANTS)
@pytest.mark.parametrize("template", _TEMPLATES)
def test_a_conformance_variant_changes_no_text_and_no_structure(
    project: Path, tmp_path_factory: pytest.TempPathFactory, template: str, variant: str
) -> None:
    """Declaring PDF/UA or PDF/A must not move a single glyph.

    This is the assertion `pdf.variant` is sold on. If a variant ever did change
    the text layer, the setting would silently be a parseability change and every
    template's measured rating would be conditional on it.
    """
    root = tmp_path_factory.mktemp("variant")
    _write_project(root)
    (root / "cvloom.yaml").write_text(f"pdf:\n  variant: {variant}\n")

    for engine in _ENGINES:
        assert _text(root, template, engine) == _text(project, template, engine), (
            f"{template}/{engine} extracts differently under {variant}"
        )
    assert _struct_kinds(_build(root, template)) == _struct_kinds(_build(project, template)), (
        f"{template} builds a different structure tree under {variant}"
    )


@pytest.mark.parametrize("variant,marker", [("pdf/ua-1", "pdfuaid"), ("pdf/a-2b", "pdfaid")])
def test_a_declared_variant_reaches_the_xmp_metadata(
    tmp_path_factory: pytest.TempPathFactory, variant: str, marker: str
) -> None:
    """The identifier is the whole point: without it nothing has been declared.

    Asserted on the raw XMP packet rather than through a conformance checker.
    veraPDF is what proves the document *is* conformant; this proves cvloom asked
    for it, which is the half that can regress from a change in this repo.
    """
    pypdf = pytest.importorskip("pypdf")
    root = tmp_path_factory.mktemp("xmp")
    _write_project(root)
    (root / "cvloom.yaml").write_text(f"pdf:\n  variant: {variant}\n")

    reader = pypdf.PdfReader(str(_build(root, "cv/ats-clean")))
    assert reader.xmp_metadata is not None, f"{variant} produced no XMP packet"
    packet = reader.xmp_metadata.stream.get_data().decode("utf-8", "replace")
    assert marker in packet, f"{variant} left no {marker} identifier in the XMP"


def test_no_variant_declares_no_conformance(project: Path) -> None:
    """The default must stay a plain tagged PDF, claiming nothing."""
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(str(_build(project, "cv/ats-clean")))
    packet = (
        reader.xmp_metadata.stream.get_data().decode("utf-8", "replace")
        if reader.xmp_metadata is not None
        else ""
    )
    assert "pdfuaid" not in packet and "pdfaid" not in packet, (
        "a default build claims a conformance level nobody asked for"
    )


def _paints_timeline_rule(pdf_path: Path) -> bool:
    """True when page 1 fills with `--timeline-line` (#d1d5db) at least once."""
    pypdf = pytest.importorskip("pypdf")
    want = tuple(v / 255 for v in (0xD1, 0xD5, 0xDB))
    page = pypdf.PdfReader(str(pdf_path)).pages[0]
    stream = page.get_contents().get_data().decode("latin-1")
    for match in re.finditer(r"([\d.]+) ([\d.]+) ([\d.]+) rg", stream):
        rgb = tuple(float(g) for g in match.groups())
        if all(abs(a - b) < 0.02 for a, b in zip(rgb, want)):
            return True
    return False


def _shading_types(pdf_path: Path) -> set[int]:
    """Return the PDF ShadingType numbers used anywhere in *pdf_path*.

    2 is axial (a linear gradient), 3 is radial.
    """
    pypdf = pytest.importorskip("pypdf")
    found: set[int] = set()
    for page in pypdf.PdfReader(str(pdf_path)).pages:
        for xobj in page["/Resources"].get("/XObject", {}).values():  # type: ignore[union-attr]
            shadings = xobj.get_object().get("/Resources", {}).get("/Shading", {})
            for shading in shadings.values():
                kind = shading.get_object().get("/ShadingType")
                if kind is not None:
                    found.add(int(kind))
    return found


def test_timeline_rule_is_a_solid_fill_not_a_gradient(project: Path) -> None:
    """`cv/timeline-clean`'s vertical rule must not be drawn as a linear gradient.

    Drawn as a background layer it reached the PDF as a full-page *axial* shading
    inside a transparency group, whose visible 2px was nothing but alpha in the
    colour function. Poppler resolves that, so the line was there in pdftoppm and
    in the fidelity suite — and absent in the viewers people actually open the file
    in, which rasterize the soft mask too coarsely for a 2px feature to survive.

    A border is emitted as a plain filled rectangle, which has no such failure mode.
    The dots are still radial shadings (type 3): an opaque circle survives a coarse
    mask where a hairline does not.
    """
    pdf = _build(project, "cv/timeline-clean")
    types = _shading_types(pdf)
    assert 2 not in types, (
        "cv/timeline-clean emits an axial shading — the rule is a gradient again, "
        "and will not render in every PDF viewer"
    )
    assert _paints_timeline_rule(pdf), (
        "cv/timeline-clean paints no rule at all. A rule that is simply absent also "
        "emits no axial shading, so the assertion above passes on a blank page — an "
        "unterminated CSS comment once swallowed the `border-left` and this test "
        "stayed green."
    )
