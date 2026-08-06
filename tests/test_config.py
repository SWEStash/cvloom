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
