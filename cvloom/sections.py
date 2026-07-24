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
from typing import Any

from cvloom.models import ResolvedProfile

# Array sections whose entries carry highlights.
ARRAY_SECTIONS = ("work", "education", "projects")

# Text-bearing scalar fields on an array-section entry.
ENTRY_TEXT_FIELDS = (
    "title",
    "company",
    "institution",
    "name",
    "description",
    "location",
    "degree",
    "field",
)

# Which field labels an entry of a given array section.
SECTION_LABEL_KEY: dict[str, str] = {
    "work": "company",
    "education": "institution",
    "projects": "name",
}


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
