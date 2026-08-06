"""Load and merge CV data from YAML files."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from cvloom import locale as locale_mod
from cvloom import schema, sections
from cvloom.locale import LocalePack

_console = Console(stderr=True)

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

    ``contact`` is excluded: templates guard it with ``is defined`` so a public
    build, which deletes email and phone, renders nothing rather than a blank.
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
    locale: LocalePack | None = None,
) -> dict[str, Any]:
    """Load all CV data sections and return a merged context dict.

    Args:
        data_dir: Path to the ``data/`` directory.
        private_dir: Path to the ``private/`` directory (may not exist).
        public: If True, use placeholder contact data instead of private/contact.yaml.
        locale: Pack supplying the placeholder contact. Defaults to ``en``.

    Selection by tag is not done here — see :mod:`cvloom.select`, which the
    builder applies to the loaded data. This function is I/O and merge only.
    """
    pack = locale if locale is not None else locale_mod.default_pack()
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
        result["contact"] = {"name": pack.placeholder_contact["name"]}
    else:
        _console.print(
            "[yellow]Warning:[/yellow] private/contact.yaml not found — "
            "using placeholder contact. Run with --public to silence this warning."
        )
        result["contact"] = dict(pack.placeholder_contact)

    return result


def load_profile(profile_path: Path) -> dict[str, Any]:
    """Load and return a build profile YAML file.

    A missing profile raises an error naming the profiles that do exist.
    """
    if not profile_path.exists():
        available = sorted(p.stem for p in profile_path.parent.glob("*.yaml"))
        if available:
            hint = f"Available profiles: {', '.join(available)}"
        else:
            hint = (
                f"No profiles found in {profile_path.parent}/ — "
                "run `cvloom init` from your project directory to scaffold one."
            )
        raise FileNotFoundError(f"Profile not found: {profile_path.stem}. {hint}")
    return _load_yaml(profile_path) or {}
