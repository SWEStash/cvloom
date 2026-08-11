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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

from cvloom import config, sections
from cvloom.locale import LocalePack
from cvloom.models import ResolvedProfile

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


@dataclass(frozen=True)
class Completion(Generic[_T]):
    """A parsed completion, plus what the call itself revealed.

    ``notes`` carries what the *transport* had to give up — JSON mode refused, a
    reply reprompted, a prompt the backend appears to have cropped. That is the
    same kind of fact :class:`cvloom.ai.analysis.AnalysisBlock` carries about the
    prompt, which is why the orchestrators concatenate the two into
    ``context_notes`` rather than inventing a second channel for it.
    """

    value: _T
    prompt_tokens: int | None = None
    notes: list[str] = field(default_factory=list)


# Markers a backend uses when it means "I do not do JSON mode". Checked before the
# status code because naming the parameter is near-certain evidence, where a bare
# 400 covers a bad model name and an over-long context too.
_RESPONSE_FORMAT_MARKERS = ("response_format", "json_object", "json mode", "json schema")

_JSON_MODE_NOTE = (
    "The backend rejected JSON mode, so the reply was requested as plain text. "
    "The prompt still demands JSON, but nothing enforced it."
)
_REPROMPT_NOTE = "The first reply was not valid JSON and the model was asked to send it again."
_REPAIR_INSTRUCTION = (
    "That reply could not be parsed as JSON: {error}. Send the same content again "
    "as a single valid JSON object and nothing else — no prose, no markdown fence, "
    "no trailing commentary."
)

# Deliberately generous: English runs 3.5–4.5 chars per token, so dividing by 6
# already under-counts by a third. Requiring the backend's own count to fall below
# 60% of that under-count means a false positive needs it to report under ~40% of
# the true number, which no tokenizer difference produces — only cropping does.
_CHARS_PER_TOKEN = 6.0
_TRUNCATION_RATIO = 0.6
_TRUNCATION_FLOOR = 500


def _rejects_response_format(exc: BaseException) -> bool:
    """Whether *exc* plausibly means the backend does not support JSON mode.

    The status-code fallback is wide on purpose. An unrelated 400 costs exactly one
    retry that fails the same way; a missed rejection costs the whole command on a
    backend that simply does not implement the parameter.
    """
    text = str(exc).lower()
    if any(marker in text for marker in _RESPONSE_FORMAT_MARKERS):
        return True
    return getattr(exc, "status_code", None) in (400, 422)


def _prompt_tokens(response: Any) -> int | None:
    """The backend's own prompt-token count, or None when it does not report one.

    ``getattr`` rather than ``try``/``except``: a proxy that omits ``usage`` is an
    ordinary backend, not an error.
    """
    value = getattr(getattr(response, "usage", None), "prompt_tokens", None)
    return value if isinstance(value, int) else None


def _truncation_note(prompt_tokens: int | None, text: str) -> str | None:
    """Warn when the backend counted far fewer tokens than were sent.

    Ollama crops an over-long prompt from the *front* and does not error, and the
    front is where the system prompt's grounding contract and the instructions sit.
    A run that silently lost them still returns a confident-looking review.
    """
    if prompt_tokens is None:
        return None
    estimate = len(text) / _CHARS_PER_TOKEN
    if estimate < _TRUNCATION_FLOOR or prompt_tokens >= estimate * _TRUNCATION_RATIO:
        return None
    return (
        f"The backend counted only {prompt_tokens} prompt tokens for a prompt of "
        f"roughly {int(estimate)}. It has very likely cropped the front of the prompt "
        "to fit its context window, which is where the instructions and the grounding "
        "rules are. Raise the model's context size (num_ctx on Ollama) or build a "
        "shorter profile."
    )


def complete(
    client: Any,
    model: str,
    *,
    system: str,
    prompt: str,
    temperature: float,
    parse: Callable[[str], _T],
    seed: int | None = None,
) -> Completion[_T]:
    """Run a JSON-mode chat completion, parse it, and report what it cost.

    Sends *system* + *prompt* at *temperature* with
    ``response_format={"type": "json_object"}``, then hands the raw content to
    *parse*. Three things can go wrong with an arbitrary OpenAI-compatible backend,
    and each is survivable exactly once:

    - the client does not accept ``seed`` (*seed* makes a run reproducible where it
      is supported, and support is not universal);
    - the backend rejects ``response_format``, which several implementations 400 on;
    - the reply is not valid JSON, which one reprompt usually fixes.

    The first two are capabilities: they latch off and stay off for the rest of the
    call. The third changes the conversation instead, so it re-enters the same
    ladder rather than reopening a capability already known to fail. Only a second
    unparseable reply raises.
    """
    notes: list[str] = []
    use_seed = seed is not None
    use_response_format = True
    base = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    def _send(messages: list[dict[str, str]]) -> Any:
        nonlocal use_seed, use_response_format
        while True:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if use_response_format:
                kwargs["response_format"] = {"type": "json_object"}
            if use_seed:
                kwargs["seed"] = seed
            try:
                return client.chat.completions.create(**kwargs)
            except TypeError as exc:
                # Checked first: a client whose signature predates a parameter
                # raises before any request is made, which is the cheapest and
                # least ambiguous of the three signals.
                if use_seed:
                    use_seed = False
                    continue
                if use_response_format and _rejects_response_format(exc):
                    use_response_format = False
                    notes.append(_JSON_MODE_NOTE)
                    continue
                raise
            except Exception as exc:
                if use_response_format and _rejects_response_format(exc):
                    use_response_format = False
                    notes.append(_JSON_MODE_NOTE)
                    continue
                raise

    response = _send(base)
    raw = response.choices[0].message.content or ""
    note = _truncation_note(_prompt_tokens(response), system + prompt)
    if note:
        notes.append(note)

    try:
        value = parse(raw)
    except json.JSONDecodeError as exc:
        repair = [
            *base,
            {"role": "assistant", "content": raw},
            {"role": "user", "content": _REPAIR_INSTRUCTION.format(error=exc)},
        ]
        response = _send(repair)
        raw = response.choices[0].message.content or ""
        try:
            value = parse(raw)
        except json.JSONDecodeError as exc2:
            raise RuntimeError(f"AI returned invalid JSON. Raw response:\n{raw}") from exc2
        notes.append(_REPROMPT_NOTE)

    return Completion(value=value, prompt_tokens=_prompt_tokens(response), notes=notes)


def complete_json(
    client: Any,
    model: str,
    *,
    system: str,
    prompt: str,
    temperature: float,
    parse: Callable[[str], _T],
    seed: int | None = None,
) -> _T:
    """The parsed value alone — :func:`complete` without the call's own report.

    Kept because the Python API is part of cvloom's contract. In-tree callers use
    :func:`complete`, since a degraded call is something the user needs told.
    """
    return complete(
        client,
        model,
        system=system,
        prompt=prompt,
        temperature=temperature,
        parse=parse,
        seed=seed,
    ).value


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


# Prose fields get their own line rather than joining the headline.
_PROSE_FIELDS = ("summary", "description")

# ``degree`` and ``field`` are joined by sections.degree_line, which knows the
# entry's own connector; emitting them separately would lose it.
_HEADLINE_SKIP = frozenset({*_PROSE_FIELDS, "degree", "field"})


def _entry_dates(section: sections.Section, entry: dict[str, Any]) -> str:
    """The date fragment for an entry, driven by the registry rather than per-section keys."""
    if section.range_keys:
        start_key, end_key = section.range_keys
        start = str(entry.get(start_key, ""))
        end = str(entry.get(end_key) or "Present")
        if start:
            return f"{start} – {end}"
        return ""
    for key in section.sort_date_keys:
        value = entry.get(key)
        if value:
            return str(value)
    return ""


def _entry_lines(section: sections.Section, entry: dict[str, Any]) -> list[str]:
    """Serialize one array-section entry: headline, prose, then highlights."""
    headline = [sections.entry_label(section.name, entry)]

    if section.name == "education":
        degree = sections.degree_line(entry)
        if degree:
            headline.append(degree)

    # ENTRY_TEXT_FIELDS is the registry's own union of text-bearing scalars, so a
    # new field on any section reaches the model without a change here.
    headline += [
        str(entry[key])
        for key in sections.ENTRY_TEXT_FIELDS
        if key != section.label_key
        and key not in _HEADLINE_SKIP
        and isinstance(entry.get(key), str)
        and entry[key]
    ]

    line = " — ".join(headline)
    tags = [str(tag) for tag in entry.get("tags") or []]
    if tags:
        line += f" [{', '.join(tags)}]"
    dates = _entry_dates(section, entry)
    if dates:
        line += f" | {dates}"
    if section.expiry_key and entry.get(section.expiry_key):
        line += f" (expires {entry[section.expiry_key]})"

    lines = [f"\n{line}"]
    for key in _PROSE_FIELDS:
        prose = entry.get(key)
        if isinstance(prose, str) and prose.strip():
            lines.append(prose.strip())
    for hl in entry.get("highlights") or []:
        text = sections.highlight_text(hl)
        if text:
            lines.append(f"- {text}")
    return lines


def _skill_text(item: Any) -> str:
    """A skill's name, carrying its level where one is declared."""
    name = sections.skill_name(item)
    level = item.get("level") if isinstance(item, dict) else None
    return f"{name} ({level})" if name and level else name


def cv_to_text(
    data: dict[str, Any],
    show_sections: dict[str, bool],
    locale: LocalePack | None = None,
) -> str:
    """Serialize resolved CV data to clean readable text for use in AI prompts.

    Walks :data:`cvloom.sections.SECTIONS` so every section a profile shows reaches
    the model — a hand-written list here went stale the moment a section was added.
    ``skills`` and ``basics`` stay bespoke, for the same reason they sit outside the
    registry: their shapes differ.

    Respects section visibility from the resolved profile. Produces plain text (not
    YAML) that is compact, readable, and works well as LLM context. Headings follow
    the project's locale pack when one is passed, so the model reads the CV under the
    same words the document uses.
    """
    parts: list[str] = []
    titles = locale.section_titles if locale else {}

    def heading(name: str) -> str:
        return f"\n## {titles.get(name) or name.replace('_', ' ').title()}"

    basics: dict[str, Any] = data.get("basics") or {}
    contact: dict[str, Any] = data.get("contact") or {}

    header_parts = [p for p in [contact.get("name", ""), basics.get("headline", "")] if p]
    if header_parts:
        parts.append(" | ".join(header_parts))
    summary = basics.get("summary", "")
    if summary:
        parts.append(summary.strip())

    # Profile links carry their own lint rule (wl-010), so the model cannot judge
    # them unless it can see them.
    links = [
        f"{link.get('label') or ''} {link.get('url') or ''}".strip()
        for link in basics.get("links") or []
    ]
    if links:
        parts.append("Links: " + ", ".join(link for link in links if link))

    # DEFAULT_SECTION_ORDER, not SECTIONS, because it is the one place that knows
    # where the registry-less `skills` sits among the entry-list sections.
    for name in sections.DEFAULT_SECTION_ORDER:
        if not show_sections.get(name, True):
            continue
        if name == "skills":
            lines = _skills_lines(data.get("skills") or [])
        else:
            section = sections.SECTIONS_BY_NAME[name]
            lines = [
                line for entry in (data.get(name) or []) for line in _entry_lines(section, entry)
            ]
        if lines:
            parts.append(heading(name))
            parts += lines

    return "\n".join(parts)


def visible_sections(resolved: ResolvedProfile) -> list[str]:
    """The section names a profile shows, in render order — what the model was given."""
    return [
        name
        for name in sections.DEFAULT_SECTION_ORDER
        if resolved.show_sections.get(name, True) and (resolved.data.get(name) or [])
    ]


def _skills_lines(skills: list[dict[str, Any]]) -> list[str]:
    """One line per skill category, each item carrying its level where declared."""
    lines: list[str] = []
    for cat in skills:
        items = [_skill_text(item) for item in cat.get("items") or []]
        named = [item for item in items if item]
        if named:
            lines.append(f"{cat.get('category', '')}: {', '.join(named)}")
    return lines
