"""AI-powered cover letter generation."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import CoverResult
from cvloom.ai.prompts import SYSTEM_CREATIVE, cv_context_block, jd_context_block
from cvloom.ai.provider import complete_json, cv_to_text
from cvloom.models import ResolvedProfile


def _build_cover_prompt(cv_text: str, jd_text: str, job_context: dict[str, Any]) -> str:
    parts: list[str] = []

    _jc_keys = ("company", "role", "hiring_manager")
    jc_fields = {k: job_context[k] for k in _jc_keys if job_context.get(k)}
    if jc_fields:
        lines = ["<job_context>"]
        if "company" in jc_fields:
            lines.append(f"Company: {jc_fields['company']}")
        if "role" in jc_fields:
            lines.append(f"Role: {jc_fields['role']}")
        if "hiring_manager" in jc_fields:
            lines.append(f"Hiring Manager: {jc_fields['hiring_manager']}")
        lines.append("</job_context>")
        parts.append("\n".join(lines))

    parts.append(cv_context_block(cv_text))
    parts.append(jd_context_block(jd_text))
    parts.append(
        "Generate a tailored, professional cover letter for this role. "
        "Respond with valid JSON matching this schema exactly:\n"
        "{\n"
        '  "letter": "<full cover letter as markdown string>",\n'
        '  "word_count": <integer>,\n'
        '  "key_alignments": ["<bullet>", ...]\n'
        "}\n\n"
        "key_alignments: 3–5 brief bullets explaining why this candidate fits the role.\n"
        "Keep the letter under 400 words. Write in first person, professional tone."
    )
    return "\n\n".join(parts)


def _parse_cover_result(raw_json: str) -> CoverResult:
    data = json.loads(raw_json)
    letter = data.get("letter") or ""
    word_count = int(data.get("word_count") or 0) or len(letter.split())
    return CoverResult(
        letter=letter,
        word_count=word_count,
        key_alignments=data.get("key_alignments") or [],
    )


def generate_cover(resolved: ResolvedProfile, jd_text: str, client: Any, model: str) -> CoverResult:
    """Generate a tailored cover letter for the given job description."""
    cv_text = cv_to_text(resolved.data, resolved.show_sections)
    job_context: dict[str, Any] = resolved.profile.get("job_context") or {}
    prompt = _build_cover_prompt(cv_text, jd_text, job_context)

    return complete_json(
        client,
        model,
        system=SYSTEM_CREATIVE,
        prompt=prompt,
        temperature=0.7,
        parse=_parse_cover_result,
    )
