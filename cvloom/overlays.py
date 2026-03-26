"""Apply profile overlays — per-job data patches on top of base CV data."""

from __future__ import annotations

from typing import Any

from rich.console import Console

_console = Console(stderr=True)

# Match keys used to identify entries in each array section.
_MATCH_KEYS: dict[str, str] = {
    "work": "company",
    "education": "institution",
    "projects": "name",
}


def apply_overlays(data: dict[str, Any], profile: dict[str, Any]) -> None:
    """Apply all overlay operations from *profile* onto *data* in-place."""
    overlays = profile.get("overlays")
    if not overlays:
        return

    if "basics" in overlays:
        _apply_basics_overlay(data, overlays["basics"])

    for section in ("work", "education", "projects"):
        if section in overlays:
            _apply_array_overlay(data, section, overlays[section])

    if "skills" in overlays:
        _apply_skills_overlay(data, overlays["skills"])


# ── Basics overlay ───────────────────────────────────────────────────


def _apply_basics_overlay(
    data: dict[str, Any], overlay: dict[str, Any]
) -> None:
    """Shallow-merge overlay keys into ``data["basics"]``."""
    basics = data.get("basics")
    if basics is None:
        data["basics"] = dict(overlay)
        return
    basics.update(overlay)


# ── Array section overlays (work / education / projects) ─────────────


def _match_entry(
    entry: dict[str, Any], match: dict[str, str]
) -> bool:
    """Return True if *entry* matches all field-value pairs in *match*."""
    return all(entry.get(k) == v for k, v in match.items())


def _apply_array_overlay(
    data: dict[str, Any],
    section: str,
    overlay_list: list[dict[str, Any]],
) -> None:
    """Match-and-patch entries in an array section."""
    entries: list[dict[str, Any]] = data.get(section, [])
    if not entries:
        return

    for overlay in overlay_list:
        match = overlay["match"]
        matched = False

        for i, entry in enumerate(entries):
            if not _match_entry(entry, match):
                continue
            matched = True

            if overlay.get("exclude"):
                entries[i] = None  # type: ignore[call-overload]  # mark for removal
                continue

            _apply_entry_overlay(entry, overlay)

        if not matched:
            _console.print(
                f"[yellow]Warning:[/yellow] overlay for {section} "
                f"match={match} did not match any entry."
            )

    # Remove excluded entries
    data[section] = [e for e in entries if e is not None]


def _apply_entry_overlay(
    entry: dict[str, Any], overlay: dict[str, Any]
) -> None:
    """Apply field overrides and highlight operations to a single entry."""
    # Field overrides (e.g. title)
    if "title" in overlay:
        entry["title"] = overlay["title"]

    # Highlight operations
    hl_overlay = overlay.get("highlights")
    if not hl_overlay:
        return

    highlights: list[dict[str, Any]] = entry.get("highlights", [])
    mode = hl_overlay.get("mode", "all")
    items = set(hl_overlay.get("items", []))
    replace_map: dict[str, str] = hl_overlay.get("replace", {})

    if mode == "pick":
        highlights = [h for h in highlights if h.get("id") in items]
    elif mode == "exclude":
        highlights = [h for h in highlights if h.get("id") not in items]
    # mode == "all": keep as-is

    # Apply replacements
    if replace_map:
        for h in highlights:
            hid = h.get("id")
            if hid and hid in replace_map:
                h["text"] = replace_map[hid]

    # Append extra highlights
    append = hl_overlay.get("append", [])
    for text in append:
        highlights.append({"id": None, "text": text})

    entry["highlights"] = highlights


# ── Skills overlay ───────────────────────────────────────────────────


def _apply_skills_overlay(
    data: dict[str, Any], overlay: dict[str, Any]
) -> None:
    """Filter skill categories and items."""
    skills: list[dict[str, Any]] = data.get("skills", [])
    if not skills:
        return

    include = overlay.get("include_categories")
    exclude = overlay.get("exclude_categories")

    if include is not None:
        include_set = set(include)
        skills = [s for s in skills if s["category"] in include_set]
    elif exclude is not None:
        exclude_set = set(exclude)
        skills = [s for s in skills if s["category"] not in exclude_set]

    # Per-category item overrides
    cat_overrides = overlay.get("category_overrides", {})
    for group in skills:
        override = cat_overrides.get(group["category"])
        if not override:
            continue
        exclude_items = set(override.get("exclude_items", []))
        if exclude_items:
            group["items"] = [
                item
                for item in group["items"]
                if (_item_name(item) not in exclude_items)
            ]

    data["skills"] = skills


def _item_name(item: Any) -> str:
    """Extract the display name from a skill item (string or {name, level})."""
    if isinstance(item, str):
        return item
    return str(item.get("name", ""))


# ── Validation ───────────────────────────────────────────────────────


def validate_overlays(data: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Pre-flight checks: warn on structural issues. Returns warning messages."""
    warnings: list[str] = []
    overlays = profile.get("overlays")
    if not overlays:
        return warnings

    skills_ov = overlays.get("skills", {})
    if skills_ov.get("include_categories") and skills_ov.get("exclude_categories"):
        warnings.append(
            "skills overlay: include_categories and exclude_categories "
            "are mutually exclusive — only include_categories will be used."
        )

    return warnings
