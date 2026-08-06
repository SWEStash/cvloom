"""Project-level configuration: ``cvloom.yaml`` at the project root.

Settings that belong to the project as a whole rather than to one build profile.
A profile says how one output variant is rendered; this says what the project
*is*. Today that is a single key, ``locale``.

The file is optional — a project without one gets :class:`ProjectConfig`'s
defaults, which are exactly cvloom's behaviour before the file existed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from cvloom import schema

CONFIG_FILENAME = "cvloom.yaml"

DEFAULT_LOCALE = "en"


class ConfigError(Exception):
    """``cvloom.yaml`` or a locale pack could not be loaded.

    Carries the individual messages so each frontend can present them, matching
    :class:`~cvloom.builder.ResolveError`. ``builder`` translates this into a
    ``ResolveError`` so callers keep catching one pipeline error type.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "config failed")


@dataclass(frozen=True)
class ProjectConfig:
    """Parsed ``cvloom.yaml``. Defaults match cvloom's behaviour with no file."""

    locale: str = DEFAULT_LOCALE


def load_project_config(root: Path) -> ProjectConfig:
    """Load and validate ``root/cvloom.yaml``.

    An absent file is not an error — it yields the defaults. Anything present is
    validated, so a typo'd key fails here with the file path rather than being
    silently ignored.
    """
    path = root / CONFIG_FILENAME
    if not path.exists():
        return ProjectConfig()

    try:
        with path.open() as f:
            raw: Any = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError([f"{CONFIG_FILENAME}: not valid YAML: {exc}"]) from None

    # An empty file parses to None and means "no overrides", not "invalid".
    if raw is None:
        return ProjectConfig()
    if not isinstance(raw, dict):
        raise ConfigError([f"{CONFIG_FILENAME}: expected a mapping of settings"])

    errors = schema.validate("project-config", raw, source_path=CONFIG_FILENAME)
    if errors:
        raise ConfigError(errors)

    return ProjectConfig(locale=raw.get("locale", DEFAULT_LOCALE))
