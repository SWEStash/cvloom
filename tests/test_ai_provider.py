"""Tests for cvloom.ai.provider — config loading and cv_to_text()."""

from __future__ import annotations

import pytest

from cvloom.ai.provider import (
    AINotConfiguredError,
    cv_to_text,
    get_config,
    get_model,
    is_configured,
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
