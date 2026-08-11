"""AI-powered qualitative JD alignment analysis."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.analysis import SCOPE_BRIEF, analysis_context_block
from cvloom.ai.models import AlignResult
from cvloom.ai.prompts import (
    CLOSING,
    JD_UNTRUSTED,
    SYSTEM_ANALYSIS,
    assemble,
    cv_context_block,
    jd_context_block,
    keyword_context_block,
    locale_context_block,
    unhappy_input,
)
from cvloom.ai.provider import complete_json, cv_to_text
from cvloom.locale import LocalePack
from cvloom.match import MatchReport, analyze_match
from cvloom.models import ResolvedProfile


def _build_align_prompt(
    cv_text: str,
    jd_text: str,
    match_report: MatchReport,
    locale: LocalePack,
    analysis: str = "",
) -> str:
    keyword_block = keyword_context_block(match_report)

    instruction = (
        "Analyze how well this CV positions the candidate for the job description below. "
        "The keyword analysis provides quantitative context — focus on qualitative insights "
        "(tone, framing, narrative, positioning) that go beyond keyword matching. "
        "Respond with valid JSON matching this schema exactly:\n"
        "{\n"
        '  "alignment_score": <float 1.0-10.0, overall CV-to-JD fit>,\n'
        '  "narrative": <string, 2-3 paragraph qualitative summary of alignment>,\n'
        '  "repositioning": [<string, concrete action ordered by impact>, ...],\n'
        '  "tone_gaps": [<string, tone/framing mismatch>, ...],\n'
        '  "strengths": [<string, what already aligns well>, ...]\n'
        "}\n\n"
        "Be specific and actionable. repositioning items should describe exact changes, "
        "not vague advice. tone_gaps should contrast JD language with CV language.\n"
        "<analysis> reports what cvloom's own checks found. It carries counts rather "
        "than individual bullets on purpose: use it to judge length pressure and "
        "whether the CV's overall register matches what the job description asks for. "
        "A CV the writing rules flag repeatedly, read against a posting that demands "
        "ownership, is a tone gap even when every individual bullet is accurate."
    )
    return assemble(
        locale_context_block(locale),
        instruction,
        unhappy_input("narrative"),
        JD_UNTRUSTED,
        analysis,
        keyword_block,
        cv_context_block(cv_text),
        jd_context_block(jd_text),
        CLOSING,
    )


def _parse_align_result(raw_json: str) -> AlignResult:
    data = json.loads(raw_json)
    return AlignResult(
        alignment_score=float(data.get("alignment_score") or 0.0),
        narrative=data.get("narrative") or "",
        repositioning=data.get("repositioning") or [],
        tone_gaps=data.get("tone_gaps") or [],
        strengths=data.get("strengths") or [],
    )


def align(resolved: ResolvedProfile, jd_text: str, client: Any, model: str) -> AlignResult:
    """Qualitative AI analysis of how well the CV aligns to a job description."""
    cv_text = cv_to_text(resolved.data, resolved.show_sections, resolved.locale)
    match_report = analyze_match(resolved, jd_text)
    block = analysis_context_block(resolved, cv_text, scope=SCOPE_BRIEF)
    prompt = _build_align_prompt(cv_text, jd_text, match_report, resolved.locale, block.text)

    result = complete_json(
        client,
        model,
        system=SYSTEM_ANALYSIS,
        prompt=prompt,
        temperature=0.3,
        parse=_parse_align_result,
    )
    result.context_notes = list(block.notes)
    return result
