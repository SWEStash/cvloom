"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cvloom.cli import cli


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a full project structure for CLI tests."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "basics.yaml").write_text(
        'headline: "Test Engineer"\nsummary: "Experienced engineer with 5 years in backend."\n'
    )
    (data / "work.yaml").write_text(
        '- company: Acme\n  title: Engineer\n  location: Remote\n'
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n"
        "    - Designed and implemented a distributed caching layer reducing latency by 40%.\n"
        "  tags: [python]\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "Test City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours and published 2 research papers.\n"
    )
    (data / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python, Go]\n"
    )

    projects = data / "projects"
    projects.mkdir()
    (projects / "alpha.yaml").write_text(
        "name: alpha\ndescription: First project.\ntags: [python, cli]\n"
        'url: "https://example.com/alpha"\nstart_date: "2023-01"\n'
        "highlights:\n  - Built a CLI tool used by 500 developers daily.\n"
    )
    (projects / "beta.yaml").write_text(
        "name: beta\ndescription: Second project.\ntags: [rust]\n"
        'url: "https://example.com/beta"\nstart_date: "2024-01"\n'
        "highlights:\n  - Implemented a high-performance parser reducing build times by 30%.\n"
    )

    private = tmp_path / "private"
    private.mkdir()
    (private / "contact.yaml").write_text(
        'name: Test User\nemail: "test@example.com"\nlocation: "Test City"\n'
    )

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


# ── build command ──────────────────────────────────────────────────


def test_build_html_only(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--skip-pdf", "--public"])
    assert result.exit_code == 0
    assert "HTML" in result.output


def test_build_missing_profile(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--profile", "nonexistent"])
    assert result.exit_code != 0


def test_build_with_template_override(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["build", "--template", "cv/modern-single", "--skip-pdf", "--public"]
    )
    assert result.exit_code == 0
    assert "HTML" in result.output


# ── check command ──────────────────────────────────────────────────


def test_check_clean_profile(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["check"])
    assert result.exit_code == 0


def test_check_with_noise_skill(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (project_root / "data" / "skills.yaml").write_text(
        "- category: Office\n  items: [Microsoft Word]\n"
    )
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["check"])
    assert result.exit_code == 1
    assert "ats-003" in result.output


# ── trim command ───────────────────────────────────────────────────


def test_trim_default(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["trim"])
    assert result.exit_code == 0
    assert "Total" in result.output


# ── diff command ───────────────────────────────────────────────────


def test_diff_two_profiles(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", "general", "backend"])
    assert result.exit_code == 0
    assert "Words" in result.output


# ── export command ─────────────────────────────────────────────────


def test_export_json_resume(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    out_path = project_root / "dist" / "resume.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--format", "json-resume", "--output", str(out_path)])
    assert result.exit_code == 0
    assert out_path.exists()


# ── init command ───────────────────────────────────────────────────


def test_init_creates_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_dir = tmp_path / "fresh"
    init_dir.mkdir()
    # Create a fake git repo so the hook installer doesn't skip
    (init_dir / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.chdir(init_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert (init_dir / "data").is_dir()
    assert (init_dir / "profiles").is_dir()
    assert (init_dir / "private").is_dir()


def test_init_force_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_dir = tmp_path / "fresh2"
    init_dir.mkdir()
    (init_dir / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.chdir(init_dir)
    runner = CliRunner()
    runner.invoke(cli, ["init"])
    result = runner.invoke(cli, ["init", "--force"])
    assert result.exit_code == 0
