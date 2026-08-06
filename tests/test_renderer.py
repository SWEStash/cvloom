"""Tests for template renderer."""

import re
from pathlib import Path

import pytest

from cvloom.renderer import render_template


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    t = tmp_path / "templates"
    (t / "cv").mkdir(parents=True)
    (t / "cv" / "test.html.j2").write_text("<html><body>{{ contact.name }}</body></html>")
    return t


def test_render_basic(templates_dir: Path) -> None:
    html = render_template(
        "cv/test",
        {"contact": {"name": "Jane Smith"}},
        templates_dir=templates_dir,
    )
    assert "Jane Smith" in html


def test_render_appends_extension(templates_dir: Path) -> None:
    html = render_template(
        "cv/test.html.j2",
        {"contact": {"name": "Jane"}},
        templates_dir=templates_dir,
    )
    assert "Jane" in html


def test_render_missing_template(templates_dir: Path) -> None:
    with pytest.raises(SystemExit):
        render_template("cv/nonexistent", {}, templates_dir=templates_dir)


# ── Built-in template render tests ──────────────────────────────────

_FULL_CONTEXT = {
    "contact": {
        "name": "Jane",
        "email": "jane@example.com",
        "phone": "+1 555",
        "location": "SF",
    },
    "basics": {
        "headline": "Engineer",
        "summary": "Great engineer.",
        "links": [
            {"label": "LinkedIn", "url": "https://linkedin.com/in/jane"},
            {"label": "GitHub", "url": "https://github.com/jane"},
        ],
    },
    "work": [
        {
            "company": "Acme",
            "title": "Engineer",
            "start_date": "2020-01",
            "end_date": "Present",
            "location": "Remote",
            "highlights": ["Built things."],
            "tags": ["python"],
        },
    ],
    "education": [
        {
            "institution": "Uni",
            "degree": "BSc",
            "field": "CS",
            "location": "Cambridge",
            "start_date": "2016",
            "end_date": "2020",
            "highlights": ["Dean's list."],
        },
    ],
    "skills": [{"category": "Languages", "items": ["Python", "Go"]}],
    "projects": [
        {
            "name": "proj",
            "description": "A project.",
            "tags": ["python"],
            "url": "https://example.com",
            "start_date": "2024-01",
            "highlights": ["Built it."],
        },
    ],
    "show": {"work": True, "education": True, "skills": True, "projects": True},
    "section_order": ["skills", "work", "education", "projects"],
    "job_context": {"company": "Acme", "role": "SWE", "hiring_manager": "Bob", "notes": ""},
    "profile": {},
    "public": False,
    "today": "March 22, 2026",
}


def test_render_brief_cover_letter() -> None:
    html = render_template("cover-letter/brief", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Bob" in html
    assert "Cover Letter" in html


def test_render_project_card() -> None:
    html = render_template("project-summary/card", _FULL_CONTEXT)
    assert "proj" in html
    assert "A project." in html


# ── Built-in CV template rendering ────────────────────────────────


def test_render_ats_single_template() -> None:
    html = render_template("cv/ats-clean", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Engineer" in html
    assert "Experience" in html or "Skills" in html
    assert "Acme" in html


def test_render_modern_single_template() -> None:
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Acme" in html
    assert "Languages" in html


def test_modern_single_prefixes_each_link_with_its_icon() -> None:
    """The icon is additive: the URL stays the anchor's visible text."""
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert 'class="contact-icon contact-icon-linkedin"' in html
    assert 'class="contact-icon contact-icon-github"' in html
    assert ">linkedin.com/in/jane</a>" in html
    assert ">github.com/jane</a>" in html


def test_modern_single_marks_every_contact_field() -> None:
    """Every field carries a mark; one bare value between marked ones reads as a bug."""
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert 'class="contact-icon contact-icon-envelope"' in html
    assert 'class="contact-icon contact-icon-phone"' in html
    assert 'class="contact-icon contact-icon-globe-americas"' in html
    assert "contact-icon-telephone" not in html
    assert "contact-icon-geo-alt" not in html


def test_modern_single_keeps_each_mark_welded_to_its_value() -> None:
    """A mark stranded at the end of a line, its value on the next, reads as a bug.

    `nowrap` on the field spans also keeps each value whole, which is the same
    property `test_contact_fields_survive_extraction_intact` asserts of the PDF:
    a URL wrapped mid-token comes back out of the text layer as two tokens.

    The line must still wrap *between* fields, so the rule goes on the span and not
    on `.contact-line`. Break opportunities live in the whitespace the template
    leaves between spans, which is outside them and so unaffected.
    """
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert re.search(r"\.contact-line span\s*\{[^}]*white-space:\s*nowrap", html)
    assert not re.search(r"\.contact-line\s*\{[^}]*white-space:\s*nowrap", html)
    # The separator must stay breakable, or the nowrap above makes the whole line
    # one box: it then overflows the page and poppler drops the last field.
    assert re.search(
        r"\.contact-line span \+ span::before\s*\{[^}]*white-space:\s*normal", html, re.S
    )


def test_modern_single_contact_icons_reach_the_printed_page() -> None:
    """They print deliberately: no media query may hide them.

    An earlier revision suppressed them in print because the gap each icon opens
    fragments the contact line under pdfminer and poppler. That cost grouping, not
    content — every address still extracts whole — so the marks now print, and
    `test_contact_fields_survive_extraction_intact` guards what actually matters.
    """
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    blocks = re.findall(r"@media print \{(.*?)\n\}", html, re.S)
    assert not any(re.search(r"\.contact-icon\s*\{[^}]*display:\s*none", b) for b in blocks)


_ICON_TEMPLATES = [
    "cv/modern-single",
    "cv/timeline-clean",
    "cv/executive-dark",
    "cv/sidebar-compact",
]


@pytest.mark.parametrize("template", _ICON_TEMPLATES)
def test_every_designed_template_marks_its_contact_fields(template: str) -> None:
    html = render_template(template, _FULL_CONTEXT)
    for mark in ("envelope", "phone", "globe-americas", "linkedin", "github"):
        assert f'contact-icon contact-icon-{mark}"' in html, f"{template} lacks {mark}"


@pytest.mark.parametrize("template", [t for t in _ICON_TEMPLATES if t != "cv/sidebar-compact"])
def test_single_line_contact_rows_weld_each_mark_to_its_value(template: str) -> None:
    """`sidebar-compact` is excluded: its values carry `word-break: break-all` for a
    190px column, which is the opposite instruction and wins where they disagree."""
    html = render_template(template, _FULL_CONTEXT)
    assert re.search(r"\.contact-(line|row) span\s*\{[^}]*white-space:\s*nowrap", html)


def test_executive_dark_lifts_its_contact_icons_off_the_band() -> None:
    """A literal fill, because WeasyPrint resolves no CSS against an inline SVG.

    `currentColor`, a `color` declaration on `.contact-icon` and a `fill`
    declaration were each measured and each ignored — the path paints black, which
    is invisible on the carbon band in the PDF while the HTML looked correct.

    The anchors need their own rule for a different reason: base scopes its
    header-link colour to `.contact-line`, and this header is a `.contact-row`.
    """
    html = render_template("cv/executive-dark", _FULL_CONTEXT)
    assert 'fill="#f4f5f6"' in html
    assert re.search(r"\.contact-row a\s*\{[^}]*color:\s*inherit", html)


def test_ats_clean_stays_free_of_icons() -> None:
    """The strictest template keeps a text-only contact line by design."""
    html = render_template("cv/ats-clean", _FULL_CONTEXT)
    assert "contact-icon" not in html


def test_render_academic_template() -> None:
    html = render_template("cv/academic", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Education" in html
    assert "Uni" in html


def test_render_sidebar_compact_template() -> None:
    html = render_template("cv/sidebar-compact", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Acme" in html
    assert "Languages" in html
    assert "sidebar" in html


def test_render_executive_dark_template() -> None:
    html = render_template("cv/executive-dark", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Engineer" in html
    assert "Acme" in html
    # The pack's flat "Summary", not the template's old "Executive Summary" —
    # that wording is a `templates_meta` suggestion a profile opts into now.
    assert "Summary" in html


def test_render_timeline_clean_template() -> None:
    html = render_template("cv/timeline-clean", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Acme" in html
    assert "timeline" in html


def test_render_standard_cover_letter() -> None:
    html = render_template("cover-letter/standard", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Bob" in html


def test_render_strict_undefined_error(templates_dir: Path) -> None:
    """StrictUndefined raises on missing variables."""
    (templates_dir / "cv" / "strict.html.j2").write_text("{{ nonexistent_var }}")
    with pytest.raises(Exception):  # UndefinedError
        render_template("cv/strict", {}, templates_dir=templates_dir)


# ── Font embedding tests ─────────────────────────────────────────────

_GOOGLE_FONTS_DOMAIN = "fonts.googleapis.com"


def test_timeline_clean_has_inter_font_link() -> None:
    html = render_template("cv/timeline-clean", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Inter" in html


def test_modern_single_has_lato_font_link() -> None:
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Lato" in html


def test_executive_dark_has_source_sans_font_link() -> None:
    html = render_template("cv/executive-dark", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Source+Sans+3" in html


def test_sidebar_compact_has_lato_font_link() -> None:
    html = render_template("cv/sidebar-compact", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Lato" in html


def test_ats_single_has_no_google_fonts_link() -> None:
    """ATS template must use system fonts only."""
    html = render_template("cv/ats-clean", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN not in html


def test_academic_has_no_google_fonts_link() -> None:
    """Academic template uses system serif fonts only."""
    html = render_template("cv/academic", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN not in html


# ── Redacted contact (public builds drop email/phone) ────────────────


@pytest.mark.parametrize(
    "template",
    ["cover-letter/brief", "cover-letter/standard", "project-summary/card"],
)
def test_render_with_name_only_contact(template: str) -> None:
    """A public build strips email/phone from contact entirely; under
    StrictUndefined the templates must guard on presence, not truthiness."""
    context = {**_FULL_CONTEXT, "contact": {"name": "Jane"}, "public": True}
    html = render_template(template, context)
    assert "Jane" in html


def _cert(name, issuer, *, date="", type="", url="", expiry_date="", identifier=""):
    """A certification with every optional key present.

    Raw render_template() bypasses loader.normalize_optional_fields(), which is
    what fills these in a real build; templates run under StrictUndefined.
    """
    return {
        "name": name,
        "issuer": issuer,
        "date": date,
        "type": type,
        "url": url,
        "expiry_date": expiry_date,
        "identifier": identifier,
    }


def _context_with_certs(certifications):
    ctx = dict(_FULL_CONTEXT)
    ctx["certifications"] = certifications
    ctx["show"] = {**_FULL_CONTEXT["show"], "certifications": True}
    ctx["section_order"] = [*_FULL_CONTEXT["section_order"], "certifications"]
    return ctx


def test_certifications_render_grouped_by_type():
    """Courses must not render under a "Certifications" heading."""
    html = render_template(
        "cv/ats-clean",
        _context_with_certs(
            [
                _cert("GenAI with LLMs", "DeepLearning.AI", type="course"),
                _cert("CKA", "CNCF", date="2023", type="certification"),
            ]
        ),
    )
    assert "Certifications" in html
    assert "Professional Development" in html
    # Credentials group renders before coursework.
    assert html.index("Certifications") < html.index("Professional Development")


def test_certifications_untyped_render_under_certifications_only():
    """Data predating the `type` field keeps rendering exactly as before."""
    html = render_template("cv/ats-clean", _context_with_certs([_cert("Legacy cert", "Acme")]))
    assert "Certifications" in html
    assert "Professional Development" not in html


# ── profile links in the header ──────────────────────────────────────

_CV_TEMPLATES = [
    "cv/ats-clean",
    "cv/academic",
    "cv/modern-single",
    "cv/executive-dark",
    "cv/timeline-clean",
    "cv/sidebar-compact",
]

# Every CV template except `cv/sidebar-compact`, which is the one two-column layout
# and is rated unsafe for extraction. The single-column rules below — no floated
# date, no block formatting context on the entry header — do not apply to it: it
# right-aligns its date on purpose, and its parse risk is the documented cost.
_SINGLE_COLUMN_TEMPLATES = [t for t in _CV_TEMPLATES if t != "cv/sidebar-compact"]


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_every_cv_template_renders_links_as_anchors(template: str) -> None:
    """Four templates used to ignore links entirely, dropping them silently."""
    html = render_template(template, _FULL_CONTEXT)
    assert '<a href="https://github.com/jane">' in html
    assert '<a href="https://linkedin.com/in/jane">' in html


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_link_text_is_the_url_not_the_label(template: str) -> None:
    """An ATS reading visible text must find a URL there."""
    html = render_template(template, _FULL_CONTEXT)
    assert ">github.com/jane</a>" in html


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_each_link_renders_exactly_once(template: str) -> None:
    """The old two-source model rendered LinkedIn and GitHub twice."""
    html = render_template(template, _FULL_CONTEXT)
    assert html.count('href="https://github.com/jane"') == 1
    assert html.count('href="https://linkedin.com/in/jane"') == 1


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_templates_render_without_any_links(template: str) -> None:
    context = {**_FULL_CONTEXT, "basics": {"headline": "Engineer", "summary": "S."}}
    html = render_template(template, context)
    assert "Engineer" in html


# ── entry tags are never rendered ────────────────────────────────

_TAGGED_CONTEXT = {
    **_FULL_CONTEXT,
    "work": [{**_FULL_CONTEXT["work"][0], "tags": ["FILINGTAG"]}],
    "projects": [{**_FULL_CONTEXT["projects"][0], "tags": ["FILINGTAG"]}],
}


@pytest.mark.parametrize("template", [*_CV_TEMPLATES, "project-summary/card"])
def test_entry_tags_are_never_rendered(template: str) -> None:
    """`tags` is a filing field. Rendering it published the filing vocabulary —
    career-phase and employer labels ended up as chips on the CV."""
    html = render_template(template, _TAGGED_CONTEXT)
    assert "FILINGTAG" not in html


# ── separator convention ─────────────────────────────────────────

_ASCII_FIRST_TEMPLATES = ["cv/ats-clean", "cv/academic"]

# U+00B7 MIDDLE DOT. Every separator extracts cleanly from a WeasyPrint PDF, so
# this is not about extraction; it is that a non-ASCII glyph depends on the
# embedded font subset carrying it, and the two single-column templates are the
# ones whose whole purpose is conservatism.
_MIDDOT = "·"


@pytest.mark.parametrize("template", _ASCII_FIRST_TEMPLATES)
def test_ats_first_templates_use_ascii_separators(template: str) -> None:
    html = render_template(template, _FULL_CONTEXT)
    assert _MIDDOT not in html


@pytest.mark.parametrize("template", _ASCII_FIRST_TEMPLATES)
def test_ats_first_templates_keep_title_and_org_adjacent(template: str) -> None:
    """Title and employer must land in the same extracted block, pipe-separated."""
    html = render_template(template, _FULL_CONTEXT)
    assert "Acme" in html and "Engineer" in html
    assert " | " in html  # contact line separator survives


@pytest.mark.parametrize("template", _ASCII_FIRST_TEMPLATES)
def test_ats_first_templates_use_hyphen_date_ranges(template: str) -> None:
    """Date ranges are one of the few things an ATS genuinely parses."""
    html = render_template(template, _FULL_CONTEXT)
    assert "2020-01 - Present" in html
    assert "–" not in html


@pytest.mark.parametrize(
    "template",
    [
        "cv/ats-clean",
        "cv/academic",
        "cv/modern-single",
        "cv/executive-dark",
        "cv/timeline-clean",
        "cv/sidebar-compact",
    ],
)
def test_date_ranges_are_ascii_in_every_template(template: str) -> None:
    """One range character across every template and every export format.

    An en dash is better typography, but a CV is meant to be machine-read and a
    document that mixes `-`, `–` and `—` gives a parser three things to handle.
    """
    html = render_template(template, _FULL_CONTEXT)
    assert "2020-01 - Present" in html
    body = _body_of(html)
    assert "–" not in body and "—" not in body, f"{template} renders a non-ASCII dash"


# ── Heading tracking ceiling ─────────────────────────────────────────

# WeasyPrint writes CSS letter-spacing as real inter-glyph advance in the PDF,
# and text extractors reinsert a word break wherever the advance exceeds their
# threshold. Measured against WeasyPrint output at heading sizes, .08em still
# extracts as one word and .10em does not: "EDUCATION" comes out "E D U C ATION".
# Section headings are what an ATS segments the document on, so a heading that
# extracts as loose letters costs the whole section its label. .06em keeps the
# tracked-uppercase look with margin under the cliff.
_MAX_HEADING_LETTER_SPACING_EM = 0.08

_LETTER_SPACING_RE = re.compile(r"letter-spacing:\s*(-?[\d.]+)em")


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_letter_spacing_stays_under_the_extraction_cliff(template: str) -> None:
    html = render_template(template, _FULL_CONTEXT)
    excessive = [
        v
        for v in (float(m) for m in _LETTER_SPACING_RE.findall(html))
        if v > _MAX_HEADING_LETTER_SPACING_EM
    ]
    assert not excessive, (
        f"{template} declares letter-spacing {excessive}em, above the "
        f"{_MAX_HEADING_LETTER_SPACING_EM}em ceiling at which PDF text "
        f"extraction starts splitting words into loose letters"
    )


# ── Where a right-aligned date is safe ───────────────────────────────

# Right-aligning a date puts it in its own geometric column, and an extractor
# flushes that column when the text beside it ends. Measured against WeasyPrint
# output: on work/education/projects, whose entries end in a bullet list, the date
# lands beside its own entry. On publications, certifications, and awards — short
# entries, some with a trailing summary paragraph — the column stayed open past
# the entry and the date surfaced late, in the worst case after the final section
# of the document. Those three therefore run the date inline on the meta line.


def _body_of(html: str) -> str:
    """Just the rendered body — the CSS names `.entry-date` whatever the markup does."""
    return html.split("<body>", 1)[1]


def _context_only(section: str, entries: list[dict]) -> dict:
    ctx = dict(_FULL_CONTEXT)
    ctx[section] = entries
    ctx["show"] = dict.fromkeys(_FULL_CONTEXT["show"], False) | {section: True}
    ctx["section_order"] = [section]
    ctx["basics"] = {**_FULL_CONTEXT["basics"], "summary": ""}
    return ctx


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
def test_compact_sections_run_dates_inline(template: str) -> None:
    award = {"title": "Prize", "date": "2023", "awarder": "Acme", "summary": ""}
    html = _body_of(render_template(template, _context_only("awards", [award])))
    assert "2023" in html
    # `.entry-header` is what carries `float: right`; the class alone is also used
    # for the inline date, so the header wrapper is the thing to assert against.
    assert "entry-header" not in html, f"{template} right-aligns an award date"


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
def test_compact_certifications_run_dates_inline(template: str) -> None:
    ctx = _context_only("certifications", [_cert("CKA", "CNCF", date="2023")])
    html = _body_of(render_template(template, ctx))
    assert "2023" in html
    assert "entry-header" not in html, f"{template} right-aligns a certification date"


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
@pytest.mark.parametrize("section", ["work", "education"])
def test_bullet_sections_carry_their_date_on_the_meta_line(template: str, section: str) -> None:
    """Every dated entry states its date inline, next to company and location.

    The right-hand scan column is gone: it leaves an empty band down the page that
    geometric extractors read as a column and lift the dates out of.
    """
    ctx = _context_only(section, _FULL_CONTEXT[section])
    html = _body_of(render_template(template, ctx))
    assert 'class="entry-meta"' in html
    assert "entry-date" in html
    assert "entry-header" not in html


# ── Constructs that decide extraction fidelity ───────────────────────

# Two extractors disagree about the same PDF: pdftotext rebuilds columns from glyph
# geometry, pypdf follows the content stream. `overflow: hidden` + `float: right`
# reads correctly in the first and fuses the title into the date in the second. The
# table-row form survives both. These tests pin the form, because the failure is
# invisible in the rendered page and in whichever extractor you happen to try.


def _entry_css_lines(template: str) -> list[str]:
    """CSS lines that style an entry header or its date.

    Scoped deliberately: `base.html.j2` ships a generic `.right { float: right }`
    utility, and asserting over the whole stylesheet flags that instead.
    """
    css = render_template(template, _FULL_CONTEXT).split("<body>", 1)[0]
    return [ln.strip() for ln in css.splitlines() if ".entry-date" in ln or ".entry-header" in ln]


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
def test_entry_headers_do_not_float_their_date(template: str) -> None:
    floated = [ln for ln in _entry_css_lines(template) if "float: right" in ln]
    assert not floated, f"{template} floats a date: {floated}"


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
def test_entry_headers_are_not_a_block_formatting_context(template: str) -> None:
    """`overflow: hidden` on the header is the construct pypdf mis-reads."""
    bfc = [ln for ln in _entry_css_lines(template) if ".entry-header" in ln and "overflow" in ln]
    assert not bfc, f"{template}: {bfc}"


@pytest.mark.parametrize("template", _SINGLE_COLUMN_TEMPLATES)
def test_entry_dates_are_not_a_right_hand_column(template: str) -> None:
    """Only `cv/sidebar-compact` still right-aligns a date, and it is rated unsafe.

    A right-aligned date leaves an empty band down the page that geometric
    extractors read as a column. The date now runs inline on the meta line;
    whether that survives extraction is settled in test_extraction_fidelity.py.
    """
    html = render_template(template, _FULL_CONTEXT)
    css = html.split("<body>", 1)[0]
    assert "entry-header" not in css, f"{template} still styles a right-hand date column"
    assert '<div class="entry-meta"' in html, f"{template} has no entry meta line"


# ── The base/template boundary ───────────────────────────────────────

# `skill-level*` is the one class base may style without a second user: nothing
# writes it in markup, `skill_level_bar` emits it, so that CSS is the rendering
# half of a filter's output contract rather than one template's styling.
_FILTER_OWNED_CLASSES = {"skill-level"}

_TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "cvloom" / "templates"


def _classes_in_markup() -> dict[str, set[str]]:
    """Map every class used in a packaged template's markup to the templates using it."""
    usage: dict[str, set[str]] = {}
    for path in sorted(_TEMPLATE_ROOT.glob("*/*.html.j2")):
        name = f"{path.parent.name}/{path.name.removesuffix('.html.j2')}"
        for attr in re.findall(r'class="([^"]*)"', path.read_text()):
            for token in attr.split():
                if "{" in token:  # a Jinja expression, not a literal class
                    continue
                usage.setdefault(token, set()).add(name)
    return usage


def _classes_styled_by_base() -> set[str]:
    css = (_TEMPLATE_ROOT / "base.html.j2").read_text()
    css = css.split("/* ---- Reset ---- */", 1)[1].split("{% block css_extra %}", 1)[0]
    # Selectors only: comments carry prose like `docs/dev/architecture.md`, which
    # otherwise reads as a class named `md`.
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return set(re.findall(r"\.([a-zA-Z][\w-]*)", css))


def test_base_styles_no_single_template_class() -> None:
    """`base.html.j2` may not name a class only one template uses.

    Base owns the document skeleton, the design tokens, element-level typography,
    print setup and the cross-cutting correctness invariants — kerning, pagination,
    heading semantics. It reaches templates through element selectors and a small
    shared *role* vocabulary. A class only one template uses is that template's
    skin, and styling it here inverts the dependency: base ends up knowing its
    subclasses, and a guarantee like "an entry never splits across a page" silently
    becomes "…if base has heard of your class name".

    This is how `.timeline-entry` got into the pagination rules. The fix was not to
    move the rule down into the template — that duplicates an invariant and lets the
    next template lose it by omission — but to have `cv/timeline-clean` write
    `class="entry timeline-entry"`: `entry` is the role base guarantees, and
    `timeline-entry` is the skin the template owns.
    """
    usage = _classes_in_markup()
    offenders = {
        cls: sorted(usage.get(cls, ()))
        for cls in _classes_styled_by_base()
        if not any(cls.startswith(owned) for owned in _FILTER_OWNED_CLASSES)
        and len(usage.get(cls, ())) < 2
    }
    assert not offenders, (
        "base.html.j2 styles classes that fewer than two templates use: "
        f"{offenders}. Either they are dead, or they belong in the template that "
        "uses them — see the docstring for the role-vs-skin rule."
    )


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_every_cv_entry_carries_the_entry_role(template: str) -> None:
    """Base's page-break protection is keyed on `.entry`, so every entry needs it.

    A template is free to add its own class alongside for styling; what it may not
    do is use that class *instead*, which is how a timeline entry once ended up
    depending on base knowing the word "timeline".
    """
    html = _body_of(render_template(template, _FULL_CONTEXT))
    attrs = [a.split() for a in re.findall(r'class="([^"]*)"', html)]
    assert any("entry" in tokens for tokens in attrs), f"{template} renders no entry boxes"
    for tokens in attrs:
        skins = [t for t in tokens if t.endswith("-entry")]
        assert not skins or "entry" in tokens, (
            f"{template} has an entry box classed {' '.join(tokens)!r}: {skins} is a skin "
            "used without the `entry` role, so base does not protect it from splitting "
            "across a page break"
        )


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_degree_and_field_join_with_a_space_by_default(template: str) -> None:
    """cvloom supplies no connecting word — the entry owns it (see decision F9)."""
    html = _body_of(render_template(template, _FULL_CONTEXT))
    assert "BSc CS" in html
    assert "BSc in CS" not in html


@pytest.mark.parametrize("template", _CV_TEMPLATES)
@pytest.mark.parametrize("connector", [" in ", ", ", " en "])
def test_degree_connector_renders_verbatim(template: str, connector: str) -> None:
    """Whatever the entry supplies is written through untouched, spacing included."""
    education = [{**_FULL_CONTEXT["education"][0], "connector": connector}]  # type: ignore[index]
    html = _body_of(render_template(template, {**_FULL_CONTEXT, "education": education}))
    assert f"BSc{connector}CS" in html
