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

    sort_date_keys: tuple[str, ...] = ()
    """Date fields ranking an entry chronologically; the first present wins.

    Empty for sections with no meaningful chronology (languages).
    """

    range_keys: tuple[str, str] | None = None
    """``(start, end)`` field pair, where the section has one, for date sanity."""

    expiry_key: str = ""
    """Field carrying a credential expiry date, where the section has one."""


# Shared by the three sections that carry a start/end range.
_DATED = ("end_date", "start_date")
_RANGE = ("start_date", "end_date")

SECTIONS: tuple[Section, ...] = (
    Section(
        "work",
        "work",
        "company",
        "Work Experience",
        "work",
        warn_if_missing=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "education",
        "education",
        "institution",
        "Education",
        "edu",
        warn_if_missing=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "projects",
        "project",
        "name",
        "Projects",
        "projects",
        from_directory=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "publications",
        "publications",
        "name",
        "Publications",
        "pubs",
        sort_date_keys=("release_date",),
    ),
    Section(
        "certifications",
        "certifications",
        "name",
        "Certifications",
        "certs",
        sort_date_keys=("date",),
        expiry_key="expiry_date",
    ),
    Section("awards", "awards", "title", "Awards", "awards", sort_date_keys=("date",)),
    Section("languages", "languages", "language", "Languages", "langs"),
)

SECTIONS_BY_NAME: dict[str, Section] = {s.name: s for s in SECTIONS}

# Entry-list section names, in data-model order.
ARRAY_SECTIONS: tuple[str, ...] = tuple(s.name for s in SECTIONS)

# Every section a profile can toggle or order, including the ones with bespoke
# shapes. Order is the default render order.
#
# Work leads, skills follow it. Skills used to open the CV, which put a keyword
# block where the reader's first fixation lands: the Ladders eye-tracking work
# found recruiters fixate on job titles before anything else during the ~7s
# initial scan, and a skills wall pushes the first title down the page. Derived
# rather than written out so a new entry in SECTIONS cannot silently go missing.
_ORDER_HEAD: tuple[str, ...] = ("work", "skills")
DEFAULT_SECTION_ORDER: tuple[str, ...] = (
    *_ORDER_HEAD,
    *(name for name in ARRAY_SECTIONS if name not in _ORDER_HEAD),
)

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


# Credential kinds, following the Open Badges 3.0 achievementType vocabulary.
# The split is exam-backed credential vs completion record — the same line
# LinkedIn draws between "Licenses & Certifications" and "Courses", which is
# what makes this field a direct lookup for the LinkedIn export.
CREDENTIAL_TYPES: frozenset[str] = frozenset({"certification", "license"})
COURSEWORK_TYPES: frozenset[str] = frozenset({"course", "micro-credential"})

CREDENTIAL_HEADING = "Certifications"
COURSEWORK_HEADING = "Professional Development"

# `certifications` renders as two headed groups, so one profile key cannot rename
# both. These are the keys a profile's `section_titles` block uses for them.
CERT_GROUP_KEYS: dict[str, str] = {
    CREDENTIAL_HEADING: "certifications",
    COURSEWORK_HEADING: "professional_development",
}

# Keys a profile may rename. `summary` is here because every template heads the
# basics summary differently ("About", "Executive Summary", "Research Interests")
# and a profile should be able to say which it wants without forking a template.
TITLE_KEYS: tuple[str, ...] = (
    *DEFAULT_SECTION_ORDER,
    "summary",
    "professional_development",
    "contact",
)

# JSON Resume has no type discriminator on `certificates`, so data imported
# from elsewhere arrives untyped. Treat that as the credential case: it is what
# the section meant before the field existed.
DEFAULT_CREDENTIAL_TYPE = "certification"


def group_certifications(
    entries: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Split certification entries into their rendered groups.

    Returns ``(heading, entries)`` pairs — credentials first, coursework
    second — omitting any group with no entries, so a section of purely one
    kind renders under a single accurate heading rather than a hardcoded
    "Certifications" that overclaims a list of MOOCs.
    """
    credentials: list[dict[str, Any]] = []
    coursework: list[dict[str, Any]] = []
    for entry in entries:
        kind = str(entry.get("type") or DEFAULT_CREDENTIAL_TYPE)
        (coursework if kind in COURSEWORK_TYPES else credentials).append(entry)
    return [
        (heading, group)
        for heading, group in (
            (CREDENTIAL_HEADING, credentials),
            (COURSEWORK_HEADING, coursework),
        )
        if group
    ]


def ordered_runs(section: str, entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Entry runs that are each rendered as one contiguous, independently
    ordered block.

    Almost every section renders as a single run, so chronology applies to the
    whole list. Certifications render as two groups, and ordering only means
    anything *within* a group — a course newer than the credential above it is
    not out of order, because they never appear under the same heading.
    """
    if section == "certifications":
        return [group for _, group in group_certifications(entries)]
    return [entries]


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
