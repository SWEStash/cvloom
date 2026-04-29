"""AI-powered CV content improvement suggestions."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import Suggestion, SuggestResult
from cvloom.ai.prompts import SYSTEM_ANALYSIS, cv_context_block
from cvloom.ai.provider import cv_to_text
from cvloom.models import ResolvedProfile

_KNOWN_SECTIONS = ("work", "education", "skills", "projects")


def _build_suggest_prompt(cv_text: str, sections: list[str], role_context: str) -> str:
    sections_str = ", ".join(sections) if sections else "all sections"
    role_block = f"\n<target_role>{role_context}</target_role>\n" if role_context else ""
    return (
        cv_context_block(cv_text)
        + role_block
        + "\n\n"
        + "Suggest specific improvements to this CV. "
        + "Respond with valid JSON matching this schema exactly:\n"
        + "{\n"
        + '  "suggestions": [\n'
        + "    {\n"
        + '      "section": <string, section name>,\n'
        + '      "entry": <string or null, e.g. company name, or null for global>,\n'
        + '      "type": <"bullet"|"skill"|"reword"|"remove">,\n'
        + '      "current": <string or null, existing text for reword/remove>,\n'
        + '      "suggested": <string, the new or improved text>,\n'
        + '      "rationale": <string, why this change improves the CV>\n'
        + "    }\n"
        + "  ],\n"
        + '  "missing_skills": [<string>, ...],\n'
        + '  "summary": <string, 1-2 sentence overview of the main improvement areas>\n'
        + "}\n\n"
        + f"Sections to review: {sections_str}\n"
        + "Produce 5-10 suggestions ordered by impact. Be specific — include exact wording for "
        + "new bullets and rewords. missing_skills lists skills worth adding given the role."
    )


def _parse_suggest_result(raw_json: str) -> SuggestResult:
    data = json.loads(raw_json)
    suggestions = [
        Suggestion(
            section=s["section"],
            entry=s.get("entry"),
            type=s.get("type", "bullet"),
            current=s.get("current"),
            suggested=s.get("suggested", ""),
            rationale=s.get("rationale", ""),
        )
        for s in (data.get("suggestions") or [])
    ]
    return SuggestResult(
        suggestions=suggestions,
        missing_skills=data.get("missing_skills") or [],
        summary=data.get("summary") or "",
    )


def suggest(
    resolved: ResolvedProfile,
    client: Any,
    model: str,
    role_context: str = "",
) -> SuggestResult:
    """Generate content improvement suggestions for the CV."""
    cv_text = cv_to_text(resolved.data, resolved.show_sections)
    sections = [s for s in _KNOWN_SECTIONS if resolved.show_sections.get(s, True)]
    prompt = _build_suggest_prompt(cv_text, sections, role_context)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_ANALYSIS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    try:
        return _parse_suggest_result(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"AI returned invalid JSON. Raw response:\n{raw}"
        ) from exc
