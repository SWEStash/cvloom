"""Parse-risk metadata for the packaged templates.

This is deliberately not part of the writing linter. ``cvloom check`` grades what
the user *wrote*; whether a layout survives PDF text extraction is a property of
the template, and no amount of editing a bullet changes it. A user who never
looks at the template list would otherwise have no way to learn that the layout
they picked interleaves its columns — the CV reads perfectly on screen, and the
failure only appears inside an ATS they cannot see.

Ratings come from rendering each template to PDF and extracting the text layer back
out with two independent extractors — pdftotext, which rebuilds columns from glyph
geometry, and pypdf, which follows the content stream. They disagree, and only what
survives both is rated safe: the constructs that broke were invisible in whichever
one we happened to try first. See ``docs/reference/ats-readiness.md``.

``ATS_CAUTION`` currently has no members. It is kept because the distinction is real
— a layout can be order-preserving but adjacency-losing — and a future template may
land there rather than at one of the extremes.
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
        summary="Carbon header band, steel accent, company-first entries.",
    ),
    TemplateInfo(
        name="cv/sidebar-compact",
        columns=2,
        ats=ATS_UNSAFE,
        fonts="network",
        summary="Two-column, coloured sidebar. Best-looking of the set for a human.",
        caveat=(
            "The two columns interleave line by line when the text layer is extracted: "
            "contact details and skills land in the middle of the work history. Send it "
            "to a person or link it from a portfolio; do not upload it to an ATS portal."
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
