"""Parse-risk metadata for the packaged templates.

A rating is a function of how many of the five extraction engines flag a defect:

===============  ============================================================
``ATS_SAFE``     No engine finds a defect.
``ATS_CAUTION``  Some engines find a defect, others do not.
``ATS_UNSAFE``   Every engine finds a defect.
===============  ============================================================

``tests/test_ats_ratings.py`` measures each template and fails if a declared rating
disagrees. See docs/reference/ats-readiness.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

# Extraction verdicts, worst last — `build` warns on anything but SAFE.
ATS_SAFE = "safe"
ATS_CAUTION = "caution"
ATS_UNSAFE = "unsafe"


@dataclass(frozen=True)
class TemplateInfo:
    """What a template costs and what it buys."""

    name: str
    columns: int
    ats: str
    fonts: str  # "system" (no network) | "network" (Google Fonts at render time)
    summary: str
    caveat: str = ""

    suggested_titles: Mapping[str, str] = field(default_factory=dict)
    """Section wording this design reads best with, for `profile.section_titles`.

    A suggestion, not a mechanism: the locale pack supplies one flat default per
    section key, and `profile.section_titles` is the only way to change it. This
    is where a template says what it would have called things, surfaced by
    `list-templates` — most users install from PyPI and never open a packaged
    template, so a comment inside one is invisible to exactly the people who
    would want the hint.
    """


_INFO = (
    TemplateInfo(
        name="cv/ats-clean",
        columns=1,
        ats=ATS_SAFE,
        fonts="system",
        summary="Single column, system fonts, no network. The one to upload.",
    ),
    TemplateInfo(
        name="cv/academic",
        columns=1,
        ats=ATS_SAFE,
        fonts="system",
        summary="Education-first serif CV. Runs long by convention; page cap does not apply.",
        suggested_titles=MappingProxyType(
            {
                "skills": "Technical Skills",
                "work": "Positions Held",
                "projects": "Research & Projects",
                "summary": "Research Interests",
            }
        ),
    ),
    TemplateInfo(
        name="cv/modern-single",
        columns=1,
        ats=ATS_SAFE,
        fonts="network",
        summary="Single column, slate rule system, aligned skills column.",
        suggested_titles=MappingProxyType({"summary": "About"}),
    ),
    TemplateInfo(
        name="cv/timeline-clean",
        columns=1,
        ats=ATS_SAFE,
        fonts="network",
        summary="Swiss minimal, timeline rule down the experience section.",
    ),
    TemplateInfo(
        name="cv/executive-dark",
        columns=1,
        ats=ATS_SAFE,
        fonts="network",
        summary="Carbon header band, steel accent, title-first entries.",
        suggested_titles=MappingProxyType(
            {
                "skills": "Core Competencies",
                "projects": "Notable Projects",
                "summary": "Executive Summary",
            }
        ),
    ),
    TemplateInfo(
        name="cv/sidebar-compact",
        columns=2,
        ats=ATS_CAUTION,
        fonts="network",
        summary="Two-column, coloured sidebar. Best-looking of the set for a human.",
        caveat=(
            "Under pdftotext the two columns interleave: contact details and skills land "
            "in the middle of the work history, and dates read outside their entry. The "
            "other four engines read it correctly, so this is a real risk rather than a "
            "certainty — but pdftotext is the most widely deployed of them. Send it to a "
            "person or link it from a portfolio; for a portal, upload the DOCX."
        ),
    ),
)

TEMPLATES: dict[str, TemplateInfo] = {t.name: t for t in _INFO}


def info_for(template_name: str) -> TemplateInfo | None:
    """Return metadata for *template_name*, or None for a user's own template.

    A project can point `template:` at a file of its own under `templates/`, and
    cvloom has no way to rate one it has never rendered. None means "unknown",
    which is reported as such rather than assumed safe.
    """
    return TEMPLATES.get(template_name.removesuffix(".html.j2"))
