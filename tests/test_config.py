"""Tests for ``cvloom.yaml`` project configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom import config


def _write(root: Path, text: str) -> Path:
    (root / config.CONFIG_FILENAME).write_text(text)
    return root


def test_absent_file_yields_defaults(tmp_path: Path) -> None:
    """No cvloom.yaml is the normal case, not an error."""
    assert config.load_project_config(tmp_path) == config.ProjectConfig(locale="en")


def test_empty_file_yields_defaults(tmp_path: Path) -> None:
    """An empty file parses to None and means 'no overrides'."""
    _write(tmp_path, "")
    assert config.load_project_config(tmp_path).locale == "en"


def test_locale_is_read(tmp_path: Path) -> None:
    _write(tmp_path, "locale: es\n")
    assert config.load_project_config(tmp_path).locale == "es"


def test_regional_locale_is_accepted(tmp_path: Path) -> None:
    _write(tmp_path, "locale: pt-BR\n")
    assert config.load_project_config(tmp_path).locale == "pt-BR"


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    """additionalProperties: false — a typo must fail rather than be ignored."""
    _write(tmp_path, "locale: en\nlocal: es\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert any(config.CONFIG_FILENAME in e for e in exc.value.errors)


def test_ai_block_is_read(tmp_path: Path) -> None:
    _write(tmp_path, "ai:\n  base_url: http://localhost:11434/v1\n  model: gemma3:27b\n")
    cfg = config.load_project_config(tmp_path)
    assert cfg.ai.base_url == "http://localhost:11434/v1"
    assert cfg.ai.model == "gemma3:27b"


def test_no_ai_block_yields_empty_settings(tmp_path: Path) -> None:
    _write(tmp_path, "locale: en\n")
    assert config.load_project_config(tmp_path).ai == config.AIConfig()


def test_unknown_ai_key_is_rejected(tmp_path: Path) -> None:
    """`additionalProperties: false` on the block, so `temperature:` fails here
    rather than being silently ignored until someone wonders why it did nothing."""
    _write(tmp_path, "ai:\n  temperature: 0.7\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert any(config.CONFIG_FILENAME in e for e in exc.value.errors)


def test_api_key_is_refused_with_its_own_message(tmp_path: Path) -> None:
    """The schema would reject it too, but "additional properties are not
    allowed" does not tell a user that the file they put a secret in is tracked."""
    _write(tmp_path, "ai:\n  api_key: sk-not-a-real-key\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    message = "; ".join(exc.value.errors)
    assert config.CONFIG_FILENAME in message
    assert "committed" in message
    assert "CVLOOM_AI_API_KEY" in message


@pytest.mark.parametrize("spelling", ["api_key", "API_KEY", "api-key", "apiKey"])
def test_api_key_is_refused_however_it_is_spelled(spelling: str, tmp_path: Path) -> None:
    """`additionalProperties` catches these anyway, but with a message about
    unexpected properties. Someone who just wrote a live credential into a
    tracked file should be told that, whichever way they capitalised it."""
    _write(tmp_path, f"ai:\n  {spelling}: sk-not-a-real-key\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert "committed" in "; ".join(exc.value.errors)


def test_malformed_locale_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "locale: English\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert exc.value.errors


def test_wrong_locale_type_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "locale: 42\n")
    with pytest.raises(config.ConfigError):
        config.load_project_config(tmp_path)


def test_invalid_yaml_is_reported_with_the_filename(tmp_path: Path) -> None:
    _write(tmp_path, "locale: [unclosed\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert config.CONFIG_FILENAME in exc.value.errors[0]


def test_non_mapping_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "- just\n- a list\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load_project_config(tmp_path)
    assert "mapping" in exc.value.errors[0]


def test_config_is_frozen() -> None:
    """Immutable so a cached or shared instance cannot drift."""
    cfg = config.ProjectConfig()
    with pytest.raises(Exception):
        cfg.locale = "es"  # type: ignore[misc]
