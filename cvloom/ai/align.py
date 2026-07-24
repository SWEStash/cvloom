"""AI-powered qualitative JD alignment analysis."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.models import AlignResult
from cvloom.ai.prompts import SYSTEM_ANALYSIS, cv_context_block, jd_context_block
from cvloom.ai.provider import complete_json, cv_to_text
from cvloom.match import MatchReport, analyze_match
from cvloom.models import ResolvedProfile


def _build_align_prompt(cv_text: str, jd_text: str, match_report: MatchReport) -> str:
    matched_keywords = ", ".join(m.keyword for m in match_report.matched[:20])
    gap_keywords = ", ".join(match_report.gaps[:20])
    coverage = f"{match_report.cv_keywords_coverage:.0%}"
    reorder_hints = "\n".join(match_report.reorder_hints) if match_report.reorder_hints else "none"

    keyword_block = (
        "<keyword_analysis>\n"
        f"coverage: {coverage} of unique JD keywords found in CV\n"
        f"matched: {matched_keywords or 'none'}\n"
        f"gaps: {gap_keywords or 'none'}\n"
        f"reorder hints: {reorder_hints}\n"
        "</keyword_analysis>"
    )

    return (
        cv_context_block(cv_text)
        + "\n\n"
        + jd_context_block(jd_text)
        + "\n\n"
        + keyword_block
        + "\n\n"
        + "Analyze how well this CV positions the candidate for the job description above. "
        + "The keyword analysis provides quantitative context — focus on qualitative insights "
        + "(tone, framing, narrative, positioning) that go beyond keyword matching. "
        + "Respond with valid JSON matching this schema exactly:\n"
        + "{\n"
        + '  "alignment_score": <float 1.0-10.0, overall CV-to-JD fit>,\n'
        + '  "narrative": <string, 2-3 paragraph qualitative summary of alignment>,\n'
        + '  "repositioning": [<string, concrete action ordered by impact>, ...],\n'
        + '  "tone_gaps": [<string, tone/framing mismatch>, ...],\n'
        + '  "strengths": [<string, what already aligns well>, ...]\n'
        + "}\n\n"
        + "Be specific and actionable. repositioning items should describe exact changes, "
        + "not vague advice. tone_gaps should contrast JD language with CV language."
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
    cv_text = cv_to_text(resolved.data, resolved.show_sections)
    match_report = analyze_match(resolved, jd_text)
    prompt = _build_align_prompt(cv_text, jd_text, match_report)

    return complete_json(
        client,
        model,
        system=SYSTEM_ANALYSIS,
        prompt=prompt,
        temperature=0.3,
        parse=_parse_align_result,
    )
