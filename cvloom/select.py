"""Per-section content selection for a build profile.

Selection used to be split across two mechanisms. ``include_tags`` was *global* —
one tag set applied to all seven entry sections at once — so narrowing one
section silently gutted the others, and ``include_entries`` existed purely to
claw back what the global filter over-removed. Skills, meanwhile, were selected
by a different key in a different block (``overlays.skills.include_categories``).

``select`` replaces all three. It is per-section and opt-in: a section not named
in the profile is untouched. That is what makes strict semantics safe — you only
ever filter a section you deliberately named.

Selection is *which content*; overlays are *how it is edited*. Keeping the two
apart is why ``overlays.skills`` now holds only ``category_overrides``.
"""

from __future__ import annotations

from typing import Any

from cvloom import sections

_TAGS_KEY = "tags"
_CATEGORIES_KEY = "categories"
_EXCLUDE_CATEGORIES_KEY = "exclude_categories"


def _select_entries(entries: list[dict[str, Any]], tags: list[str]) -> list[dict[str, Any]]:
    """Keep entries carrying at least one of *tags*.

    An entry with no tags does not match: an include list is a query, and
    untagged content answers no query. This is uniform across every section —
    ``projects`` used to be the only strict one, an exception that existed
    because ``tags`` is required there.
    """
    wanted = set(tags)
    return [entry for entry in entries if wanted & set(entry.get("tags") or ())]


def _select_skills(
    groups: list[dict[str, Any]], categories: list[str], exclude: list[str]
) -> list[dict[str, Any]]:
    """Filter skill groups by category name, exclusion first.

    Unlike tags, categories are a *closed* set declared in ``data/skills.yaml``,
    so excluding four of fifteen is both equally expressive and far shorter than
    listing the other eleven. That asymmetry is why exclusion exists here and
    not for tags.
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

    Warnings surface the two ways a selector quietly does the wrong thing: it
    matches nothing at all, or it drops entries only because they were never
    tagged. The second is the safety net for strict semantics — a newly added,
    untagged entry vanishes from every filtered profile, and this warning is
    what stands between that and shipping a CV missing a current role.
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
