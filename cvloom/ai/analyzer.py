"""AI-powered CV section scoring and feedback."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import ReviewResult, SectionScore
from cvloom.ai.prompts import (
    CLOSING,
    SYSTEM_ANALYSIS,
    assemble,
    cv_context_block,
    unhappy_input,
)
from cvloom.ai.provider import complete_json, cv_to_text, visible_sections
from cvloom.models import ResolvedProfile


def _build_review_prompt(cv_text: str, sections: list[str]) -> str:
    sections_str = ", ".join(sections) if sections else "all sections"
    instruction = (
        "Score each section of this CV. Respond with valid JSON matching this schema exactly:\n"
        "{\n"
        '  "overall_score": <float 1.0-10.0, weighted average across sections>,\n'
        '  "sections": [\n'
        "    {\n"
        '      "section": <string, section name>,\n'
        '      "score": <float 1.0-10.0>,\n'
        '      "strengths": [<string>, ...],\n'
        '      "weaknesses": [<string>, ...],\n'
        '      "suggestions": [<string>, ...]\n'
        "    }\n"
        "  ],\n"
        '  "top_priorities": [<string>, <string>, <string>]\n'
        "}\n\n"
        f"Sections to review: {sections_str}\n"
        "Be honest and specific. "
        "top_priorities lists the 3 highest-impact improvements across all sections."
    )
    return assemble(
        instruction,
        # review has no prose field of its own, so the report lands in the one
        # free-text list it does have.
        unhappy_input("the first item of top_priorities"),
        cv_context_block(cv_text),
        CLOSING,
    )


def _parse_review_result(raw_json: str) -> ReviewResult:
    data = json.loads(raw_json)
    sections = [
        SectionScore(
            section=s["section"],
            score=float(s["score"]),
            strengths=s.get("strengths") or [],
            weaknesses=s.get("weaknesses") or [],
            suggestions=s.get("suggestions") or [],
        )
        for s in (data.get("sections") or [])
    ]
    return ReviewResult(
        overall_score=float(data.get("overall_score") or 0.0),
        sections=sections,
        top_priorities=data.get("top_priorities") or [],
    )


def review(resolved: ResolvedProfile, client: Any, model: str) -> ReviewResult:
    """Score each visible CV section with AI-powered feedback."""
    cv_text = cv_to_text(resolved.data, resolved.show_sections, resolved.locale)
    shown = visible_sections(resolved)
    prompt = _build_review_prompt(cv_text, shown)

    return complete_json(
        client,
        model,
        system=SYSTEM_ANALYSIS,
        prompt=prompt,
        temperature=0.3,
        parse=_parse_review_result,
    )
