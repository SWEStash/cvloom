"""AI-powered CV section scoring and feedback."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import ReviewResult, SectionScore
from cvloom.ai.prompts import SYSTEM_ANALYSIS, cv_context_block
from cvloom.ai.provider import cv_to_text
from cvloom.models import ResolvedProfile

_KNOWN_SECTIONS = ("work", "education", "skills", "projects")


def _build_review_prompt(cv_text: str, sections: list[str]) -> str:
    sections_str = ", ".join(sections) if sections else "all sections"
    return (
        cv_context_block(cv_text)
        + "\n\n"
        + "Score each section of this CV. Respond with valid JSON matching this schema exactly:\n"
        + "{\n"
        + '  "overall_score": <float 1.0-10.0, weighted average across sections>,\n'
        + '  "sections": [\n'
        + "    {\n"
        + '      "section": <string, section name>,\n'
        + '      "score": <float 1.0-10.0>,\n'
        + '      "strengths": [<string>, ...],\n'
        + '      "weaknesses": [<string>, ...],\n'
        + '      "suggestions": [<string>, ...]\n'
        + "    }\n"
        + "  ],\n"
        + '  "top_priorities": [<string>, <string>, <string>]\n'
        + "}\n\n"
        + f"Sections to review: {sections_str}\n"
        + "Be honest and specific. "
        + "top_priorities lists the 3 highest-impact improvements across all sections."
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
    cv_text = cv_to_text(resolved.data, resolved.show_sections)
    sections = [s for s in _KNOWN_SECTIONS if resolved.show_sections.get(s, True)]
    prompt = _build_review_prompt(cv_text, sections)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_ANALYSIS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    try:
        return _parse_review_result(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"AI returned invalid JSON. Raw response:\n{raw}"
        ) from exc
