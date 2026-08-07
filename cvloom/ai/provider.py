"""AI provider configuration and CV serialization utilities.

Any OpenAI-compatible backend works (Ollama, LiteLLM proxy, OpenAI, Azure, …)
without cvloom needing vendor-specific code.

Two layers, environment winning, resolved by :func:`resolve_ai_config`:

    CVLOOM_AI_BASE_URL   e.g. http://localhost:11434/v1
    CVLOOM_AI_API_KEY    API key ("ollama" works for local Ollama)
    CVLOOM_AI_MODEL      model identifier, e.g. gemma3:27b or gpt-4o

    # cvloom.yaml
    ai:
      base_url: http://localhost:11434/v1
      model: gemma3:27b

Which backend and model a project is analysed with is a property of the project,
so it belongs in the project's file. The **credential is not expressible there**:
``cvloom.yaml`` sits at the project root and is committed. The environment wins
because a committed ``base_url`` of ``localhost`` is wrong on any other machine —
and because it makes every setup that predates the file behave identically.

The feature is disabled when no ``base_url`` resolves from either layer.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from cvloom import config, sections

_DEFAULT_MODEL = "gpt-4o"

_BASE_URL_VAR = "CVLOOM_AI_BASE_URL"
_API_KEY_VAR = "CVLOOM_AI_API_KEY"
_MODEL_VAR = "CVLOOM_AI_MODEL"

_T = TypeVar("_T")


class AINotConfiguredError(RuntimeError):
    """Raised when AI features are requested but not configured."""


@dataclass(frozen=True)
class AIConfig:
    """Resolved AI settings, with where each one came from.

    The sources are carried rather than recomputed because "which model is it
    actually using" is the question a two-layer config makes hard to answer: a
    stale exported variable silently beating an explicit file value is the
    classic confusion. ``cvloom ai config`` prints these.
    """

    base_url: str
    model: str
    api_key: str
    base_url_source: str
    model_source: str

    @property
    def configured(self) -> bool:
        return bool(self.base_url)


def _source(env_var: str, from_env: bool, from_file: bool) -> str:
    """Describe where a value came from, naming the layer it overrode."""
    if from_env:
        return f"{env_var} — overrides cvloom.yaml" if from_file else env_var
    if from_file:
        return config.CONFIG_FILENAME
    return "default"


def resolve_ai_config(root: Path | None = None) -> AIConfig:
    """Resolve AI settings for the project at *root* (default: the cwd).

    A malformed ``cvloom.yaml`` does not break AI configuration: the file layer
    is skipped and the environment answers alone, because failing `ai config`
    on an unrelated typo would hide the very output that explains the problem.
    """
    try:
        file_ai = config.load_project_config(root or Path.cwd()).ai
    except config.ConfigError:
        file_ai = config.AIConfig()

    env_base_url = os.environ.get(_BASE_URL_VAR, "").strip()
    env_model = os.environ.get(_MODEL_VAR, "").strip()

    return AIConfig(
        base_url=(env_base_url or file_ai.base_url or "").rstrip("/"),
        model=env_model or file_ai.model or _DEFAULT_MODEL,
        api_key=os.environ.get(_API_KEY_VAR, ""),
        base_url_source=_source(_BASE_URL_VAR, bool(env_base_url), bool(file_ai.base_url)),
        model_source=_source(_MODEL_VAR, bool(env_model), bool(file_ai.model)),
    )


def is_configured(root: Path | None = None) -> bool:
    """Return True if a base URL resolves for the project at *root*.

    *root* is optional so that this stays backward compatible: the Python API is
    part of the public contract, and a required parameter would break every
    existing caller.
    """
    return resolve_ai_config(root).configured


def get_client(root: Path | None = None) -> Any:
    """Return a configured OpenAI-compatible client.

    Raises AINotConfiguredError if no base URL resolves.
    Raises ImportError if the openai package is not installed.
    """
    cfg = resolve_ai_config(root)
    if not cfg.configured:
        raise AINotConfiguredError(
            f"AI features require a base URL: set {_BASE_URL_VAR}, or an `ai.base_url` "
            f"in {config.CONFIG_FILENAME}.\nRun 'cvloom ai config' for setup instructions."
        )
    try:
        import openai
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for AI features.\nInstall with: uv sync --extra ai"
        ) from exc

    return openai.OpenAI(base_url=cfg.base_url, api_key=cfg.api_key or "not-set")


def get_model(root: Path | None = None) -> str:
    """Return the configured model name, falling back to the default."""
    return resolve_ai_config(root).model


def complete_json(
    client: Any,
    model: str,
    *,
    system: str,
    prompt: str,
    temperature: float,
    parse: Callable[[str], _T],
) -> _T:
    """Run a JSON-mode chat completion and parse the response.

    Shared by all AI orchestrators: sends *system* + *prompt* at *temperature*
    with ``response_format={"type": "json_object"}``, then hands the raw content
    to *parse*. Wraps a JSON decode failure in a RuntimeError carrying the raw
    response for debugging.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    try:
        return parse(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI returned invalid JSON. Raw response:\n{raw}") from exc


def get_config(root: Path | None = None) -> dict[str, str | bool]:
    """Return a summary of the current AI configuration (safe to display).

    Carries the provenance of each value alongside it — never the key itself,
    only whether one is set.
    """
    cfg = resolve_ai_config(root)
    return {
        "configured": cfg.configured,
        "base_url": cfg.base_url,
        "base_url_source": cfg.base_url_source,
        "api_key_set": bool(cfg.api_key),
        "model": cfg.model,
        "model_source": cfg.model_source,
    }


# ---------------------------------------------------------------------------
# CV serialization
# ---------------------------------------------------------------------------


def cv_to_text(data: dict[str, Any], show_sections: dict[str, bool]) -> str:
    """Serialize resolved CV data to clean readable text for use in AI prompts.

    Respects section visibility from the resolved profile. Produces plain
    text (not YAML) that is compact, readable, and works well as LLM context.
    """
    parts: list[str] = []

    basics: dict[str, Any] = data.get("basics") or {}
    contact: dict[str, Any] = data.get("contact") or {}

    name = contact.get("name", "")
    headline = basics.get("headline", "")
    summary = basics.get("summary", "")

    header_parts = [p for p in [name, headline] if p]
    if header_parts:
        parts.append(" | ".join(header_parts))
    if summary:
        parts.append(summary.strip())

    if show_sections.get("work", True):
        work: list[dict[str, Any]] = data.get("work") or []
        if work:
            parts.append("\n## Work Experience")
            for entry in work:
                company = entry.get("company", "")
                title = entry.get("title", "")
                location = entry.get("location", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "Present")
                loc_str = f" ({location})" if location else ""
                parts.append(f"\n{company} — {title}{loc_str} | {start} – {end}")
                for h in entry.get("highlights") or []:
                    text = sections.highlight_text(h)
                    if text:
                        parts.append(f"- {text}")

    if show_sections.get("education", True):
        education: list[dict[str, Any]] = data.get("education") or []
        if education:
            parts.append("\n## Education")
            for entry in education:
                institution = entry.get("institution", "")
                degree = entry.get("degree", "")
                field = entry.get("field", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                field_str = f" in {field}" if field else ""
                date_str = f" | {start}–{end}" if start else ""
                parts.append(f"\n{institution} — {degree}{field_str}{date_str}")
                for h in entry.get("highlights") or []:
                    text = sections.highlight_text(h)
                    if text:
                        parts.append(f"- {text}")

    if show_sections.get("skills", True):
        skills: list[dict[str, Any]] = data.get("skills") or []
        if skills:
            parts.append("\n## Skills")
            for cat in skills:
                category = cat.get("category", "")
                items = cat.get("items") or []
                item_names = [sections.skill_name(item) for item in items]
                if item_names:
                    parts.append(f"{category}: {', '.join(item_names)}")

    if show_sections.get("projects", True):
        projects: list[dict[str, Any]] = data.get("projects") or []
        if projects:
            parts.append("\n## Projects")
            for entry in projects:
                name_p = entry.get("name", "")
                description = entry.get("description", "")
                tags = entry.get("tags") or []
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                parts.append(f"\n{name_p}{tag_str}")
                if description:
                    parts.append(description.strip())
                for h in entry.get("highlights") or []:
                    text = sections.highlight_text(h)
                    if text:
                        parts.append(f"- {text}")

    return "\n".join(parts)
