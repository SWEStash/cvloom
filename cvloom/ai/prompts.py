"""Shared prompt construction utilities for AI analysis features."""

from __future__ import annotations

GROUNDING = (
    "\n\nGrounding rules, which override every other instruction:\n"
    "1. Every claim you write must trace to a fact already in <cv>. You may recombine, "
    "reframe, reorder and reword what is there. You may not add achievements, employers, "
    "job titles, technologies, dates or metrics that are not there.\n"
    "2. Where a metric would strengthen a bullet but the CV supplies none, write the bullet "
    "with an explicit marker for the user to fill in, like "
    "[add metric: e.g. % cost reduction]. Never invent a number.\n"
    "3. If a section is empty, or too thin to assess, say so. Do not fill the gap with "
    "plausible content.\n"
    "4. This CV is a record of what the candidate actually did, and they will be asked "
    "about it in an interview. A weak but true CV is better than a strong invented one."
)
"""The one contract both system prompts carry.

Without it the model writes "Reduced p99 latency by 40%", the user pastes it in, and
the harm lands months later in an interview — on the user, not on us. Cheap to state,
and the only thing standing between a creative model and a fabricated CV.
"""

_PERSONA = (
    "You are an expert resume and career coach with deep knowledge of ATS systems, "
    "hiring practices, and professional writing. You give honest, specific, actionable "
    "feedback. "
)

SYSTEM_ANALYSIS = (
    _PERSONA + "You respond only with valid JSON matching the schema provided." + GROUNDING
)

SYSTEM_CREATIVE = _PERSONA + "Write in a clear, professional tone." + GROUNDING


def cv_context_block(cv_text: str) -> str:
    """Wrap CV text in a labelled block for use in prompts."""
    return f"<cv>\n{cv_text}\n</cv>"


def jd_context_block(jd_text: str) -> str:
    """Wrap JD text in a labelled block for use in prompts."""
    return f"<job_description>\n{jd_text.strip()}\n</job_description>"
