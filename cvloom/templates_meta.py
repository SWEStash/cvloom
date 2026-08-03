"""Parse-risk metadata for the packaged templates.

This is deliberately not part of the writing linter. ``cvloom check`` grades what
the user *wrote*; whether a layout survives PDF text extraction is a property of
the template, and no amount of editing a bullet changes it. A user who never
looks at the template list would otherwise have no way to learn that the layout
they picked interleaves its columns — the CV reads perfectly on screen, and the
failure only appears inside an ATS they cannot see.

Ratings come from rendering each template to PDF and extracting the text layer back
out with five independent extractors, spanning raw content-stream order through
geometric reconstruction to the PDF structure tree. They disagree, and only what
survives all five is rated safe: the constructs that broke were invisible in whichever
one we happened to try first. Measured against worst-case content — short titles and
short bullets, which leave the widest empty bands for a column detector to find. See
``docs/reference/ats-readiness.md``.

The rating is a function of how many engines flag a defect, not a judgement call:

===============  ============================================================
``ATS_SAFE``     No engine finds a defect.
``ATS_CAUTION``  Some engines find a defect, others do not. The layout is
                 readable by most of the market and scrambled by part of it —
                 including minor flags such as alignment artefacts.
``ATS_UNSAFE``   Every engine finds a defect. Nothing reads it correctly.
===============  ============================================================

Ratings are checked against that rule by ``tests/test_ats_ratings.py``, which builds
each template, runs the defect suite per engine, and fails if the declared rating and
the measured one disagree. A rating cannot drift from reality unnoticed.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    ),
    TemplateInfo(
        name="cv/modern-single",
        columns=1,
        ats=ATS_SAFE,
        fonts="network",
        summary="Single column, slate rule system, aligned skills column.",
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
