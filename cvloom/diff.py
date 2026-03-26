"""Profile diff — compare two resolved profiles side by side."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cvloom.models import ResolvedProfile

_MATCH_KEYS: dict[str, str] = {
    "work": "company",
    "education": "institution",
    "projects": "name",
}


@dataclass
class ProfileDiff:
    """Result of comparing two resolved profiles."""

    profile_a: str
    profile_b: str
    template_a: str
    template_b: str
    sections_only_in_a: list[str] = field(default_factory=list)
    sections_only_in_b: list[str] = field(default_factory=list)
    entries_only_in_a: dict[str, list[str]] = field(default_factory=dict)
    entries_only_in_b: dict[str, list[str]] = field(default_factory=dict)
    word_count_a: int = 0
    word_count_b: int = 0
    highlight_count_a: int = 0
    highlight_count_b: int = 0


def _visible_sections(resolved: ResolvedProfile) -> set[str]:
    return {s for s, v in resolved.show_sections.items() if v}


def _entry_labels(data: dict[str, Any], section: str) -> set[str]:
    key = _MATCH_KEYS.get(section)
    if not key:
        return set()
    return {str(e.get(key, "?")) for e in data.get(section, [])}


def _count_words(data: dict[str, Any], sections: set[str]) -> int:
    total = 0
    for section in ("work", "education", "projects"):
        if section not in sections:
            continue
        for entry in data.get(section, []):
            for k in ("title", "company", "institution", "name",
                       "description", "location", "degree", "field"):
                val = entry.get(k)
                if isinstance(val, str):
                    total += len(val.split())
            for hl in entry.get("highlights", []):
                text = hl if isinstance(hl, str) else hl.get("text", "")
                total += len(text.split())
    if "skills" in sections:
        for group in data.get("skills", []):
            total += len(group.get("category", "").split())
            for item in group.get("items", []):
                if isinstance(item, str):
                    total += len(item.split())
                else:
                    total += len(item.get("name", "").split())
    basics = data.get("basics", {})
    for k in ("headline", "summary"):
        val = basics.get(k)
        if isinstance(val, str):
            total += len(val.split())
    return total


def _count_highlights(data: dict[str, Any], sections: set[str]) -> int:
    total = 0
    for section in ("work", "education", "projects"):
        if section not in sections:
            continue
        for entry in data.get(section, []):
            total += len(entry.get("highlights", []))
    return total


def compare(
    resolved_a: ResolvedProfile,
    resolved_b: ResolvedProfile,
    name_a: str,
    name_b: str,
) -> ProfileDiff:
    """Compare two resolved profiles and return a structured diff."""
    vis_a = _visible_sections(resolved_a)
    vis_b = _visible_sections(resolved_b)

    diff = ProfileDiff(
        profile_a=name_a,
        profile_b=name_b,
        template_a=resolved_a.template_name,
        template_b=resolved_b.template_name,
        sections_only_in_a=sorted(vis_a - vis_b),
        sections_only_in_b=sorted(vis_b - vis_a),
    )

    # Compare entries in shared sections
    for section in vis_a & vis_b:
        if section not in _MATCH_KEYS:
            continue
        labels_a = _entry_labels(resolved_a.data, section)
        labels_b = _entry_labels(resolved_b.data, section)
        only_a = sorted(labels_a - labels_b)
        only_b = sorted(labels_b - labels_a)
        if only_a:
            diff.entries_only_in_a[section] = only_a
        if only_b:
            diff.entries_only_in_b[section] = only_b

    diff.word_count_a = _count_words(resolved_a.data, vis_a)
    diff.word_count_b = _count_words(resolved_b.data, vis_b)
    diff.highlight_count_a = _count_highlights(resolved_a.data, vis_a)
    diff.highlight_count_b = _count_highlights(resolved_b.data, vis_b)

    return diff
