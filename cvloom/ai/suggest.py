"""AI-powered CV content improvement suggestions."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.analysis import SCOPE_FULL, analysis_context_block
from cvloom.ai.models import Suggestion, SuggestResult
from cvloom.ai.prompts import (
    CLOSING,
    RELATED_FINDINGS,
    SYSTEM_ANALYSIS,
    assemble,
    cv_context_block,
    locale_context_block,
    unhappy_input,
)
from cvloom.ai.provider import complete_json, cv_to_text, visible_sections
from cvloom.locale import LocalePack
from cvloom.models import ResolvedProfile

_ANALYSIS_TASK = (
    "Each finding in <analysis> names a specific problem in specific text, and the "
    "user has already seen all of them from `cvloom check`. Where a suggestion "
    "addresses one, cite it in related_findings. But do not stop there: the "
    "highest-value suggestions are the ones no rule can generate — reframing an "
    "achievement so its significance is legible to the target role, cutting an entry "
    "that dilutes the story, or surfacing something buried in a bullet that deserves "
    "its own line.\n"
)


def _build_suggest_prompt(
    cv_text: str,
    sections: list[str],
    role_context: str,
    locale: LocalePack,
    analysis: str = "",
) -> str:
    sections_str = ", ".join(sections) if sections else "all sections"
    instruction = (
        "Suggest specific improvements to this CV. "
        "Respond with valid JSON matching this schema exactly:\n"
        "{\n"
        '  "suggestions": [\n'
        "    {\n"
        '      "section": <string, section name>,\n'
        '      "entry": <string or null, e.g. company name, or null for global>,\n'
        '      "type": <"bullet"|"skill"|"reword"|"remove">,\n'
        '      "current": <string or null, existing text for reword/remove>,\n'
        '      "suggested": <string, the new or improved text>,\n'
        '      "rationale": <string, why this change improves the CV>,\n'
        '      "related_findings": [<string, a rule id from <analysis>>, ...]\n'
        "    }\n"
        "  ],\n"
        '  "missing_skills": [<string>, ...],\n'
        '  "summary": <string, 1-2 sentence overview of the main improvement areas>\n'
        "}\n\n"
        f"Sections to review: {sections_str}\n"
        "Produce 5-10 suggestions ordered by impact. Be specific — include exact wording for "
        "new bullets and rewords, built only from what the CV already states. "
        "missing_skills lists skills the role calls for that the CV does not evidence; it is "
        "a list of gaps for the candidate to consider, not skills to add to the CV.\n"
        + _ANALYSIS_TASK
        + RELATED_FINDINGS
    )
    role_block = f"<target_role>\n{role_context}\n</target_role>" if role_context else ""
    return assemble(
        locale_context_block(locale),
        instruction,
        unhappy_input("summary"),
        analysis,
        cv_context_block(cv_text),
        role_block,
        CLOSING,
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
            related_findings=s.get("related_findings") or [],
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
    cv_text = cv_to_text(resolved.data, resolved.show_sections, resolved.locale)
    shown = visible_sections(resolved)
    block = analysis_context_block(resolved, cv_text, scope=SCOPE_FULL)
    prompt = _build_suggest_prompt(cv_text, shown, role_context, resolved.locale, block.text)

    result = complete_json(
        client,
        model,
        system=SYSTEM_ANALYSIS,
        prompt=prompt,
        # Low: this command rewords the candidate's own achievements, and variety in
        # that output is fabrication, not style. `cover` keeps 0.7 — see cover.py.
        temperature=0.2,
        parse=_parse_suggest_result,
    )
    result.context_notes = list(block.notes)
    return result
