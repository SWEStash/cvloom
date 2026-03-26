"""Tests for the MCP server tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cvloom.mcp_server import (
    _slugify,
    build_cv,
    create_profile,
    export_json_resume,
    get_section,
    list_profiles,
    list_projects,
    upsert_project,
    validate_data,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> str:
    """Create a minimal project structure for MCP tests."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "basics.yaml").write_text(
        'headline: "Test Engineer"\nsummary: "A test summary."\n'
    )
    (data / "work.yaml").write_text(
        '- company: Acme\n  title: Engineer\n  location: Remote\n'
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n    - Designed and built a distributed system handling 10k requests.\n"
        "  tags: [python]\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours in computer science program.\n"
    )
    (data / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python]\n"
    )
    projects = data / "projects"
    projects.mkdir()
    (projects / "alpha.yaml").write_text(
        'name: alpha\ndescription: "A project."\ntags: [python]\n'
        'url: "https://example.com/alpha"\nstart_date: "2023-01"\n'
        "highlights:\n  - Built a CLI tool used by 500 developers daily.\n"
    )
    (projects / "beta.yaml").write_text(
        'name: beta\ndescription: "Another project."\ntags: [go]\n'
        'url: "https://example.com/beta"\nstart_date: "2024-01"\n'
        "highlights:\n  - Implemented a high-performance parser.\n"
    )

    private = tmp_path / "private"
    private.mkdir()
    (private / "contact.yaml").write_text(
        'name: Test\nemail: "test@example.com"\nphone: "+1 (555) 000-0000"\n'
        'location: "Test City"\nlinkedin: testuser\ngithub: testuser\n'
        'website: "https://example.com"\n'
    )

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text(
        "template: cv/ats-single\noutput_filename: cv\n"
    )
    (profiles / "backend.yaml").write_text(
        "template: cv/modern-single\noutput_filename: backend-cv\n"
        "include_tags: [python]\n"
    )

    return str(tmp_path)


def test_list_profiles(project_dir: str) -> None:
    result = json.loads(list_profiles(project_root=project_dir))
    assert len(result) == 2
    names = {p["name"] for p in result}
    assert "general" in names
    assert "backend" in names
    general = next(p for p in result if p["name"] == "general")
    assert general["template"] == "cv/ats-single"


def test_list_projects_all(project_dir: str) -> None:
    result = json.loads(list_projects(project_root=project_dir))
    assert len(result) == 2
    names = {p["name"] for p in result}
    assert "alpha" in names
    assert "beta" in names


def test_list_projects_tag_filter(project_dir: str) -> None:
    result = json.loads(list_projects(project_root=project_dir, tags=["python"]))
    assert len(result) == 1
    assert result[0]["name"] == "alpha"


def test_get_section_basics(project_dir: str) -> None:
    result = json.loads(get_section("basics", project_root=project_dir))
    assert result["headline"] == "Test Engineer"


def test_get_section_projects(project_dir: str) -> None:
    result = json.loads(get_section("projects", project_root=project_dir))
    assert len(result) == 2


def test_get_section_contact(project_dir: str) -> None:
    result = json.loads(get_section("contact", project_root=project_dir))
    assert result["name"] == "Test"


def test_get_section_missing(project_dir: str) -> None:
    result = json.loads(get_section("nonexistent", project_root=project_dir))
    assert "error" in result


def test_create_profile(project_dir: str) -> None:
    config = {"template": "cv/ats-single", "output_filename": "test-cv"}
    result = json.loads(create_profile("test", config, project_root=project_dir))
    assert "created" in result
    assert Path(result["created"]).exists()


def test_create_profile_invalid(project_dir: str) -> None:
    config = {"invalid_key": True}  # missing required 'template'
    result = json.loads(create_profile("bad", config, project_root=project_dir))
    assert "error" in result


def test_upsert_project(project_dir: str) -> None:
    project = {"name": "gamma", "description": "New project.", "tags": ["rust"]}
    result = json.loads(upsert_project(project, project_root=project_dir))
    assert "written" in result
    assert Path(result["written"]).exists()


def test_validate_data_valid(project_dir: str) -> None:
    result = json.loads(validate_data(project_root=project_dir))
    assert result["valid"] is True


def test_slugify_basic() -> None:
    assert _slugify("My Project") == "my-project"


def test_slugify_accents() -> None:
    assert _slugify("Résumé Professionnel") == "resume-professionnel"


def test_slugify_special_chars() -> None:
    assert _slugify("C++ & Rust!") == "c-rust"


def test_slugify_consecutive_spaces() -> None:
    assert _slugify("  foo   bar  ") == "foo-bar"


def test_slugify_empty() -> None:
    assert _slugify("") == "untitled"


def test_upsert_project_special_name(project_dir: str) -> None:
    project = {"name": "My Project!", "description": "Special.", "tags": ["test"]}
    result = json.loads(upsert_project(project, project_root=project_dir))
    assert "written" in result
    written_path = Path(result["written"])
    assert written_path.name == "my-project.yaml"
    assert written_path.exists()


def test_validate_data_invalid(project_dir: str) -> None:
    # Write invalid basics (missing required fields)
    (Path(project_dir) / "data" / "basics.yaml").write_text("foo: bar\n")
    result = json.loads(validate_data(project_root=project_dir))
    assert result["valid"] is False
    assert len(result["errors"]) > 0


# ── build_cv tests ─────────────────────────────────────────────────


def test_build_cv_html_only(project_dir: str) -> None:
    result = json.loads(build_cv(profile="general", skip_pdf=True, project_root=project_dir))
    assert "html_path" in result
    assert result["words"] > 0
    assert result["pages"] >= 1


def test_build_cv_missing_profile(project_dir: str) -> None:
    with pytest.raises(FileNotFoundError):
        build_cv(profile="nonexistent", skip_pdf=True, project_root=project_dir)


# ── export_json_resume tests ───────────────────────────────────────


def test_export_json_resume_valid(project_dir: str) -> None:
    result = json.loads(export_json_resume(profile="general", project_root=project_dir))
    assert "basics" in result
    assert result["basics"]["name"] == "Test"


def test_export_json_resume_missing_profile(project_dir: str) -> None:
    with pytest.raises(FileNotFoundError):
        export_json_resume(profile="nonexistent", project_root=project_dir)
