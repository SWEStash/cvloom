"""AI provider configuration and CV serialization utilities.

Configuration is driven entirely by environment variables so users can plug in
any OpenAI-compatible backend (Ollama, LiteLLM proxy, OpenAI, Azure, etc.)
without cvloom needing vendor-specific code.

Required env vars (all optional — feature is disabled when BASE_URL is unset):
    CVLOOM_AI_BASE_URL   e.g. http://localhost:11434/v1
    CVLOOM_AI_API_KEY    API key ("ollama" works for local Ollama)
    CVLOOM_AI_MODEL      model identifier, e.g. gemma3:27b or gpt-4o
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any, TypeVar

from cvloom import sections

_DEFAULT_MODEL = "gpt-4o"

_T = TypeVar("_T")


class AINotConfiguredError(RuntimeError):
    """Raised when AI features are requested but not configured."""


def is_configured() -> bool:
    """Return True if CVLOOM_AI_BASE_URL is set."""
    return bool(os.environ.get("CVLOOM_AI_BASE_URL", "").strip())


def get_client() -> Any:
    """Return a configured OpenAI-compatible client.

    Raises AINotConfiguredError if CVLOOM_AI_BASE_URL is not set.
    Raises ImportError if the openai package is not installed.
    """
    if not is_configured():
        raise AINotConfiguredError(
            "AI features require CVLOOM_AI_BASE_URL to be set.\n"
            "Run 'cvloom ai config' for setup instructions."
        )
    try:
        import openai
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for AI features.\nInstall with: uv sync --extra ai"
        ) from exc

    base_url = os.environ["CVLOOM_AI_BASE_URL"].rstrip("/")
    api_key = os.environ.get("CVLOOM_AI_API_KEY", "not-set")
    return openai.OpenAI(base_url=base_url, api_key=api_key)


def get_model() -> str:
    """Return the configured model name, falling back to the default."""
    return os.environ.get("CVLOOM_AI_MODEL", _DEFAULT_MODEL).strip()


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


def get_config() -> dict[str, str | bool]:
    """Return a summary of the current AI configuration (safe to display)."""
    configured = is_configured()
    base_url = os.environ.get("CVLOOM_AI_BASE_URL", "")
    api_key = os.environ.get("CVLOOM_AI_API_KEY", "")
    model = os.environ.get("CVLOOM_AI_MODEL", "")
    return {
        "configured": configured,
        "base_url": base_url,
        "api_key_set": bool(api_key),
        "model": model or f"{_DEFAULT_MODEL} (default)",
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
