"""Load and merge CV data from YAML files."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from cvloom import schema, sections

_console = Console(stderr=True)

# Placeholder contact used when private/contact.yaml is absent. Profile links are
# not here: they live in data/basics.yaml, which is present in every build.
_PLACEHOLDER_CONTACT: dict[str, Any] = {
    "name": "Your Name",
    "email": "your.email@example.com",
    "phone": "+1 (555) 000-0000",
    "location": "City, Country",
}

# Fields that must never appear in public builds
_SENSITIVE_FIELDS: frozenset[str] = frozenset({"email", "phone"})


def _apply_public_mode(contact: dict[str, Any]) -> dict[str, Any]:
    """Strip sensitive fields and apply public_name override for public builds."""
    result = {k: v for k, v in contact.items() if k not in _SENSITIVE_FIELDS}
    if "public_name" in result:
        result["name"] = result.pop("public_name")
    return result


def _load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f)


def normalize_optional_fields(section: str, entries: list[dict[str, Any]]) -> None:
    """Fill schema-optional keys the data file omitted, in-place.

    ``contact`` is deliberately excluded: templates guard it with ``is
    defined`` precisely so a public build — which *deletes* email and phone —
    renders nothing rather than a blank field.
    """
    defaults = schema.entry_defaults(sections.SECTIONS_BY_NAME[section].schema)
    for entry in entries:
        for key, value in defaults.items():
            entry.setdefault(key, copy.deepcopy(value))


def normalize_highlights(entries: list[dict[str, Any]]) -> None:
    """Normalize highlight strings to ``{id, text}`` dicts in-place."""
    for entry in entries:
        raw = entry.get("highlights")
        if not raw:
            continue
        normalized = []
        for item in raw:
            if isinstance(item, str):
                normalized.append({"id": None, "text": item})
            else:
                normalized.append({"id": item.get("id"), "text": item["text"]})
        entry["highlights"] = normalized


def flatten_highlights(entries: list[dict[str, Any]]) -> None:
    """Flatten ``{id, text}`` highlight dicts back to plain strings for templates."""
    for entry in entries:
        raw = entry.get("highlights")
        if not raw:
            continue
        entry["highlights"] = [item["text"] if isinstance(item, dict) else item for item in raw]


def load_data(
    data_dir: Path,
    private_dir: Path | None,
    public: bool = False,
    include_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Load all CV data sections and return a merged context dict.

    Args:
        data_dir: Path to the ``data/`` directory.
        private_dir: Path to the ``private/`` directory (may not exist).
        public: If True, use placeholder contact data instead of private/contact.yaml.
        include_tags: If given, filter projects/work/education/publications to entries
            with at least one matching tag. Only projects are filtered strictly:
            elsewhere an entry with no tags at all is always included.
    """
    result: dict[str, Any] = {}

    # basics and skills have bespoke shapes; the entry-list sections come from
    # the shared registry.
    for name, empty in (("basics", {}), ("skills", [])):
        path = data_dir / f"{name}.yaml"
        if path.exists():
            result[name] = _load_yaml(path)
        else:
            _console.print(f"[yellow]Warning:[/yellow] {path} not found — section will be empty.")
            result[name] = copy.deepcopy(empty)

    for section in sections.SECTIONS:
        if section.from_directory:
            entries: list[dict[str, Any]] = []
            section_dir = data_dir / section.name
            if section_dir.exists():
                for entry_file in sorted(section_dir.glob("*.yaml")):
                    entry = _load_yaml(entry_file)
                    if entry:
                        entries.append(entry)
            result[section.name] = entries
            continue

        path = data_dir / f"{section.name}.yaml"
        if path.exists():
            result[section.name] = _load_yaml(path) or []
        else:
            if section.warn_if_missing:
                _console.print(
                    f"[yellow]Warning:[/yellow] {path} not found — section will be empty."
                )
            result[section.name] = []

    # Apply tag filtering
    if include_tags:
        tag_set = set(include_tags)
        for section in sections.SECTIONS:
            result[section.name] = [
                entry
                for entry in result.get(section.name, [])
                if (set(entry.get("tags", [])) & tag_set)
                or (not section.strict_tags and not entry.get("tags"))
            ]

    # Contact data
    contact_path = (private_dir / "contact.yaml") if private_dir else None
    if contact_path and contact_path.exists():
        raw_contact: dict[str, Any] = _load_yaml(contact_path)
        if public:
            result["contact"] = _apply_public_mode(raw_contact)
        else:
            contact = dict(raw_contact)
            contact.pop("public_name", None)
            result["contact"] = contact
    elif public:
        # No private dir in public build — use minimal name-only placeholder
        result["contact"] = {"name": "Your Name"}
    else:
        _console.print(
            "[yellow]Warning:[/yellow] private/contact.yaml not found — "
            "using placeholder contact. Run with --public to silence this warning."
        )
        result["contact"] = copy.deepcopy(_PLACEHOLDER_CONTACT)

    return result


def load_profile(profile_path: Path) -> dict[str, Any]:
    """Load and return a build profile YAML file."""
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    return _load_yaml(profile_path) or {}
