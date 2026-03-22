"""Tests for CLI commands added in Phase 1."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cvloom.cli import cli


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project structure for CLI tests."""
    # data/projects/
    projects = tmp_path / "data" / "projects"
    projects.mkdir(parents=True)
    (projects / "alpha.yaml").write_text(
        "name: alpha\ndescription: First project.\ntags: [python, cli]\n"
    )
    (projects / "beta.yaml").write_text(
        "name: beta\ndescription: Second project.\ntags: [rust]\n"
    )

    # profiles/
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text(
        "template: cv/ats-single\noutput_filename: cv\n"
    )
    (profiles / "backend.yaml").write_text(
        "template: cv/modern-single\noutput_filename: backend-cv\n"
        "include_tags: [python]\n"
        "job_context:\n  company: Acme\n  role: Senior Engineer\n"
    )

    return tmp_path


def test_list_projects_all(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-projects"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" in result.output
    assert "2 project(s)" in result.output


def test_list_projects_tag_filter(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-projects", "--tag", "python"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" not in result.output
    assert "1 project(s)" in result.output


def test_list_projects_no_match(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-projects", "--tag", "haskell"])
    assert result.exit_code == 0
    assert "No projects match" in result.output


def test_list_projects_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-projects"])
    assert result.exit_code != 0


def test_list_profiles(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-profiles"])
    assert result.exit_code == 0
    assert "general" in result.output
    assert "backend" in result.output
    assert "2 profile(s)" in result.output


def test_list_profiles_shows_job_context(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-profiles"])
    assert result.exit_code == 0
    assert "Acme" in result.output


def test_list_profiles_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-profiles"])
    assert result.exit_code != 0
