"""The ``SECTIONS`` registry and the shared walk over CV data.

Single source of truth for the entry-list sections: loader, schema, builder, cli,
export, trim and diff all derive from it.

Invariant: after :func:`cvloom.builder.resolve`, highlights in ``work`` /
``education`` / ``projects`` are plain strings. :func:`highlight_text` also accepts
the pre-flatten ``{id, text}`` form, so it is safe in the loader/overlays zone.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Annotation-only: importing this at runtime would close the cycle
    # models -> locale -> schema -> sections -> models.
    from cvloom.models import ResolvedProfile


@dataclass(frozen=True)
class Section:
    """One entry-list CV section, and what the pipeline needs to know about it.

    These sections share a shape — a YAML list of entry dicts — so loading, tag
    filtering, validation, word counting and visibility are all driven from this
    table. Headings are not: they belong to the locale pack. ``skills`` and
    ``basics`` are absent: their shapes differ enough that including them would
    need more exceptions than it saves.
    """

    name: str
    """Data key, and the key used in a profile's ``sections`` / ``section_order``."""

    schema: str
    """JSON schema in ``cvloom/schemas/`` describing a single entry."""

    label_key: str
    """Field that labels an entry in diffs and trim reports."""

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
        "work",
        warn_if_missing=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "education",
        "education",
        "institution",
        "edu",
        warn_if_missing=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "projects",
        "project",
        "name",
        "projects",
        from_directory=True,
        sort_date_keys=_DATED,
        range_keys=_RANGE,
    ),
    Section(
        "publications",
        "publications",
        "name",
        "pubs",
        sort_date_keys=("release_date",),
    ),
    Section(
        "certifications",
        "certifications",
        "name",
        "certs",
        sort_date_keys=("date",),
        expiry_key="expiry_date",
    ),
    Section("awards", "awards", "title", "awards", sort_date_keys=("date",)),
    Section("languages", "languages", "language", "langs"),
)

SECTIONS_BY_NAME: dict[str, Section] = {s.name: s for s in SECTIONS}

# Entry-list section names, in data-model order.
ARRAY_SECTIONS: tuple[str, ...] = tuple(s.name for s in SECTIONS)

# Every section a profile can toggle or order, including the ones with bespoke
# shapes. Order is the default render order.
# Derived from SECTIONS rather than written out, so a new section cannot silently
# go missing from the default order.
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
# The split is exam-backed credential vs completion record, and it decides which
# of the two groups below an entry renders under.
CREDENTIAL_TYPES: frozenset[str] = frozenset({"certification", "license"})
COURSEWORK_TYPES: frozenset[str] = frozenset({"course", "micro-credential"})

# `certifications` renders as two headed groups, so one profile key cannot rename
# both. These are the title keys the two groups render under, in render order;
# the wording behind each comes from the locale pack.
CERT_GROUP_KEYS: tuple[str, str] = ("certifications", "professional_development")

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

    Returns ``(title_key, entries)`` pairs, credentials first and coursework
    second, omitting any empty group. The key rather than the heading, so that
    the visible wording stays the locale pack's and the profile's to decide.
    """
    credentials: list[dict[str, Any]] = []
    coursework: list[dict[str, Any]] = []
    for entry in entries:
        kind = str(entry.get("type") or DEFAULT_CREDENTIAL_TYPE)
        (coursework if kind in COURSEWORK_TYPES else credentials).append(entry)
    return [
        (title_key, group)
        for title_key, group in zip(CERT_GROUP_KEYS, (credentials, coursework), strict=True)
        if group
    ]


def ordered_runs(section: str, entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Entry runs that are each rendered as one contiguous, independently
    ordered block.

    Almost every section is a single run. Certifications render as two groups, and
    ordering only applies within a group.
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


def degree_line(entry: dict[str, Any]) -> str:
    """An education entry's degree and field, joined by the entry's own ``connector``.

    The connector is written verbatim, so it carries its own spacing:
    ``connector: " in "`` gives ``BSc in Computer Science``. Omitted, the two
    join with a single space — no language belongs to cvloom here, since the
    right connector is per entry, not per language (``Licenciatura en
    Informática`` but ``Ingeniero Informático``).
    """
    degree = str(entry.get("degree", ""))
    field = str(entry.get("field", ""))
    if not field:
        return degree
    return f"{degree}{entry.get('connector') or ' '}{field}"


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
