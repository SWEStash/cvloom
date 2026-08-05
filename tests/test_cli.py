"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from cvloom.cli import cli
from tests.ai_fakes import FakeClient


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a full project structure for CLI tests."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "basics.yaml").write_text(
        'headline: "Test Engineer"\n'
        'summary: "Experienced backend engineer with 5 years building scalable distributed'
        " systems in Python and Go, delivering measurable reliability improvements and"
        ' infrastructure cost reductions across high-traffic production services."\n'
        "links:\n"
        '  - label: LinkedIn\n    url: "https://linkedin.com/in/testuser"\n'
        '  - label: GitHub\n    url: "https://github.com/testuser"\n'
    )
    (data / "work.yaml").write_text(
        "- company: Acme\n  title: Engineer\n  location: Remote\n"
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n"
        "    - Reduce API latency by 40 percent by adding a Redis cache to five endpoints.\n"
        "    - Save 30 percent on cloud costs by right-sizing Docker containers.\n"
        "    - Mentor 4 junior engineers and help them reach senior level in 18 months.\n"
        "  tags: [python]\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "Test City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours and published 2 research papers.\n"
    )
    (data / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python, Go, Rust, TypeScript]\n"
        "- category: Tools\n  items: [Docker, Kubernetes, Terraform, Postgres]\n"
    )

    # Projects load in *filename* order, so the alphabetically-first file must
    # hold the newest project to stay reverse-chronological (wl-019).
    projects = data / "projects"
    projects.mkdir()
    (projects / "alpha.yaml").write_text(
        "name: alpha\ndescription: First project.\ntags: [python, cli]\n"
        'url: "https://example.com/alpha"\nstart_date: "2024-01"\n'
        "highlights:\n  - Built a CLI tool in Python used by over 500 developers every day.\n"
    )
    (projects / "beta.yaml").write_text(
        "name: beta\ndescription: Second project.\ntags: [rust]\n"
        'url: "https://example.com/beta"\nstart_date: "2023-01"\n'
        "highlights:\n  - Wrote a Rust parser cutting build times by 30 percent on all pipelines.\n"
    )

    private = tmp_path / "private"
    private.mkdir()
    (private / "contact.yaml").write_text(
        'name: Test User\nemail: "test@example.com"\nlocation: "Test City"\n'
    )

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text("template: cv/ats-clean\noutput_filename: cv\n")
    (profiles / "backend.yaml").write_text(
        "template: cv/modern-single\noutput_filename: backend-cv\n"
        "select:\n  work:\n    tags: [python]\n"
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


def test_build_prints_section_summary(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The summary is wrapped in literal brackets, which Rich reads as a markup
    tag unless escaped — it was computed and silently dropped for a long time."""
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["build", "--skip-pdf", "--public"])
    assert result.exit_code == 0
    assert "work×1" in result.output
    assert "edu×1" in result.output


def test_build_missing_profile(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--profile", "nonexistent"])
    assert result.exit_code != 0


def test_build_with_template_override(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["build", "--template", "cv/modern-single", "--skip-pdf", "--public"]
    )
    assert result.exit_code == 0
    assert "HTML" in result.output


def test_build_check_flag(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--skip-pdf", "--public", "--check"])
    assert result.exit_code == 0
    assert "Writing lint" in result.output


def test_build_strict_passes(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    # A generous findings budget passes.
    result = runner.invoke(cli, ["build", "--skip-pdf", "--public", "--strict", "100"])
    assert result.exit_code == 0
    assert "Writing lint" in result.output


def test_build_strict_fails(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Guarantee at least one finding (a noise skill), then use a zero budget.
    (project_root / "data" / "skills.yaml").write_text(
        "- category: Office\n  items: [Microsoft Word]\n"
    )
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--skip-pdf", "--public", "--strict", "0"])
    assert result.exit_code != 0
    assert "Writing lint" in result.output


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
    assert "wl-003" in result.output


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
    # Scaffolds the reusable GitHub Pages publish workflow.
    workflow = init_dir / ".github" / "workflows" / "publish-cv.yml"
    assert workflow.is_file()
    assert "DEPLOY_PAGES" in workflow.read_text()
    assert "DEPLOY_PAGES" in result.output


def test_init_force_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_dir = tmp_path / "fresh2"
    init_dir.mkdir()
    (init_dir / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.chdir(init_dir)
    runner = CliRunner()
    runner.invoke(cli, ["init"])
    # Corrupt a scaffolded file, then prove --force restores it.
    basics = init_dir / "data" / "basics.yaml"
    original = basics.read_text()
    basics.write_text("# clobbered\n")
    result = runner.invoke(cli, ["init", "--force"])
    assert result.exit_code == 0
    assert basics.read_text() == original
    assert "# clobbered" not in basics.read_text()


# ── sync command ───────────────────────────────────────────────────


def _init_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.chdir(proj)
    CliRunner().invoke(cli, ["init"])
    return proj


def test_sync_reports_up_to_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_project(tmp_path, monkeypatch)
    result = CliRunner().invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "up to date" in result.output


def test_sync_detects_outdated_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _init_project(tmp_path, monkeypatch)
    workflow = proj / ".github" / "workflows" / "publish-cv.yml"
    workflow.write_text(workflow.read_text() + "\n# local edit\n")

    result = CliRunner().invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "out of date" in result.output
    assert "--force" in result.output
    # Without --force the file is untouched.
    assert "# local edit" in workflow.read_text()


def test_sync_force_restores_managed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj = _init_project(tmp_path, monkeypatch)
    workflow = proj / ".github" / "workflows" / "publish-cv.yml"
    workflow.write_text("garbage\n")

    result = CliRunner().invoke(cli, ["sync", "--force"])
    assert result.exit_code == 0
    assert "Updated" in result.output
    restored = workflow.read_text()
    assert "garbage" not in restored
    assert "DEPLOY_PAGES" in restored


def test_sync_reports_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    proj = _init_project(tmp_path, monkeypatch)
    (proj / ".github" / "workflows" / "publish-cv.yml").unlink()

    result = CliRunner().invoke(cli, ["sync"])
    assert result.exit_code == 0
    assert "missing" in result.output
    # --force writes the missing file back.
    CliRunner().invoke(cli, ["sync", "--force"])
    assert (proj / ".github" / "workflows" / "publish-cv.yml").is_file()


# ── build --all ──────────────────────────────────────────────────────


def test_build_all_builds_every_profile(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["build", "--all", "--public", "--skip-pdf"])
    assert result.exit_code == 0, result.output
    assert "general" in result.output
    assert "backend" in result.output
    assert "Built 2 profile(s)." in result.output
    assert (project_root / "dist" / "cv.html").exists()
    assert (project_root / "dist" / "backend-cv.html").exists()


def test_build_all_without_profiles_dir_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["build", "--all", "--public", "--skip-pdf"])
    assert result.exit_code == 1


def test_build_all_stops_on_a_broken_profile(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A batch that reports success while one CV silently did not rebuild is worse
    than one that stops and names the profile."""
    (project_root / "profiles" / "broken.yaml").write_text(
        "template: cv/ats-clean\noutput_filename: broken\nsection_titles:\n  nope: 'X'\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["build", "--all", "--public", "--skip-pdf"])
    assert result.exit_code == 1
    assert "Built 3 profile(s)." not in result.output


def test_list_templates_reports_extraction_ratings(monkeypatch: pytest.MonkeyPatch) -> None:
    result = CliRunner().invoke(cli, ["list-templates"])
    assert result.exit_code == 0
    assert "cv/ats-clean" in result.output
    assert "safe" in result.output
    # Every rating in use must reach the table, whatever the current mix is.
    from cvloom import templates_meta

    for rating in {info.ats for info in templates_meta.TEMPLATES.values()}:
        assert rating in result.output, f"list-templates omits the {rating!r} rating"


def test_risky_template_recommends_the_docx_export(capsys: pytest.CaptureFixture[str]) -> None:
    """A PDF only implies its reading order; a .docx states it.

    So when the layout is one we know extracts badly, the build should name the
    artifact that does not have the problem rather than only warning about the one
    that does.
    """
    from cvloom.cli import _warn_template_parse_risk

    _warn_template_parse_risk("cv/sidebar-compact")
    out = capsys.readouterr().out
    assert "parses with caveats" in out
    assert "docx" in out.lower()


def test_safe_template_says_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    from cvloom.cli import _warn_template_parse_risk

    _warn_template_parse_risk("cv/ats-clean")
    assert capsys.readouterr().out == ""


# ── error reporting ──────────────────────────────────────────────────


def test_unknown_profile_reports_an_error_not_a_traceback(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mistyped profile name is the user's to fix, so it gets a message.

    `export` was the one command that never wrapped its own resolve call, and so
    printed a raw FileNotFoundError traceback at the terminal. The handling now
    lives on the group, where a command cannot forget it.
    """
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--format", "json-resume", "--profile", "nope"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Profile not found: nope" in result.output


def test_unknown_profile_names_the_ones_that_exist(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--format", "json-resume", "--profile", "nope"])
    assert "general" in result.output


def test_verbose_restores_the_traceback(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--verbose", "export", "--format", "json-resume", "--profile", "nope"]
    )
    assert result.exit_code == 1
    assert "FileNotFoundError" in result.output


def test_error_message_points_at_the_verbose_flag(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--format", "json-resume", "--profile", "nope"])
    assert "--verbose" in result.output


def test_a_command_that_succeeds_is_untouched(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The handler must not swallow or reword a normal run."""
    monkeypatch.chdir(project_root)
    runner = CliRunner()
    result = runner.invoke(cli, ["list-profiles"])
    assert result.exit_code == 0
    assert "Error:" not in result.output


@pytest.mark.parametrize("command", ["build", "check", "export", "trim", "diff", "init"])
def test_subcommand_help_exits_clean(command: str) -> None:
    """`--help` raises `click.exceptions.Exit`, which subclasses `RuntimeError` rather
    than `ClickException` or `SystemExit`. Left out of the re-raise tuple it reached the
    generic handler, so every subcommand printed its help and then `Error: Exit: 0`."""
    result = CliRunner().invoke(cli, [command, "--help"])
    assert result.exit_code == 0
    assert "Error:" not in result.output
    assert "--verbose" not in result.output


def test_group_help_exits_clean() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Error:" not in result.output


# ── _friendly: the exception rewrites ────────────────────────────────

# Click validates path options before a command body runs, so a directory passed
# where a file is expected, or an unreadable file, never reaches the group handler
# through the CLI. These branches are therefore exercised directly.


def test_friendly_names_the_directory_when_a_file_was_expected() -> None:
    from cvloom.cli import _friendly

    exc = IsADirectoryError(21, "Is a directory")
    exc.filename = "data/work.yaml"
    assert _friendly(exc) == "Expected a file, got a directory: data/work.yaml"


def test_friendly_names_the_unreadable_file() -> None:
    from cvloom.cli import _friendly

    exc = PermissionError(13, "Permission denied")
    exc.filename = "private/contact.yaml"
    assert _friendly(exc) == "Permission denied: private/contact.yaml"


def test_friendly_joins_every_validation_error() -> None:
    """A ResolveError carries a list; reporting only the first hides the rest."""
    from cvloom import builder
    from cvloom.cli import _friendly

    assert _friendly(builder.ResolveError(["work[0]: no title", "work[0]: no company"])) == (
        "work[0]: no title; work[0]: no company"
    )


def test_friendly_admits_an_unexpected_exception_is_ours() -> None:
    """Anything not on the list is a bug, and says so as `TypeName: message`
    rather than being dressed up as user error."""
    from cvloom.cli import _friendly

    assert _friendly(ValueError("something we did not anticipate")) == (
        "ValueError: something we did not anticipate"
    )


def test_malformed_yaml_reports_one_line(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / "data" / "work.yaml").write_text("- company: Acme\n  title: [unclosed\n")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["check"])
    assert result.exit_code == 1
    assert "Invalid YAML" in result.output
    assert "Traceback" not in result.output


# ── resolve errors and selection warnings ────────────────────────────


def test_check_reports_validation_errors_from_resolve(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`check` resolves through `_resolve`, which renders a ResolveError itself."""
    (project_root / "data" / "work.yaml").write_text("- company: Acme\n")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["check"])
    assert result.exit_code == 1
    assert "Validation errors:" in result.output


def test_selection_that_matches_nothing_warns(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selection is include-only, so a typo'd tag silently empties a section."""
    (project_root / "profiles" / "general.yaml").write_text(
        "template: cv/ats-clean\noutput_filename: cv\nselect:\n  work:\n    tags: [typo]\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["trim"])
    assert result.exit_code == 0
    assert "Warning:" in result.output


# ── build: extracted text ────────────────────────────────────────────


def test_extracted_text_is_named_per_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One `.txt` would imply one right answer; the engines disagree by design."""
    from cvloom import extract as extract_mod
    from cvloom.cli import _write_extracted_text

    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(extract_mod, "available_engines", lambda: ["poppler", "pypdf"])
    monkeypatch.setattr(
        extract_mod,
        "extract_all",
        lambda p: [
            extract_mod.Extraction("poppler", "poppler order"),
            extract_mod.Extraction("pypdf", "pypdf order"),
        ],
    )
    _write_extracted_text(pdf)
    assert (tmp_path / "cv.poppler.txt").read_text() == "poppler order"
    assert (tmp_path / "cv.pypdf.txt").read_text() == "pypdf order"


def test_extracted_text_warns_when_no_engine_is_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from cvloom import extract as extract_mod
    from cvloom.cli import _write_extracted_text

    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(extract_mod, "available_engines", lambda: [])
    _write_extracted_text(pdf)
    assert "no PDF text extractor available" in capsys.readouterr().err
    assert list(tmp_path.glob("*.txt")) == []


def test_build_extract_text_writes_beside_the_pdf(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("weasyprint")
    from cvloom import extract as extract_mod

    monkeypatch.setattr(extract_mod, "available_engines", lambda: ["poppler"])
    monkeypatch.setattr(
        extract_mod, "extract_all", lambda p: [extract_mod.Extraction("poppler", "text layer")]
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["build", "--public", "--extract-text"])
    assert result.exit_code == 0
    # The PDF is named after the contact, so find the text layer beside it.
    written = list((project_root / "dist").glob("*.poppler.txt"))
    assert [p.read_text() for p in written] == ["text layer"]


def _fatten(project_root: Path, entries: int) -> None:
    """Append enough work history to push the build past the page ceiling."""
    blocks = [
        f"- company: Corp{i}\n  title: Engineer\n  location: Remote\n"
        f'  start_date: "20{i:02d}-01"\n  end_date: "20{i:02d}-12"\n'
        "  highlights:\n"
        + "".join(
            f"    - Delivered subsystem {i}.{j} and cut processing time by {j} percent "
            "across every regional deployment in the fleet during the migration.\n"
            for j in range(6)
        )
        for i in range(entries)
    ]
    with (project_root / "data" / "work.yaml").open("a") as fh:
        fh.write("".join(blocks))


def test_build_warns_when_the_cv_runs_long(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fatten(project_root, 12)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["build", "--skip-pdf", "--public"])
    assert result.exit_code == 0
    assert "exceeds" in result.output


def test_trim_reports_the_words_to_cut(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fatten(project_root, 12)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["trim"])
    assert result.exit_code == 0
    assert "words to reach target" in result.output
    assert "Recommendations:" in result.output


def test_build_all_with_an_empty_profiles_dir_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Distinct from a missing directory: the directory is there and holds nothing."""
    (tmp_path / "profiles").mkdir()
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["build", "--all", "--skip-pdf"])
    assert result.exit_code == 1
    assert "No profiles found" in result.output


# ── diff: sections and entries present on only one side ──────────────


def test_diff_reports_sections_and_entries_only_on_one_side(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / "profiles" / "narrow.yaml").write_text(
        "template: cv/modern-single\noutput_filename: narrow\n"
        "sections:\n  projects: false\n"
        "select:\n  work:\n    tags: [rust]\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["diff", "general", "narrow"])
    assert result.exit_code == 0
    assert "Template:" in result.output
    assert "only in general" in result.output


def test_diff_reports_the_other_side_too(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A and B are reported by separate branches, so both directions need a test."""
    (project_root / "profiles" / "narrow.yaml").write_text(
        "template: cv/modern-single\noutput_filename: narrow\n"
        "sections:\n  projects: false\n"
        "select:\n  work:\n    tags: [rust]\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["diff", "narrow", "general"])
    assert result.exit_code == 0
    assert "only in general" in result.output


# ── export: the non-JSON formats ─────────────────────────────────────


def test_export_markdown(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["export", "--format", "markdown"])
    assert result.exit_code == 0
    assert (project_root / "dist" / "general.resume.md").exists()


def test_export_text(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["export", "--format", "text"])
    assert result.exit_code == 0
    assert (project_root / "dist" / "general.resume.txt").exists()


def test_export_rejects_the_old_linkedin_format(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`linkedin` was renamed to `text`; the old value must fail loudly, not silently."""
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["export", "--format", "linkedin"])
    assert result.exit_code != 0


def test_export_docx(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("docx")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["export", "--format", "docx"])
    assert result.exit_code == 0
    assert (project_root / "dist" / "general.resume.docx").exists()


# ── import: data that parses but does not validate ───────────────────


def test_import_rejects_data_that_fails_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A JSON Resume can parse cleanly and still not be valid cvloom data —
    here a language entry that states a fluency but never names the language."""
    source = tmp_path / "resume.json"
    source.write_text(
        json.dumps({"basics": {"name": "Jane"}, "languages": [{"fluency": "C1"}]}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["import", str(source)])
    assert result.exit_code == 1
    assert "failed validation" in result.output


# ── match: truncation and reorder hints ──────────────────────────────


def test_match_truncates_a_long_gap_list(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Printing 200 gaps buries the ones worth acting on."""
    jd = project_root / "jd.txt"
    jd.write_text(" ".join(f"gapword{i}" for i in range(60)) + "\n")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["match", "--jd", str(jd)])
    assert result.exit_code == 0
    assert "more" in result.output


def test_match_suggests_reordering_work(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hint only fires when a later job matches the JD better than the first."""
    with (project_root / "data" / "work.yaml").open("a") as fh:
        fh.write(
            "- company: Globex\n  title: Platform Engineer\n  location: Remote\n"
            '  start_date: "2018-01"\n  end_date: "2019-12"\n'
            "  highlights:\n"
            "    - Ran Kubernetes clusters and Terraform pipelines for platform teams.\n"
            "  tags: [python]\n"
        )
    jd = project_root / "jd.txt"
    jd.write_text("We need Kubernetes and Terraform experience on our platform teams.\n")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["match", "--jd", str(jd)])
    assert result.exit_code == 0
    assert "Reorder Suggestions" in result.output


# ── the listing commands' empty and edge rows ────────────────────────


def test_list_projects_empty_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data" / "projects").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["list-projects"])
    assert result.exit_code == 0
    assert "No projects found" in result.output


def test_list_projects_truncates_a_long_description(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / "data" / "projects" / "alpha.yaml").write_text(
        "name: alpha\ndescription: " + "x" * 200 + "\ntags: [python]\n"
        'url: "https://example.com/alpha"\nstart_date: "2024-01"\n'
        "highlights:\n  - Built a CLI tool in Python used by over 500 developers every day.\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["list-projects"])
    assert result.exit_code == 0
    # Rich wraps the line, so the ellipsis can straddle a newline.
    assert "..." in result.output.replace("\n", "")
    assert "x" * 100 not in result.output


def test_list_profiles_empty_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "profiles").mkdir()
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["list-profiles"])
    assert result.exit_code == 0
    assert "No profiles found" in result.output


def test_list_profiles_shows_a_company_without_a_role(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / "profiles" / "backend.yaml").write_text(
        "template: cv/modern-single\noutput_filename: backend-cv\njob_context:\n  company: Acme\n"
    )
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["list-profiles"])
    assert result.exit_code == 0
    assert "Acme" in result.output


# ── ai command group ─────────────────────────────────────────────────

_REVIEW_JSON = json.dumps(
    {
        "overall_score": 7.5,
        "sections": [
            {
                "section": "work",
                "score": 8.0,
                "strengths": ["QUANTIFIED"],
                "weaknesses": ["THIN"],
                "suggestions": ["ADDMETRICS"],
            }
        ],
        "top_priorities": ["QUANTIFYMORE"],
    }
)

_COVER_JSON = json.dumps(
    {
        "letter": "Dear Hiring Manager, LETTERBODY.",
        "word_count": 4,
        "key_alignments": ["PYTHONMATCH"],
    }
)

_SUGGEST_JSON = json.dumps(
    {
        "suggestions": [
            {
                "section": "work",
                "entry": "Acme",
                "type": "bullet",
                "current": "OLDBULLET",
                "suggested": "NEWBULLET",
                "rationale": "WHYBULLET",
            }
        ],
        "missing_skills": ["KUBERNETES"],
        "summary": "SUMMARYLINE",
    }
)

_ALIGN_JSON = json.dumps(
    {
        "alignment_score": 6.5,
        "narrative": "NARRATIVEBODY",
        "repositioning": ["REPOSITIONME"],
        "tone_gaps": ["TONEGAP"],
        "strengths": ["ALIGNSTRENGTH"],
    }
)


def _patch_ai(monkeypatch: pytest.MonkeyPatch, content: str) -> FakeClient:
    """Configure the provider and hand every ai command the same fake client.

    Each ai command does `from cvloom.ai import get_client` inside its own body, so
    the module attribute is read at call time and patching it is what takes effect
    — the same lever tests/test_mcp_server.py uses.
    """
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://fake/v1")
    client = FakeClient(content)
    monkeypatch.setattr("cvloom.ai.get_client", lambda: client)
    return client


def _jd_file(project_root: Path) -> Path:
    jd = project_root / "jd.txt"
    jd.write_text("We need a Python developer with Kubernetes experience.\n")
    return jd


def _ai_argv(command: str, jd: Path) -> list[str]:
    if command in {"cover", "align"}:
        return ["ai", command, "--jd", str(jd)]
    return ["ai", command]


_AI_COMMANDS = ["review", "cover", "suggest", "align"]


def test_ai_config_unconfigured_lists_the_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    result = CliRunner().invoke(cli, ["ai", "config"])
    assert result.exit_code == 0
    assert "not configured" in result.output
    for var in ("CVLOOM_AI_BASE_URL", "CVLOOM_AI_API_KEY", "CVLOOM_AI_MODEL"):
        assert var in result.output


def test_ai_config_configured_hides_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://fake/v1")
    monkeypatch.setenv("CVLOOM_AI_API_KEY", "sk-secret-value")
    monkeypatch.setenv("CVLOOM_AI_MODEL", "gemma3:27b")
    result = CliRunner().invoke(cli, ["ai", "config"])
    assert result.exit_code == 0
    assert "http://fake/v1" in result.output
    assert "gemma3:27b" in result.output
    assert "sk-secret-value" not in result.output


def test_ai_config_reports_a_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://fake/v1")
    monkeypatch.delenv("CVLOOM_AI_API_KEY", raising=False)
    result = CliRunner().invoke(cli, ["ai", "config"])
    assert result.exit_code == 0
    assert "not set" in result.output


@pytest.mark.parametrize("command", _AI_COMMANDS)
def test_ai_command_without_a_provider_points_at_config(
    command: str, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    jd = _jd_file(project_root)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, _ai_argv(command, jd))
    assert result.exit_code == 1
    assert "cvloom ai config" in result.output


@pytest.mark.parametrize("command", _AI_COMMANDS)
def test_ai_command_reports_a_client_that_will_not_build(
    command: str, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`is_configured()` only checks the base URL, so the client can still refuse."""
    from cvloom.ai import AINotConfiguredError

    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://fake/v1")

    def _refuse() -> Any:
        raise AINotConfiguredError("CVLOOM_AI_BASE_URL is not set.")

    monkeypatch.setattr("cvloom.ai.get_client", _refuse)
    jd = _jd_file(project_root)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, _ai_argv(command, jd))
    assert result.exit_code == 1
    assert "Traceback" not in result.output


@pytest.mark.parametrize("command", _AI_COMMANDS)
def test_ai_command_reports_a_response_that_is_not_json(
    command: str, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A proxy returning an HTML error page is the realistic version of this."""
    _patch_ai(monkeypatch, "<html>502 Bad Gateway</html>")
    jd = _jd_file(project_root)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, _ai_argv(command, jd))
    assert result.exit_code == 1
    assert "AI error:" in result.output


def test_ai_review_renders_every_part_of_the_result(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_ai(monkeypatch, _REVIEW_JSON)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "review"])
    assert result.exit_code == 0
    assert "7.5/10" in result.output
    for token in ("QUANTIFIED", "THIN", "ADDMETRICS", "QUANTIFYMORE"):
        assert token in result.output


def test_ai_cover_prints_the_letter(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai(monkeypatch, _COVER_JSON)
    jd = _jd_file(project_root)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "cover", "--jd", str(jd)])
    assert result.exit_code == 0
    assert "LETTERBODY" in result.output
    assert "PYTHONMATCH" in result.output


def test_ai_cover_output_writes_the_file_instead_of_printing(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_ai(monkeypatch, _COVER_JSON)
    jd = _jd_file(project_root)
    out = project_root / "cover.md"
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "cover", "--jd", str(jd), "--output", str(out)])
    assert result.exit_code == 0
    assert "LETTERBODY" in out.read_text()
    assert "LETTERBODY" not in result.output


def test_ai_suggest_renders_the_suggestions(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_ai(monkeypatch, _SUGGEST_JSON)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "suggest", "--role", "Staff Engineer"])
    assert result.exit_code == 0
    assert "Staff Engineer" in result.output
    for token in ("SUMMARYLINE", "OLDBULLET", "NEWBULLET", "WHYBULLET", "KUBERNETES"):
        assert token in result.output


def test_ai_suggest_falls_back_to_the_profile_job_context(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --role the target role comes from the profile, not from nowhere:
    the `backend` profile already names the role it was written for."""
    client = _patch_ai(monkeypatch, _SUGGEST_JSON)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "suggest", "--profile", "backend"])
    assert result.exit_code == 0
    assert "Senior Engineer" in result.output
    assert "Senior Engineer" in client.calls[0]["messages"][1]["content"]


def test_ai_align_renders_every_part_of_the_result(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_ai(monkeypatch, _ALIGN_JSON)
    jd = _jd_file(project_root)
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["ai", "align", "--jd", str(jd)])
    assert result.exit_code == 0
    assert "6.5/10" in result.output
    for token in ("NARRATIVEBODY", "ALIGNSTRENGTH", "TONEGAP", "REPOSITIONME"):
        assert token in result.output
