"""Shared prompt construction utilities for AI analysis features."""

from __future__ import annotations

SYSTEM_ANALYSIS = (
    "You are an expert resume and career coach with deep knowledge of ATS systems, "
    "hiring practices, and professional writing. You give honest, specific, actionable "
    "feedback. You respond only with valid JSON matching the schema provided."
)

SYSTEM_CREATIVE = (
    "You are an expert resume and career coach with deep knowledge of ATS systems, "
    "hiring practices, and professional writing. You give honest, specific, actionable "
    "feedback. Write in a clear, professional tone."
)


def cv_context_block(cv_text: str) -> str:
    """Wrap CV text in a labelled block for use in prompts."""
    return f"<cv>\n{cv_text}\n</cv>"


def jd_context_block(jd_text: str) -> str:
    """Wrap JD text in a labelled block for use in prompts."""
    return f"<job_description>\n{jd_text.strip()}\n</job_description>"
