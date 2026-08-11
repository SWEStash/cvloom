"""AI-powered cover letter generation."""

from __future__ import annotations

import json
from typing import Any

from cvloom.ai.analysis import SCOPE_EVIDENCE, analysis_context_block
from cvloom.ai.models import CoverResult
from cvloom.ai.prompts import (
    CLOSING,
    JD_UNTRUSTED,
    SYSTEM_CREATIVE,
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


def _furniture(locale: LocalePack, job_context: dict[str, Any]) -> str:
    """Dictate the greeting and closing, in the same words the template would use.

    ``cover-letter/*.html.j2`` builds its salutation and sign-off from the pack via
    ``filters.cover_letter_text``, resolving a ``job_context`` override first. This
    mirrors that rule so the two cover-letter paths agree on the three strings the
    pack owns, instead of the AI inventing English furniture for a Spanish letter.

    Keeping the model writing the furniture (rather than stripping it afterwards)
    is what lets a later body-only mode be pure subtraction: drop this instruction
    and the template supplies the same strings from the same pack.
    """
    greeting = job_context.get("greeting") or locale.cover_letter["greeting"]
    closing = job_context.get("closing") or locale.cover_letter["closing"]
    salutee = job_context.get("hiring_manager") or locale.cover_letter["fallback_salutee"]
    return (
        f"Open the letter with exactly this salutation, on its own line: {greeting} {salutee},\n"
        f"Close with exactly {closing} on its own line, followed by the candidate's name "
        "on the line after it. Everything between those two is yours to write."
    )


def _build_cover_prompt(
    cv_text: str,
    jd_text: str,
    job_context: dict[str, Any],
    locale: LocalePack,
    match_report: MatchReport | None = None,
    analysis: str = "",
) -> str:
    instruction = (
        "Generate a tailored, professional cover letter for this role. "
        "Respond with valid JSON matching this schema exactly:\n"
        "{\n"
        '  "letter": "<full cover letter as markdown string>",\n'
        '  "word_count": <integer>,\n'
        '  "key_alignments": ["<bullet>", ...]\n'
        "}\n\n"
        "key_alignments: 3–5 brief bullets explaining why this candidate fits the role.\n"
        "Keep the letter under 400 words. Write in first person, professional tone.\n"
        "<analysis> and <keyword_analysis> report what cvloom already measured. Lead "
        "with the entries it names as carrying a quantified outcome, and address the "
        "keyword gaps in prose where the candidate's experience genuinely covers them. "
        "Neither block licenses a number the CV does not state.\n" + _furniture(locale, job_context)
    )

    _jc_keys = ("company", "role", "hiring_manager")
    _jc_labels = {"company": "Company", "role": "Role", "hiring_manager": "Hiring Manager"}
    jc_lines = [f"{_jc_labels[k]}: {job_context[k]}" for k in _jc_keys if job_context.get(k)]
    job_context_block = ""
    if jc_lines:
        job_context_block = "\n".join(["<job_context>", *jc_lines, "</job_context>"])

    return assemble(
        locale_context_block(locale),
        instruction,
        unhappy_input("letter"),
        JD_UNTRUSTED,
        analysis,
        keyword_context_block(match_report) if match_report else "",
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
    # SCOPE_EVIDENCE, so no writing-category finding reaches this prompt. That is
    # not an oversight to tidy up later: at temperature 0.7, handing a creative
    # model "No quantified outcome in this entry" is an invitation to supply the
    # number itself, which is the exact failure GROUNDING exists to prevent.
    block = analysis_context_block(resolved, cv_text, scope=SCOPE_EVIDENCE)
    match_report = analyze_match(resolved, jd_text)
    prompt = _build_cover_prompt(
        cv_text, jd_text, job_context, resolved.locale, match_report, block.text
    )

    result = complete_json(
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
    result.context_notes = list(block.notes)
    return result
