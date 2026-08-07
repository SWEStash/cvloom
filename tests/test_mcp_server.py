"""Tests for the MCP server tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cvloom import mcp_server
from cvloom.mcp_server import (
    ai_align_to_jd,
    ai_generate_cover,
    ai_review_cv,
    ai_suggest_improvements,
    build_cv,
    check_cv,
    create_profile,
    diff_profiles,
    export_json_resume,
    get_section,
    list_locales,
    list_profiles,
    list_projects,
    match_jd,
    trim_report,
    upsert_project,
    validate_data,
)
from cvloom.sections import slugify as _slugify
from tests.ai_fakes import FakeClient
from tests.conftest import make_project


@pytest.fixture
def project_dir(tmp_path: Path) -> str:
    """Create a minimal project structure for MCP tests."""
    make_project(
        tmp_path,
        extra={
            "data/projects/beta.yaml": (
                'name: beta\ndescription: "Another project."\ntags: [go]\n'
                'url: "https://example.com/beta"\nstart_date: "2024-01"\n'
                "highlights:\n  - Implemented a high-performance parser.\n"
            ),
            "profiles/backend.yaml": (
                "template: cv/modern-single\noutput_filename: backend-cv\n"
                "select:\n  work:\n    tags: [python]\n"
            ),
        },
    )
    return str(tmp_path)


def test_list_profiles(project_dir: str) -> None:
    result = json.loads(list_profiles(project_root=project_dir))
    assert len(result) == 2
    names = {p["name"] for p in result}
    assert "general" in names
    assert "backend" in names
    general = next(p for p in result if p["name"] == "general")
    assert general["template"] == "cv/ats-clean"


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
    config = {"template": "cv/ats-clean", "output_filename": "test-cv"}
    result = json.loads(create_profile("test", config, project_root=project_dir))
    assert "created" in result
    assert Path(result["created"]).exists()


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


# ── agent-safety: PII fence ────────────────────────────────────────

# Read/analysis tools that must never surface real contact PII in agent context.
_FENCED_READ_TOOLS = [
    lambda root: check_cv(profile="general", project_root=root),
    lambda root: trim_report(profile="general", project_root=root),
    lambda root: diff_profiles("general", "backend", project_root=root),
    lambda root: match_jd("python engineer", profile="general", project_root=root),
    lambda root: export_json_resume(profile="general", project_root=root),
]


def test_export_json_resume_fences_pii_by_default(project_dir: str) -> None:
    raw = export_json_resume(profile="general", project_root=project_dir)
    assert "test@example.com" not in raw
    assert "(555)" not in raw
    # Non-sensitive fields still export.
    assert json.loads(raw)["basics"]["name"] == "Test"


def test_export_json_resume_public_false_includes_pii(project_dir: str) -> None:
    raw = export_json_resume(profile="general", public=False, project_root=project_dir)
    assert "test@example.com" in raw


@pytest.mark.parametrize("call", _FENCED_READ_TOOLS)
def test_read_tools_do_not_leak_email_or_phone(project_dir: str, call) -> None:
    raw = call(project_dir)
    assert "test@example.com" not in raw
    assert "(555)" not in raw


def test_get_section_contact_is_explicit_pii_read(project_dir: str) -> None:
    # get_section("contact") is the deliberate, named way to read PII.
    raw = get_section("contact", project_root=project_dir)
    assert "test@example.com" in raw


# ── agent-safety: schema-validated writes ──────────────────────────


def test_create_profile_invalid_returns_structured_error(project_dir: str) -> None:
    result = json.loads(create_profile("bad", {"invalid_key": True}, project_root=project_dir))
    assert result["error"] == "Validation failed"
    assert isinstance(result["details"], list) and result["details"]
    # No partial file written.
    assert not (Path(project_dir) / "profiles" / "bad.yaml").exists()


def test_upsert_project_invalid_returns_structured_error(project_dir: str) -> None:
    # Missing required 'description' and 'tags'.
    result = json.loads(upsert_project({"name": "oops"}, project_root=project_dir))
    assert result["error"] == "Validation failed"
    assert isinstance(result["details"], list) and result["details"]
    assert not (Path(project_dir) / "data" / "projects" / "oops.yaml").exists()


def test_resolve_failure_returns_real_details_not_exit_code(project_dir: str) -> None:
    # Corrupt basics so resolve() fails; the tool must surface the actual messages.
    (Path(project_dir) / "data" / "basics.yaml").write_text("headline: 123\n")
    result = json.loads(check_cv(profile="general", project_root=project_dir))
    assert result["error"] == "resolve failed"
    assert isinstance(result["details"], list) and result["details"]
    # The old lossy "exit code 1" is gone.
    assert "exit code" not in json.dumps(result)


# ── check_cv tests ────────────────────────────────────────────────


def test_check_cv_returns_findings(project_dir: str) -> None:
    result = json.loads(check_cv(profile="general", project_root=project_dir))
    assert isinstance(result["findings"], list)


def test_check_cv_with_rule_filter(project_dir: str) -> None:
    result = json.loads(check_cv(profile="general", rule_ids=["wl-001"], project_root=project_dir))
    for finding in result["findings"]:
        assert finding["rule_id"] == "wl-001"


def test_check_cv_reports_the_coverage_behind_its_findings(project_dir: str) -> None:
    """An empty `findings` list under a locale that skipped rules is a weaker
    result than one under a locale that ran them all. Without the counts an agent
    cannot tell the two apart, and reads a partial pass as a clean one.
    """
    from cvloom import linter

    result = json.loads(check_cv(profile="general", project_root=project_dir))
    active, skipped = linter.rules_for("en")
    assert result["locale"] == "en"
    assert result["rules_run"] == len(active)
    assert result["rules_total"] == len(active) + len(skipped)
    assert [r["rule_id"] for r in result["rules_skipped"]] == [r.rule_id for r in skipped]


def test_check_cv_reports_the_projects_own_locale(tmp_path: Path) -> None:
    make_project(tmp_path, extra={"cvloom.yaml": "locale: es\n"})
    result = json.loads(check_cv(profile="general", project_root=str(tmp_path)))
    assert result["locale"] == "es"
    assert "wl-016" in [r["rule_id"] for r in result["rules_skipped"]]


# ── trim_report tests ─────────────────────────────────────────────


def test_trim_report_returns_sections(project_dir: str) -> None:
    result = json.loads(trim_report(profile="general", project_root=project_dir))
    assert "total_words" in result
    assert "sections" in result
    assert isinstance(result["sections"], list)
    if result["sections"]:
        assert "section" in result["sections"][0]


# ── diff_profiles tests ───────────────────────────────────────────


def test_diff_profiles_returns_comparison(project_dir: str) -> None:
    result = json.loads(
        diff_profiles(profile_a="general", profile_b="backend", project_root=project_dir)
    )
    assert "word_count_a" in result
    assert "word_count_b" in result
    assert "template_a" in result


# ── match_jd tests ────────────────────────────────────────────────


def test_match_jd_returns_coverage(project_dir: str) -> None:
    jd = "Python engineer with distributed systems experience"
    result = json.loads(match_jd(jd_text=jd, profile="general", project_root=project_dir))
    assert "coverage" in result
    assert "matched" in result
    assert "gaps" in result
    assert isinstance(result["matched"], list)


# ── AI tool tests (fake client, no backend) ───────────────────────


@pytest.fixture
def ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("CVLOOM_AI_MODEL", "test-model")


def _patch_client(monkeypatch: pytest.MonkeyPatch, content: str) -> FakeClient:
    client = FakeClient(content)
    # `root` is optional on get_client, so the fake takes it and ignores it.
    monkeypatch.setattr("cvloom.ai.get_client", lambda root=None: client)
    return client


def test_ai_tools_error_when_not_configured(
    project_dir: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    for tool in (ai_review_cv, ai_generate_cover, ai_suggest_improvements, ai_align_to_jd):
        result = json.loads(tool(project_root=project_dir))
        assert "not configured" in result["error"]


def test_ai_review_cv_resolve_failure_returns_structured_error(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A resolve failure inside an AI tool must return JSON, not escape uncaught.
    _patch_client(monkeypatch, "{}")
    (Path(project_dir) / "data" / "basics.yaml").write_text("headline: 123\n")
    result = json.loads(ai_review_cv(profile="general", project_root=project_dir))
    assert result["error"] == "resolve failed"
    assert isinstance(result["details"], list) and result["details"]


def test_ai_review_cv_success(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(
        monkeypatch,
        json.dumps(
            {
                "overall_score": 8.0,
                "sections": [
                    {"section": "work", "score": 8.5, "strengths": ["clear"], "weaknesses": []}
                ],
                "top_priorities": ["add metrics"],
            }
        ),
    )
    result = json.loads(ai_review_cv(profile="general", project_root=project_dir))
    assert result["overall_score"] == 8.0
    assert result["sections"][0]["section"] == "work"
    assert result["top_priorities"] == ["add metrics"]


def test_ai_settings_come_from_the_targeted_project_not_the_servers_cwd(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The case that needs root-aware AI config at all: an MCP server runs in
    whatever directory the client launched it in, which is nobody's project."""
    for var in ("CVLOOM_AI_BASE_URL", "CVLOOM_AI_MODEL"):
        monkeypatch.delenv(var, raising=False)
    Path(project_dir, "cvloom.yaml").write_text(
        "ai:\n  base_url: http://localhost:9999/v1\n  model: pinned-by-the-project\n"
    )
    monkeypatch.chdir(_elsewhere(tmp_path))

    from cvloom.ai.provider import get_model

    assert get_model() == "gpt-4o"  # the server's cwd knows nothing

    client = FakeClient(json.dumps({"suggestions": [], "summary": "ok"}))
    monkeypatch.setattr("cvloom.ai.get_client", lambda root=None: client)
    result = json.loads(ai_suggest_improvements(profile="general", project_root=project_dir))

    assert "error" not in result
    assert client.calls[0]["model"] == "pinned-by-the-project"


def test_ai_tool_error_names_the_root_it_resolved(
    project_dir: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrong root is the likely cause of "not configured" now that settings
    are per project, so the payload says which project answered."""
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    result = json.loads(ai_review_cv(profile="general", project_root=project_dir))
    assert result["project_root"] == project_dir
    assert "cvloom.yaml" in result["error"]


def test_ai_review_cv_malformed_response_returns_error(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(monkeypatch, "not { json")
    result = json.loads(ai_review_cv(profile="general", project_root=project_dir))
    assert "invalid JSON" in result["error"]


def test_ai_generate_cover_success(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(
        monkeypatch,
        json.dumps({"letter": "Dear team, hello.", "word_count": 3, "key_alignments": ["python"]}),
    )
    result = json.loads(
        ai_generate_cover(profile="general", jd_text="Python role", project_root=project_dir)
    )
    assert result["letter"] == "Dear team, hello."
    assert result["word_count"] == 3


def test_ai_generate_cover_malformed_response_returns_error(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(monkeypatch, "<oops>")
    result = json.loads(
        ai_generate_cover(profile="general", jd_text="Python role", project_root=project_dir)
    )
    assert "invalid JSON" in result["error"]


def test_ai_suggest_improvements_success(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(
        monkeypatch,
        json.dumps(
            {
                "suggestions": [
                    {
                        "section": "work",
                        "entry": "Acme",
                        "type": "bullet",
                        "current": None,
                        "suggested": "Cut costs by 20%.",
                        "rationale": "metric",
                    }
                ],
                "missing_skills": ["Docker"],
                "summary": "ok",
            }
        ),
    )
    result = json.loads(
        ai_suggest_improvements(profile="general", role="Backend", project_root=project_dir)
    )
    assert result["suggestions"][0]["suggested"] == "Cut costs by 20%."
    assert result["missing_skills"] == ["Docker"]


def test_ai_suggest_improvements_malformed_response_returns_error(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(monkeypatch, "nope")
    result = json.loads(ai_suggest_improvements(profile="general", project_root=project_dir))
    assert "invalid JSON" in result["error"]


def test_ai_align_to_jd_success(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(
        monkeypatch,
        json.dumps(
            {
                "alignment_score": 7.0,
                "narrative": "Good fit.",
                "repositioning": ["Lead with Python."],
                "tone_gaps": [],
                "strengths": ["python"],
            }
        ),
    )
    result = json.loads(
        ai_align_to_jd(profile="general", jd_text="Python role", project_root=project_dir)
    )
    assert result["alignment_score"] == 7.0
    assert result["repositioning"] == ["Lead with Python."]


def test_ai_align_to_jd_malformed_response_returns_error(
    project_dir: str, ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_client(monkeypatch, "{{bad")
    result = json.loads(
        ai_align_to_jd(profile="general", jd_text="Python role", project_root=project_dir)
    )
    assert "invalid JSON" in result["error"]


# ── project config (cvloom.yaml) ──────────────────────────────────
#
# The CLI resolves its root from the cwd; MCP takes `project_root` as an
# argument and can be pointed at a project the server process is not sitting
# in. These cover the part of the config surface the CLI tests structurally
# cannot: that the file is read from `project_root`, and that a bad one
# arrives as a JSON error rather than an exception crossing the tool boundary.


def _elsewhere(tmp_path: Path) -> Path:
    """A cwd that is not the project — and is not itself a cvloom project."""
    other = tmp_path / "elsewhere"
    other.mkdir()
    return other


def test_build_cv_reads_config_from_project_root_not_cwd(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (Path(project_dir) / "cvloom.yaml").write_text("locale: zz\n")
    monkeypatch.chdir(_elsewhere(tmp_path))
    result = json.loads(build_cv(profile="general", public=True, project_root=project_dir))
    assert result["error"] == "resolve failed"
    assert "Unknown locale 'zz'" in " ".join(result["details"])


def test_cwd_config_does_not_leak_into_an_explicit_project_root(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The inverse: a broken cvloom.yaml in the cwd must not break a build of
    a project elsewhere that has none."""
    other = _elsewhere(tmp_path)
    (other / "cvloom.yaml").write_text("locale: zz\n")
    monkeypatch.chdir(other)
    result = json.loads(
        build_cv(profile="general", public=True, skip_pdf=True, project_root=project_dir)
    )
    assert "error" not in result
    assert result["words"] > 0


def test_check_cv_reads_config_from_project_root(project_dir: str) -> None:
    """`check_cv` resolves by a different path than `build_cv` — build_project
    and resolve_project each read the config separately."""
    (Path(project_dir) / "cvloom.yaml").write_text("locale: zz\n")
    result = json.loads(check_cv(profile="general", project_root=project_dir))
    assert result["error"] == "resolve failed"
    assert "Unknown locale 'zz'" in " ".join(result["details"])


def test_bad_config_key_returns_structured_error(project_dir: str) -> None:
    """A malformed cvloom.yaml must not escape as an exception."""
    (Path(project_dir) / "cvloom.yaml").write_text("locale: en\nlocal: es\n")
    result = json.loads(validate_data(project_root=project_dir))
    assert result["valid"] is False
    assert any("cvloom.yaml" in e for e in result["errors"])


def test_valid_config_is_a_no_op(project_dir: str) -> None:
    """The invisibility contract, from the MCP side."""
    (Path(project_dir) / "cvloom.yaml").write_text("locale: en\n")
    result = json.loads(validate_data(project_root=project_dir))
    assert result["valid"] is True


def test_validate_data_names_the_locale_it_validated_under(project_dir: str) -> None:
    """Which project's settings were applied is not inferable from `valid: true`."""
    (Path(project_dir) / "cvloom.yaml").write_text("locale: es\n")
    result = json.loads(validate_data(project_root=project_dir))
    assert result["locale"] == "es"


# ── project root precedence ───────────────────────────────────────
#
# Four levels, argument → --project-root → CVLOOM_PROJECT_ROOT → cwd. The two
# server-level ones exist because clients disagree about whether they can pass
# args or env; the tests below pin the ordering between them.


def test_env_var_supplies_the_root_when_no_argument_is_given(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_elsewhere(tmp_path))
    monkeypatch.setenv(mcp_server.ROOT_ENV_VAR, project_dir)
    result = json.loads(list_profiles())
    assert any(p["name"] == "general" for p in result)


def test_argument_beats_the_env_var(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-call argument is the narrowest source and must win outright."""
    monkeypatch.setenv(mcp_server.ROOT_ENV_VAR, str(_elsewhere(tmp_path)))
    result = json.loads(list_profiles(project_root=project_dir))
    assert any(p["name"] == "general" for p in result)


def test_pinned_root_beats_the_env_var(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(mcp_server.ROOT_ENV_VAR, str(_elsewhere(tmp_path)))
    monkeypatch.setattr(mcp_server, "_pinned_root", Path(project_dir))
    result = json.loads(list_profiles())
    assert any(p["name"] == "general" for p in result)


def test_argument_beats_the_pinned_root(
    project_dir: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp_server, "_pinned_root", _elsewhere(tmp_path))
    result = json.loads(list_profiles(project_root=project_dir))
    assert any(p["name"] == "general" for p in result)


def test_cwd_is_the_last_resort(project_dir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(mcp_server.ROOT_ENV_VAR, raising=False)
    monkeypatch.setattr(mcp_server, "_pinned_root", None)
    monkeypatch.chdir(project_dir)
    result = json.loads(list_profiles())
    assert any(p["name"] == "general" for p in result)


# ── list_locales tool ─────────────────────────────────────────────


def test_list_locales_covers_every_shipped_pack() -> None:
    from cvloom import locale

    rows = json.loads(list_locales())
    assert [r["code"] for r in rows] == locale.available_locales()


def test_list_locales_reports_both_axes_separately() -> None:
    """A document pack does not imply linter data; the table must not merge them."""
    from cvloom import linter, linter_locales

    rows = {r["code"]: r for r in json.loads(list_locales())}
    active, skipped = linter.rules_for("es")
    assert rows["es"]["document_complete"] is True
    assert rows["es"]["rules_run"] == len(active)
    assert rows["es"]["rules_skipped"] == [r.rule_id for r in skipped]
    assert rows["es"]["lint_data"] == (
        "native" if "es" in linter_locales.available_locales() else "en fallback"
    )


def test_list_locales_marks_the_projects_own_locale(tmp_path: Path) -> None:
    make_project(tmp_path, extra={"cvloom.yaml": "locale: es\n"})
    rows = {r["code"]: r for r in json.loads(list_locales(project_root=str(tmp_path)))}
    assert rows["es"]["active"] is True
    assert rows["en"]["active"] is False


def test_list_locales_survives_a_broken_project_config(tmp_path: Path) -> None:
    """It answers "what does cvloom support", which is true regardless of the
    project standing in front of it — so a bad cvloom.yaml must not break it."""
    make_project(tmp_path, extra={"cvloom.yaml": "local: es\n"})
    rows = json.loads(list_locales(project_root=str(tmp_path)))
    assert not any(r["active"] for r in rows)
