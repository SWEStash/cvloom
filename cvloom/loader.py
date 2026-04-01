"""Load and merge CV data from YAML files."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

_console = Console(stderr=True)

# Placeholder contact used when private/contact.yaml is absent
_PLACEHOLDER_CONTACT: dict[str, Any] = {
    "name": "Your Name",
    "email": "your.email@example.com",
    "phone": "+1 (555) 000-0000",
    "location": "City, Country",
    "website": "https://yourwebsite.example.com",
    "linkedin": "yourlinkedin",
    "github": "SWEStash",
}

# Fields that must never appear in public builds
_SENSITIVE_FIELDS: frozenset[str] = frozenset({"email", "phone"})


def _apply_public_mode(contact: dict[str, Any]) -> dict[str, Any]:
    """Strip sensitive fields and apply public_name override for public builds."""
    result = {k: v for k, v in contact.items() if k not in _SENSITIVE_FIELDS}
    if "public_name" in result:
        result["name"] = result.pop("public_name")
    else:
        result.pop("public_name", None)
    return result


def _load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f)


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
        entry["highlights"] = [
            item["text"] if isinstance(item, dict) else item for item in raw
        ]


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
        include_tags: If given, filter projects/work to entries with at least one matching tag.
    """
    result: dict[str, Any] = {}

    for section in ("basics", "work", "education", "skills"):
        path = data_dir / f"{section}.yaml"
        if path.exists():
            result[section] = _load_yaml(path)
        else:
            _console.print(f"[yellow]Warning:[/yellow] {path} not found — section will be empty.")
            result[section] = [] if section in ("work", "education", "skills") else {}

    # Load projects from data/projects/*.yaml
    projects_dir = data_dir / "projects"
    projects: list[dict[str, Any]] = []
    if projects_dir.exists():
        for project_file in sorted(projects_dir.glob("*.yaml")):
            project = _load_yaml(project_file)
            if project:
                projects.append(project)
    result["projects"] = projects

    # Apply tag filtering
    if include_tags:
        tag_set = set(include_tags)
        result["projects"] = [
            p for p in result["projects"] if set(p.get("tags", [])) & tag_set
        ]
        result["work"] = [
            w for w in result.get("work", [])
            if not w.get("tags") or set(w.get("tags", [])) & tag_set
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
