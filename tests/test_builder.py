"""Tests for builder utilities and resolve()."""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom.builder import (
    ResolveError,
    _estimate_pages,
    _pdf_filename,
    resolve,
)
from cvloom.cli import _section_summary
from cvloom.models import ResolvedProfile
from cvloom.renderer import list_templates, template_exists
from cvloom.sections import count_words
from tests.conftest import make_project, make_resolved

# ── _estimate_pages ─────────────────────────────────────────────────


def test_estimate_pages_single():
    html = "<p>" + " ".join(["word"] * 200) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 200
    assert pages == 1


def test_estimate_pages_two():
    html = "<p>" + " ".join(["word"] * 700) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 700
    assert pages == 2


def test_estimate_pages_strips_style_blocks():
    style = "<style>.foo { border-bottom: 1px solid red; color: blue; }</style>"
    body = "<p>" + " ".join(["word"] * 100) + "</p>"
    html = style + body
    words, _ = _estimate_pages(html)
    assert words == 100


# ── _section_summary ────────────────────────────────────────────────


def test_section_summary_all():
    data = {
        "work": [{}] * 3,
        "education": [{}] * 1,
        "skills": [{}] * 4,
        "projects": [{}] * 2,
    }
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert "work×3" in result
    assert "edu×1" in result
    assert "skills×4" in result
    assert "projects×2" in result


def test_section_summary_hidden():
    data = {
        "work": [{}] * 2,
        "education": [{}] * 1,
        "skills": [{}] * 3,
        "projects": [{}] * 5,
    }
    show = {"work": True, "education": False, "skills": True, "projects": False}
    result = _section_summary(data, show)
    assert "work×2" in result
    assert "edu" not in result
    assert "skills×3" in result
    assert "projects" not in result


def test_section_summary_empty_data():
    data: dict = {}
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert result == ""


# ── sections.count_words ────────────────────────────────────────────


def test_word_count_by_section():
    data = {
        "basics": {"headline": "Software Engineer", "summary": "A great engineer."},
        "work": [
            {"company": "Acme", "title": "Engineer", "highlights": ["Built things fast."]},
        ],
        "skills": [
            {"category": "Languages", "items": ["Python", "Go"]},
        ],
        "education": [],
        "projects": [],
    }
    show = {"work": True, "education": True, "skills": True, "projects": True}
    resolved = ResolvedProfile(
        profile={},
        data=data,
        show_sections=show,
        section_order=[],
        template_name="cv/ats-single",
        output_filename="cv",
    )
    counts = count_words(resolved)
    assert counts["basics"] > 0
    assert counts["work"] > 0
    assert counts["skills"] > 0


# ── _pdf_filename ────────────────────────────────────────────────────


def _make_resolved_for_pdf(
    contact_name: str = "Jane Doe",
    output_filename: str = "cv",
    pdf_filename_format: str | None = None,
) -> ResolvedProfile:
    profile: dict = {}
    if pdf_filename_format:
        profile["pdf_filename_format"] = pdf_filename_format
    return make_resolved(
        profile=profile,
        contact={"name": contact_name},
        show={},
        section_order=[],
        output_filename=output_filename,
    )


def test_pdf_filename_derives_from_contact_name():
    resolved = _make_resolved_for_pdf(contact_name="Jane Doe")
    assert _pdf_filename(resolved) == "Jane_Doe_Resume"


def test_pdf_filename_single_name():
    resolved = _make_resolved_for_pdf(contact_name="Mononym")
    assert _pdf_filename(resolved) == "Mononym_Resume"


def test_pdf_filename_format_override():
    resolved = _make_resolved_for_pdf(
        contact_name="Jane Doe",
        pdf_filename_format="{first}_{last}_CV_2026",
    )
    assert _pdf_filename(resolved) == "Jane_Doe_CV_2026"


def test_pdf_filename_format_name_placeholder():
    resolved = _make_resolved_for_pdf(
        contact_name="Jane Doe",
        pdf_filename_format="{name}_Resume",
    )
    assert _pdf_filename(resolved) == "Jane_Doe_Resume"


def test_pdf_filename_fallback_on_empty_name():
    resolved = _make_resolved_for_pdf(contact_name="", output_filename="my-cv")
    assert _pdf_filename(resolved) == "my-cv"


# ── resolve() ───────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure for resolve() tests."""
    return make_project(tmp_path)


def test_resolve_returns_resolved_profile(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        profile_name="general",
        public=True,
    )
    assert result.template_name == "cv/ats-single"
    assert result.output_filename == "cv"
    assert "basics" in result.data
    assert "work" in result.data
    assert result.show_sections["work"] is True


def test_resolve_invalid_template_fails_early(project_dir: Path) -> None:
    (project_dir / "profiles" / "bad.yaml").write_text("template: cv/nonexistent\n")
    with pytest.raises(ResolveError) as excinfo:
        resolve(
            data_dir=project_dir / "data",
            private_dir=project_dir / "private",
            profiles_dir=project_dir / "profiles",
            profile_name="bad",
            public=True,
        )
    assert any("not found" in e for e in excinfo.value.errors)


def test_resolve_invalid_data_raises_resolve_error_silently(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Corrupt basics so schema validation fails.
    (project_dir / "data" / "basics.yaml").write_text("headline: 123\n")
    with pytest.raises(ResolveError) as excinfo:
        resolve(
            data_dir=project_dir / "data",
            private_dir=project_dir / "private",
            profiles_dir=project_dir / "profiles",
            profile_name="general",
            public=True,
        )
    assert excinfo.value.errors  # carries the real messages
    # resolve() is pure: it prints nothing.
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_template_exists_true() -> None:
    assert template_exists("cv/ats-single") is True


def test_template_exists_false() -> None:
    assert template_exists("cv/nonexistent") is False


def test_list_templates_contains_known() -> None:
    templates = list_templates()
    assert "cv/ats-single" in templates
    assert "cv/modern-single" in templates
    assert "cv/academic" in templates


def test_resolve_public_redacts_sensitive_fields(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert "email" not in result.data["contact"]
    assert "phone" not in result.data["contact"]
    assert result.data["contact"]["name"] == "Test"
