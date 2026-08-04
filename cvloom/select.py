"""Per-section content selection for a build profile.

Per-section and opt-in: a section not named in the profile is untouched.
Selection is *which content*; overlays are *how it is edited*.
"""

from __future__ import annotations

from typing import Any

from cvloom import sections

_TAGS_KEY = "tags"
_CATEGORIES_KEY = "categories"
_EXCLUDE_CATEGORIES_KEY = "exclude_categories"


def _select_entries(entries: list[dict[str, Any]], tags: list[str]) -> list[dict[str, Any]]:
    """Keep entries carrying at least one of *tags*.

    An entry with no tags does not match. Uniform across every section.
    """
    wanted = set(tags)
    return [entry for entry in entries if wanted & set(entry.get("tags") or ())]


def _select_skills(
    groups: list[dict[str, Any]], categories: list[str], exclude: list[str]
) -> list[dict[str, Any]]:
    """Filter skill groups by category name, exclusion first.

    Categories are a closed set declared in ``data/skills.yaml``, which is why
    exclusion exists here and not for tags.
    """
    include_set, exclude_set = set(categories), set(exclude)
    result = []
    for group in groups:
        name = group.get("category", "")
        if name in exclude_set:
            continue
        if include_set and name not in include_set:
            continue
        result.append(group)
    return result


def apply_selection(data: dict[str, Any], select_cfg: dict[str, Any]) -> list[str]:
    """Filter each named section of *data* in place; return warnings.

    Warnings cover the two silent failures: a selector matching nothing, and
    entries dropped only because they were never tagged.
    """
    warnings: list[str] = []
    if not select_cfg:
        return warnings

    known = {s.name for s in sections.SECTIONS} | {"skills"}
    for name in select_cfg:
        if name not in known:
            warnings.append(f"select: unknown section '{name}' — ignored.")

    for section in sections.SECTIONS:
        selector = select_cfg.get(section.name)
        if not selector:
            continue
        tags = selector.get(_TAGS_KEY) or []
        if not tags:
            continue

        entries = data.get(section.name, [])
        kept = _select_entries(entries, tags)
        untagged = sum(1 for e in entries if not e.get("tags"))
        data[section.name] = kept

        if entries and not kept:
            warnings.append(
                f"select.{section.name}: no entry matches {sorted(set(tags))} — section is empty."
            )
        if untagged:
            noun = "entry that carries" if untagged == 1 else "entries that carry"
            warnings.append(
                f"select.{section.name}: dropped {untagged} {noun} no tags. "
                f"Tag them to keep them in this profile."
            )

    skills_selector = select_cfg.get("skills")
    if skills_selector:
        groups = data.get("skills", [])
        categories = skills_selector.get(_CATEGORIES_KEY) or []
        exclude = skills_selector.get(_EXCLUDE_CATEGORIES_KEY) or []
        existing = {g.get("category", "") for g in groups}
        for key, names in ((_CATEGORIES_KEY, categories), (_EXCLUDE_CATEGORIES_KEY, exclude)):
            for name in names:
                if name not in existing:
                    warnings.append(f"select.skills: {key} references unknown category '{name}'.")

        kept_groups = _select_skills(groups, categories, exclude)
        data["skills"] = kept_groups
        if groups and not kept_groups:
            warnings.append("select.skills: no category matches — section is empty.")

    return warnings
