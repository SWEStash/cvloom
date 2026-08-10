"""AI-powered cover letter generation."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import CoverResult
from cvloom.ai.prompts import (
    CLOSING,
    SYSTEM_CREATIVE,
    assemble,
    cv_context_block,
    jd_context_block,
)
from cvloom.ai.provider import complete_json, cv_to_text
from cvloom.models import ResolvedProfile


def _build_cover_prompt(cv_text: str, jd_text: str, job_context: dict[str, Any]) -> str:
    instruction = (
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

    _jc_keys = ("company", "role", "hiring_manager")
    _jc_labels = {"company": "Company", "role": "Role", "hiring_manager": "Hiring Manager"}
    jc_lines = [f"{_jc_labels[k]}: {job_context[k]}" for k in _jc_keys if job_context.get(k)]
    job_context_block = ""
    if jc_lines:
        job_context_block = "\n".join(["<job_context>", *jc_lines, "</job_context>"])

    return assemble(
        instruction,
        cv_context_block(cv_text),
        jd_context_block(jd_text),
        job_context_block,
        CLOSING,
    )


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
    cv_text = cv_to_text(resolved.data, resolved.show_sections, resolved.locale)
    job_context: dict[str, Any] = resolved.profile.get("job_context") or {}
    prompt = _build_cover_prompt(cv_text, jd_text, job_context)

    return complete_json(
        client,
        model,
        system=SYSTEM_CREATIVE,
        prompt=prompt,
        # Higher than the analysis commands on purpose: a cover letter is prose, and
        # its voice genuinely benefits from the variety. The grounding clause in
        # SYSTEM_CREATIVE is what keeps that variety off the facts.
        temperature=0.7,
        parse=_parse_cover_result,
    )
