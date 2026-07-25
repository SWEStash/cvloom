"""Shared knowledge of the CV data model — walked in one place.

Several modules need to walk entries, extract highlight text, count words, or
label an entry. Historically each re-implemented the same field tuple and the
same ``str | {text}`` guards. These helpers are the single source of truth.

Invariant: after :func:`cvloom.builder.resolve`, highlights in ``work`` /
``education`` / ``projects`` are plain strings (see ``loader.flatten_highlights``).
:func:`highlight_text` stays tolerant of the pre-flatten ``{id, text}`` form so
it is safe in the loader/overlays zone as well.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cvloom.models import ResolvedProfile


@dataclass(frozen=True)
class Section:
    """One entry-list CV section, and what the pipeline needs to know about it.

    These five sections share a shape — a YAML list of entry dicts — so loading,
    tag filtering, validation, word counting, section visibility and export
    headings can all be driven from this one table instead of being restated in
    each module. ``skills`` and ``basics`` are deliberately absent: their entry
    shapes are genuinely different, and pretending otherwise would buy uniformity
    with a pile of exceptions.
    """

    name: str
    """Data key, and the key used in a profile's ``sections`` / ``section_order``."""

    schema: str
    """JSON schema in ``cvloom/schemas/`` describing a single entry."""

    label_key: str
    """Field that labels an entry in diffs and trim reports."""

    heading: str
    """Human-readable heading used by the Markdown and DOCX exports."""

    summary_label: str
    """Short label for the CLI's post-build section summary."""

    from_directory: bool = False
    """Entries live in ``data/<name>/*.yaml`` rather than one ``data/<name>.yaml``."""

    warn_if_missing: bool = False
    """Warn when the data file is absent. False for opt-in sections."""

    strict_tags: bool = False
    """Under ``include_tags``, drop entries with no tags at all.

    Only true for projects, where ``tags`` is a required field so an untagged
    project cannot exist. Everywhere else an untagged entry is treated as
    universally relevant and always included.
    """


SECTIONS: tuple[Section, ...] = (
    Section("work", "work", "company", "Work Experience", "work", warn_if_missing=True),
    Section("education", "education", "institution", "Education", "edu", warn_if_missing=True),
    Section(
        "projects",
        "project",
        "name",
        "Projects",
        "projects",
        from_directory=True,
        strict_tags=True,
    ),
    Section("publications", "publications", "name", "Publications", "pubs"),
    Section("certifications", "certifications", "name", "Certifications", "certs"),
    Section("awards", "awards", "title", "Awards", "awards"),
    Section("languages", "languages", "language", "Languages", "langs"),
)

SECTIONS_BY_NAME: dict[str, Section] = {s.name: s for s in SECTIONS}

# Entry-list section names, in data-model order.
ARRAY_SECTIONS: tuple[str, ...] = tuple(s.name for s in SECTIONS)

# Every section a profile can toggle or order, including the ones with bespoke
# shapes. Order is the default render order.
DEFAULT_SECTION_ORDER: tuple[str, ...] = ("skills", *ARRAY_SECTIONS)

# Which field labels an entry of a given array section.
SECTION_LABEL_KEY: dict[str, str] = {s.name: s.label_key for s in SECTIONS}

# Text-bearing scalar fields on an array-section entry. A flat union across
# sections: cheap, and harmless since a missing key simply yields nothing.
ENTRY_TEXT_FIELDS = (
    "title",
    "company",
    "institution",
    "name",
    "description",
    "location",
    "degree",
    "field",
    "publisher",
    "summary",
    "issuer",
    "awarder",
    "language",
    "fluency",
)


def highlight_text(hl: Any) -> str:
    """Plain text of a highlight — a bare string, or a ``{text}`` dict."""
    if isinstance(hl, str):
        return hl
    if isinstance(hl, dict):
        return str(hl.get("text", ""))
    return ""


def skill_name(item: Any) -> str:
    """Name of a skill item — a bare string, or a ``{name}`` dict."""
    if isinstance(item, str):
        return item
    return str(item.get("name", ""))


def entry_label(section: str, entry: dict[str, Any]) -> str:
    """Human-readable label for an entry (company / institution / name)."""
    key = SECTION_LABEL_KEY.get(section, "name")
    return str(entry.get(key, "?"))


def iter_entry_text(entry: dict[str, Any]) -> Iterable[str]:
    """Yield every text fragment in an array-section entry: scalar fields then highlights."""
    for key in ENTRY_TEXT_FIELDS:
        val = entry.get(key)
        if isinstance(val, str):
            yield val
    for hl in entry.get("highlights") or []:
        yield highlight_text(hl)


def count_words(resolved: ResolvedProfile) -> dict[str, int]:
    """Word count per visible section (work/education/projects/skills) plus basics."""
    data = resolved.data
    show = resolved.show_sections
    counts: dict[str, int] = {}

    for section in ARRAY_SECTIONS:
        if not show.get(section):
            continue
        counts[section] = sum(
            len(text.split()) for entry in data.get(section, []) for text in iter_entry_text(entry)
        )

    if show.get("skills"):
        words = 0
        for group in data.get("skills", []):
            words += len(str(group.get("category", "")).split())
            for item in group.get("items", []):
                words += len(skill_name(item).split())
        counts["skills"] = words

    basics = data.get("basics", {})
    basics_words = 0
    for key in ("headline", "summary"):
        val = basics.get(key)
        if isinstance(val, str):
            basics_words += len(val.split())
    counts["basics"] = basics_words

    return counts


def slugify(name: str, fallback: str = "untitled") -> str:
    """Turn a name into a safe filename stem, transliterating accents to ASCII."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or fallback
