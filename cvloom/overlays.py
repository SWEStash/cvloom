"""Apply profile overlays — per-job data patches on top of base CV data."""

from __future__ import annotations

from typing import Any

from cvloom import sections


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


def _apply_basics_overlay(data: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Shallow-merge overlay keys into ``data["basics"]``."""
    basics = data.get("basics")
    if basics is None:
        data["basics"] = dict(overlay)
        return
    basics.update(overlay)


# ── Array section overlays (work / education / projects) ─────────────


def _match_entry(entry: dict[str, Any], match: dict[str, str]) -> bool:
    """Return True if *entry* matches all field-value pairs in *match*."""
    return all(entry.get(k) == v for k, v in match.items())


def _apply_array_overlay(
    data: dict[str, Any],
    section: str,
    overlay_list: list[dict[str, Any]],
) -> None:
    """Match-and-patch entries in an array section.

    Unmatched overlays are not warned about here — ``validate_overlays`` reports
    them (once) to the caller.
    """
    entries: list[dict[str, Any]] = data.get(section, [])
    if not entries:
        return

    excluded: set[int] = set()
    for overlay in overlay_list:
        match = overlay["match"]
        for i, entry in enumerate(entries):
            if not _match_entry(entry, match):
                continue
            if overlay.get("exclude"):
                excluded.add(i)
                continue
            _apply_entry_overlay(entry, overlay)

    if excluded:
        data[section] = [e for i, e in enumerate(entries) if i not in excluded]


def _apply_entry_overlay(entry: dict[str, Any], overlay: dict[str, Any]) -> None:
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


def _apply_skills_overlay(data: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Override the items within a skill category.

    Choosing *which* categories appear is selection, not patching, and lives in
    :mod:`cvloom.select` under ``select.skills``.
    """
    skills: list[dict[str, Any]] = data.get("skills", [])
    if not skills:
        return

    # Per-category item overrides
    cat_overrides = overlay.get("category_overrides", {})
    for group in skills:
        override = cat_overrides.get(group["category"])
        if not override:
            continue
        exclude_items = set(override.get("exclude_items", []))
        if exclude_items:
            group["items"] = [
                item for item in group["items"] if (sections.skill_name(item) not in exclude_items)
            ]

    data["skills"] = skills


# ── Validation ───────────────────────────────────────────────────────


_VALID_MATCH_FIELDS: dict[str, set[str]] = {
    "work": {"company", "title", "location", "start_date"},
    "education": {"institution", "degree", "field"},
    "projects": {"name"},
}


def validate_overlays(data: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Pre-flight checks: warn on structural issues. Returns warning messages."""
    warnings: list[str] = []
    overlays = profile.get("overlays")
    if not overlays:
        return warnings

    # --- Skills overlay checks ---
    skills_ov = overlays.get("skills", {})
    existing_categories = {g.get("category") for g in data.get("skills", [])}

    for cat_name in skills_ov.get("category_overrides", {}):
        if cat_name not in existing_categories:
            warnings.append(
                f"skills overlay: category_overrides references unknown category '{cat_name}'."
            )

    # --- Array section overlay checks ---
    for section in ("work", "education", "projects"):
        overlay_list = overlays.get(section, [])
        entries: list[dict[str, Any]] = data.get(section, [])
        valid_fields = _VALID_MATCH_FIELDS.get(section, set())

        for ov in overlay_list:
            match_spec = ov.get("match", {})

            # Check match field names
            for field in match_spec:
                if field not in valid_fields:
                    warnings.append(
                        f"{section} overlay: unknown match field '{field}' "
                        f"(valid: {', '.join(sorted(valid_fields))})."
                    )

            # Check if match spec matches any entry
            matched_entries = [e for e in entries if _match_entry(e, match_spec)]
            if not matched_entries:
                warnings.append(f"{section} overlay: match={match_spec} does not match any entry.")
                continue

            # Check highlight IDs in pick/exclude/replace
            hl_overlay = ov.get("highlights")
            if not hl_overlay:
                continue

            mode = hl_overlay.get("mode", "all")
            items = hl_overlay.get("items", [])
            replace_map = hl_overlay.get("replace", {})

            for entry in matched_entries:
                entry_highlights = entry.get("highlights", [])
                available_ids: set[str] = {
                    h["id"]
                    for h in entry_highlights
                    if isinstance(h, dict) and isinstance(h.get("id"), str)
                }

                if mode in ("pick", "exclude") and items:
                    for item_id in items:
                        if item_id not in available_ids:
                            label = sections.entry_label(section, entry)
                            warnings.append(
                                f"{section} overlay for {label}: highlight ID '{item_id}' "
                                f"not found (available: {', '.join(sorted(available_ids))})."
                            )

                for rid in replace_map:
                    if rid not in available_ids:
                        label = sections.entry_label(section, entry)
                        warnings.append(
                            f"{section} overlay for {label}: replace ID '{rid}' "
                            f"not found (available: {', '.join(sorted(available_ids))})."
                        )

    return warnings
