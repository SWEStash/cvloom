"""Tests for template renderer."""

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
        "linkedin": "jane",
        "github": "jane",
        "website": "https://jane.dev",
    },
    "basics": {
        "headline": "Engineer",
        "summary": "Great engineer.",
        "public_links": [{"label": "GitHub", "url": "https://github.com/jane"}],
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
    assert "python" in html
    assert "A project." in html


# ── Built-in CV template rendering ────────────────────────────────


def test_render_ats_single_template() -> None:
    html = render_template("cv/ats-single", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Engineer" in html
    assert "Experience" in html or "Skills" in html
    assert "Acme" in html


def test_render_modern_single_template() -> None:
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert "Jane" in html
    assert "Acme" in html
    assert "Languages" in html


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
    assert "Executive Summary" in html


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


def test_modern_single_has_inter_font_link() -> None:
    html = render_template("cv/modern-single", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Inter" in html


def test_executive_dark_has_roboto_font_link() -> None:
    html = render_template("cv/executive-dark", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Roboto" in html


def test_sidebar_compact_has_roboto_font_link() -> None:
    html = render_template("cv/sidebar-compact", _FULL_CONTEXT)
    assert _GOOGLE_FONTS_DOMAIN in html
    assert "Roboto" in html


def test_ats_single_has_no_google_fonts_link() -> None:
    """ATS template must use system fonts only."""
    html = render_template("cv/ats-single", _FULL_CONTEXT)
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
