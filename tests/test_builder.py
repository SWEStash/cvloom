"""Tests for builder utilities and resolve()."""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom.builder import (
    _estimate_pages,
    _section_summary,
    _word_count_by_section,
    resolve,
)
from cvloom.renderer import list_templates, template_exists

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


# ── _word_count_by_section ──────────────────────────────────────────


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
    counts = _word_count_by_section(data, show)
    assert counts["basics"] > 0
    assert counts["work"] > 0
    assert counts["skills"] > 0


# ── resolve() ───────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure for resolve() tests."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "basics.yaml").write_text(
        'headline: "Test Engineer"\nsummary: "A test summary."\n'
    )
    (data / "work.yaml").write_text(
        '- company: Acme\n  title: Engineer\n  start_date: "2020-01"\n'
        "  highlights:\n    - Built things.\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  start_date: "2016"\n'
    )
    (data / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python]\n"
    )
    projects = data / "projects"
    projects.mkdir()
    (projects / "alpha.yaml").write_text(
        'name: alpha\ndescription: "A project."\ntags: [python]\n'
    )

    private = tmp_path / "private"
    private.mkdir()
    (private / "contact.yaml").write_text(
        'name: Test\nemail: "test@example.com"\n'
    )

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text(
        "template: cv/ats-single\noutput_filename: cv\n"
    )

    return tmp_path


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
    with pytest.raises(SystemExit, match="not found"):
        resolve(
            data_dir=project_dir / "data",
            private_dir=project_dir / "private",
            profiles_dir=project_dir / "profiles",
            profile_name="bad",
            public=True,
        )


def test_template_exists_true() -> None:
    assert template_exists("cv/ats-single") is True


def test_template_exists_false() -> None:
    assert template_exists("cv/nonexistent") is False


def test_list_templates_contains_known() -> None:
    templates = list_templates()
    assert "cv/ats-single" in templates
    assert "cv/modern-single" in templates
    assert "cv/academic" in templates


def test_resolve_public_uses_placeholder(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert result.data["contact"]["email"] == "your.email@example.com"
