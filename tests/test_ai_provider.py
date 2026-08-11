"""Tests for cvloom.ai.provider — config loading and cv_to_text()."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cvloom import config, locale, sections
from cvloom.ai.provider import (
    AINotConfiguredError,
    complete,
    complete_json,
    cv_to_text,
    get_config,
    get_model,
    is_configured,
    resolve_ai_config,
)
from tests.ai_fakes import FakeAPIStatusError, FakeClient, NoJsonModeClient, ScriptedClient

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
            "links": [{"label": "GitHub", "url": "https://example.com/jane"}],
        },
        "contact": {"name": "Jane Doe"},
        "publications": [{"name": "On Loom Theory", "publisher": "ACM", "release_date": "2022-03"}],
        "certifications": [
            {"name": "AWS SA", "issuer": "Amazon", "date": "2023", "expiry_date": "2026"}
        ],
        "awards": [{"title": "Best Paper", "awarder": "ACM", "date": "2022"}],
        "languages": [{"language": "Spanish", "fluency": "native"}],
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


def test_cv_to_text_covers_every_registry_section() -> None:
    """Every section a profile shows reaches the model, not just the original four."""
    data = _sample_data()
    show = dict.fromkeys(sections.DEFAULT_SECTION_ORDER, True)
    text = cv_to_text(data, show)
    for expected in ("On Loom Theory", "AWS SA", "Best Paper", "Spanish"):
        assert expected in text
    # Registry-driven detail: publisher, issuer, awarder and fluency all ride along.
    assert "ACM" in text
    assert "native" in text
    assert "expires 2026" in text


def test_cv_to_text_includes_links_and_skill_levels() -> None:
    text = cv_to_text(_sample_data(), {"skills": True})
    assert "https://example.com/jane" in text
    assert "Go (advanced)" in text


def test_cv_to_text_uses_locale_section_titles() -> None:
    pack, _ = locale.load_pack("es")
    text = cv_to_text(_sample_data(), {"work": True}, pack)
    assert f"## {pack.section_titles['work']}" in text


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


# ---------------------------------------------------------------------------
# complete_json — seed passthrough
# ---------------------------------------------------------------------------


class _SeedBlindClient(FakeClient):
    """A backend whose client signature predates `seed`, as several proxies do."""

    def __init__(self, response_content: str) -> None:
        super().__init__(response_content)
        self.rejected = 0

    def create(self, **kwargs: Any) -> Any:
        if "seed" in kwargs:
            self.rejected += 1
            raise TypeError("unexpected keyword argument 'seed'")
        return super().create(**kwargs)


def test_seed_is_passed_through_when_the_backend_accepts_it() -> None:
    client = FakeClient('{"ok": true}')
    complete_json(client, "m", system="s", prompt="p", temperature=0.0, parse=json.loads, seed=7)
    assert client.calls[0]["seed"] == 7


def test_a_backend_that_rejects_seed_still_answers() -> None:
    client = _SeedBlindClient('{"ok": true}')
    result = complete_json(
        client, "m", system="s", prompt="p", temperature=0.0, parse=json.loads, seed=7
    )
    assert result == {"ok": True}
    assert client.rejected == 1
    assert "seed" not in client.calls[-1]


# ---------------------------------------------------------------------------
# complete — surviving a hostile backend
# ---------------------------------------------------------------------------

_OK = '{"ok": true}'


def _complete(client: Any, prompt: str = "p", system: str = "s") -> Any:
    return complete(client, "m", system=system, prompt=prompt, temperature=0.0, parse=json.loads)


def test_a_clean_run_reports_nothing() -> None:
    """The notes channel has to stay empty on a healthy call, or the CLI prints a
    notice on every run and users learn to skip past the ones that matter."""
    completion = _complete(FakeClient(_OK))
    assert completion.value == {"ok": True}
    assert completion.notes == []
    assert completion.prompt_tokens is None


def test_complete_json_still_returns_the_bare_value() -> None:
    """The wrapper is what keeps the published Python API working."""
    client = FakeClient(_OK)
    assert complete_json(
        client, "m", system="s", prompt="p", temperature=0.0, parse=json.loads
    ) == {"ok": True}


def test_a_malformed_reply_is_reprompted_once() -> None:
    client = ScriptedClient("not { json", _OK)
    completion = _complete(client)
    assert completion.value == {"ok": True}
    assert len(client.calls) == 2


def test_the_reprompt_shows_the_model_its_own_reply_and_the_decode_error() -> None:
    """Echoing the bad reply lets the model repair it. Regenerating from scratch
    would produce different prose, which at cover's temperature is a different letter."""
    client = ScriptedClient("not { json", _OK)
    _complete(client)
    messages = client.calls[1]["messages"]
    assert messages[-2] == {"role": "assistant", "content": "not { json"}
    assert "line 1" in messages[-1]["content"]


def test_a_reprompted_run_says_so() -> None:
    completion = _complete(ScriptedClient("not { json", _OK))
    assert len(completion.notes) == 1
    assert "not valid JSON" in completion.notes[0]


def test_two_malformed_replies_raise_the_original_error() -> None:
    client = ScriptedClient("not { json", "still not { json")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        _complete(client)
    assert len(client.calls) == 2


def test_the_raised_error_carries_the_second_reply_not_the_first() -> None:
    """The first is already spent; the useful one is what the repair produced."""
    client = ScriptedClient("first bad", "second bad")
    with pytest.raises(RuntimeError, match="second bad"):
        _complete(client)


def test_a_backend_that_rejects_json_mode_still_answers() -> None:
    client = NoJsonModeClient(_OK, error=FakeAPIStatusError("bad request", 400))
    completion = _complete(client)
    assert completion.value == {"ok": True}
    assert client.rejected == 1
    assert "response_format" not in client.calls[-1]


def test_json_mode_rejection_is_detected_from_the_message_alone() -> None:
    """Not every proxy sets a status code; some just say what they refused."""
    client = NoJsonModeClient(_OK, error=Exception("unknown parameter: response_format"))
    completion = _complete(client)
    assert completion.value == {"ok": True}
    assert client.rejected == 1


def test_dropping_json_mode_is_reported() -> None:
    """Nothing enforced the JSON that came back, and the user should know that
    before trusting a review built from it."""
    completion = _complete(NoJsonModeClient(_OK, error=FakeAPIStatusError("bad request")))
    assert len(completion.notes) == 1
    assert "JSON mode" in completion.notes[0]


def test_an_unrelated_failure_is_not_retried() -> None:
    """A dead connection is not a capability to degrade; retrying it just doubles
    the wait before the same error reaches the user."""

    class _Dead(FakeClient):
        def create(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            raise Exception("connection refused")

    client = _Dead(_OK)
    with pytest.raises(Exception, match="connection refused"):
        _complete(client)
    assert len(client.calls) == 1


def test_a_persistent_rejection_propagates_after_one_retry() -> None:
    """The degradation latches, so a backend that 400s on everything cannot loop."""

    class _Always400(FakeClient):
        def create(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            raise FakeAPIStatusError("bad request", 400)

    client = _Always400(_OK)
    with pytest.raises(FakeAPIStatusError):
        _complete(client)
    assert len(client.calls) == 2


def test_a_client_blind_to_both_seed_and_json_mode_degrades_in_two_steps() -> None:
    class _Blind(FakeClient):
        def create(self, **kwargs: Any) -> Any:
            if "seed" in kwargs:
                raise TypeError("unexpected keyword argument 'seed'")
            if "response_format" in kwargs:
                raise FakeAPIStatusError("response_format is not supported", 400)
            return super().create(**kwargs)

    client = _Blind(_OK)
    completion = complete(
        client, "m", system="s", prompt="p", temperature=0.0, parse=json.loads, seed=7
    )
    assert completion.value == {"ok": True}
    assert len(client.calls) == 1  # only the successful call records
    assert "seed" not in client.calls[-1]
    assert "response_format" not in client.calls[-1]


def test_a_cropped_prompt_is_reported() -> None:
    """Ollama crops from the front and does not error, so the token count is the
    only evidence that the model never saw the instructions."""
    completion = _complete(FakeClient(_OK, prompt_tokens=200), prompt="x" * 12000)
    assert len(completion.notes) == 1
    assert "context window" in completion.notes[0]


def test_a_plausible_token_count_is_silent() -> None:
    completion = _complete(FakeClient(_OK, prompt_tokens=2000), prompt="x" * 12000)
    assert completion.notes == []


def test_a_short_prompt_never_trips_the_check() -> None:
    """Fixed template overhead dominates a short prompt, so the ratio is noise there."""
    completion = _complete(FakeClient(_OK, prompt_tokens=1), prompt="x" * 200)
    assert completion.notes == []


def test_a_response_without_usage_is_silent() -> None:
    completion = _complete(FakeClient(_OK), prompt="x" * 12000)
    assert completion.notes == []
    assert completion.prompt_tokens is None


def test_the_token_count_reaches_the_caller() -> None:
    assert _complete(FakeClient(_OK, prompt_tokens=1234)).prompt_tokens == 1234


def test_the_truncation_check_counts_the_system_prompt_too() -> None:
    """GROUNDING lives in the system prompt, and the front is what gets cropped —
    measuring only the user turn would miss exactly the loss that matters most."""
    completion = _complete(FakeClient(_OK, prompt_tokens=200), prompt="p", system="x" * 12000)
    assert len(completion.notes) == 1


def test_a_failure_carries_the_notes_that_explain_it() -> None:
    """The path where the notes matter most: a cropped prompt loses the schema,
    which is *why* the reply will not parse. Raising bare leaves the user with the
    raw body and nothing pointing at context size."""
    client = ScriptedClient("bad", "still bad", prompt_tokens=200)
    with pytest.raises(RuntimeError, match="context window"):
        _complete(client, prompt="x" * 12000)


def test_a_failure_with_nothing_to_report_keeps_the_original_message() -> None:
    with pytest.raises(RuntimeError, match=r"invalid JSON\. Raw response:\nstill bad$"):
        _complete(ScriptedClient("bad", "still bad"))
