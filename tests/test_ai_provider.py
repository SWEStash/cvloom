"""Tests for cvloom.ai.provider — config loading and cv_to_text()."""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom import config
from cvloom.ai.provider import (
    AINotConfiguredError,
    cv_to_text,
    get_config,
    get_model,
    is_configured,
    resolve_ai_config,
)

# ---------------------------------------------------------------------------
# is_configured / get_config
# ---------------------------------------------------------------------------


def test_not_configured_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    assert is_configured() is False


def test_configured_when_base_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://localhost:11434/v1")
    assert is_configured() is True


def test_not_configured_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "   ")
    assert is_configured() is False


def test_get_config_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    monkeypatch.delenv("CVLOOM_AI_API_KEY", raising=False)
    monkeypatch.delenv("CVLOOM_AI_MODEL", raising=False)
    cfg = get_config()
    assert cfg["configured"] is False
    assert cfg["api_key_set"] is False


def test_get_config_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("CVLOOM_AI_API_KEY", "ollama")
    monkeypatch.setenv("CVLOOM_AI_MODEL", "gemma3:27b")
    cfg = get_config()
    assert cfg["configured"] is True
    assert cfg["base_url"] == "http://localhost:11434/v1"
    assert cfg["api_key_set"] is True
    assert cfg["model"] == "gemma3:27b"


# ---------------------------------------------------------------------------
# Two layers: cvloom.yaml and the environment, environment winning
# ---------------------------------------------------------------------------


@pytest.fixture
def no_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("CVLOOM_AI_BASE_URL", "CVLOOM_AI_API_KEY", "CVLOOM_AI_MODEL"):
        monkeypatch.delenv(var, raising=False)


def _project(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cvloom.yaml").write_text(body)
    return root


def test_file_supplies_the_backend_when_the_environment_does_not(
    tmp_path: Path, no_ai_env: None
) -> None:
    """Which backend a project is analysed with is a property of the project."""
    root = _project(tmp_path, "ai:\n  base_url: http://localhost:11434/v1\n  model: gemma3:27b\n")
    cfg = resolve_ai_config(root)
    assert cfg.configured
    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.model == "gemma3:27b"
    assert cfg.base_url_source == "cvloom.yaml"
    assert cfg.model_source == "cvloom.yaml"


def test_environment_wins_and_says_so(
    tmp_path: Path, no_ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A committed `localhost` base_url is wrong on every other machine, so the
    machine has to be able to override the project — and the override has to be
    visible, or a stale exported variable is invisible."""
    root = _project(tmp_path, "ai:\n  base_url: http://localhost:11434/v1\n  model: gemma3:27b\n")
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("CVLOOM_AI_MODEL", "gpt-4o-mini")

    cfg = resolve_ai_config(root)
    assert cfg.base_url == "https://api.example.com/v1"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.base_url_source == "CVLOOM_AI_BASE_URL — overrides cvloom.yaml"
    assert cfg.model_source == "CVLOOM_AI_MODEL — overrides cvloom.yaml"


def test_environment_alone_does_not_claim_to_override_a_file(
    tmp_path: Path, no_ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "https://api.example.com/v1")
    cfg = resolve_ai_config(tmp_path)
    assert cfg.base_url_source == "CVLOOM_AI_BASE_URL"
    assert cfg.model_source == "default"
    assert cfg.model == "gpt-4o"


def test_a_project_that_pins_nothing_behaves_exactly_as_before(
    tmp_path: Path, no_ai_env: None
) -> None:
    """The primary compatibility gate: no `ai:` block means no change at all."""
    _project(tmp_path, "locale: en\n")
    cfg = resolve_ai_config(tmp_path)
    assert cfg.configured is False
    assert cfg.model == "gpt-4o"
    assert cfg.base_url_source == "default"


def test_api_key_in_the_file_is_refused_by_name(tmp_path: Path) -> None:
    """The file is committed by construction, so this is not a style preference."""
    _project(tmp_path, "ai:\n  api_key: sk-not-a-real-key\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    message = "; ".join(exc.value.errors)
    assert "cvloom.yaml" in message
    assert "committed" in message
    assert "CVLOOM_AI_API_KEY" in message


def test_a_broken_config_does_not_break_ai_configuration(
    tmp_path: Path, no_ai_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai config` is what a user runs to understand the problem; failing it on
    an unrelated typo would hide the output that explains it."""
    _project(tmp_path, "locale: 'not a locale code'\n")
    monkeypatch.setenv("CVLOOM_AI_BASE_URL", "https://api.example.com/v1")
    assert resolve_ai_config(tmp_path).configured is True


def test_is_configured_reads_the_root_it_is_given(tmp_path: Path, no_ai_env: None) -> None:
    pinned = _project(tmp_path / "pinned", "ai:\n  base_url: http://localhost:11434/v1\n")
    assert is_configured(pinned) is True
    assert is_configured(tmp_path / "bare") is False


# ---------------------------------------------------------------------------
# get_model
# ---------------------------------------------------------------------------


def test_get_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CVLOOM_AI_MODEL", raising=False)
    assert get_model() == "gpt-4o"


def test_get_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CVLOOM_AI_MODEL", "gemma3:27b")
    assert get_model() == "gemma3:27b"


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


def test_get_client_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CVLOOM_AI_BASE_URL", raising=False)
    with pytest.raises(AINotConfiguredError):
        from cvloom.ai.provider import get_client

        get_client()


# ---------------------------------------------------------------------------
# cv_to_text
# ---------------------------------------------------------------------------


def _sample_data() -> dict:
    return {
        "basics": {
            "headline": "Senior Engineer",
            "summary": "Builds scalable systems.",
        },
        "contact": {"name": "Jane Doe"},
        "work": [
            {
                "company": "Acme",
                "title": "Engineer",
                "location": "Remote",
                "start_date": "2021-01",
                "end_date": "Present",
                "highlights": ["Led rewrite.", {"id": "x", "text": "Shipped feature."}],
            }
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "BSc",
                "field": "CS",
                "start_date": "2014",
                "end_date": "2018",
                "highlights": ["GPA 3.8"],
            }
        ],
        "skills": [
            {"category": "Languages", "items": ["Python", {"name": "Go", "level": "advanced"}]},
        ],
        "projects": [
            {
                "name": "cvloom",
                "description": "A CLI tool.",
                "tags": ["python", "cli"],
                "highlights": ["Built in Python."],
            }
        ],
    }


def test_cv_to_text_includes_all_sections() -> None:
    data = _sample_data()
    show = {"work": True, "education": True, "skills": True, "projects": True}
    text = cv_to_text(data, show)
    assert "Jane Doe" in text
    assert "Senior Engineer" in text
    assert "Builds scalable systems." in text
    assert "Acme" in text
    assert "Led rewrite." in text
    assert "Shipped feature." in text
    assert "State University" in text
    assert "GPA 3.8" in text
    assert "Languages" in text
    assert "Python" in text
    assert "Go" in text
    assert "cvloom" in text
    assert "Built in Python." in text


def test_cv_to_text_respects_show_sections() -> None:
    data = _sample_data()
    show = {"work": False, "education": False, "skills": True, "projects": False}
    text = cv_to_text(data, show)
    assert "Acme" not in text
    assert "State University" not in text
    assert "cvloom" not in text
    assert "Languages" in text


def test_cv_to_text_handles_missing_sections() -> None:
    data: dict = {"basics": {"headline": "Dev", "summary": "Summary."}, "contact": {}}
    show: dict = {}
    text = cv_to_text(data, show)
    assert "Dev" in text
    assert "Summary." in text


def test_cv_to_text_handles_empty_data() -> None:
    text = cv_to_text({}, {})
    assert isinstance(text, str)
