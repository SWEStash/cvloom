"""Tests for the MCP server tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cvloom.mcp_server import (
    create_profile,
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
    (projects / "beta.yaml").write_text(
        'name: beta\ndescription: "Another project."\ntags: [go]\n'
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

    return str(tmp_path)


def test_list_profiles(project_dir: str) -> None:
    result = json.loads(list_profiles(project_root=project_dir))
    assert len(result) == 1
    assert result[0]["name"] == "general"
    assert result[0]["template"] == "cv/ats-single"


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


def test_validate_data_invalid(project_dir: str) -> None:
    # Write invalid basics (missing required fields)
    (Path(project_dir) / "data" / "basics.yaml").write_text("foo: bar\n")
    result = json.loads(validate_data(project_root=project_dir))
    assert result["valid"] is False
    assert len(result["errors"]) > 0
