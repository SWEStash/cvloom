"""Profile- and project-listing data layer, shared by the CLI and MCP server.

Reading and tag filtering happen here; each frontend formats the returned
summaries (a Rich table for the CLI, JSON for MCP).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProfileSummary:
    """Summary of one build profile."""

    name: str
    template: str
    output_filename: str
    selected_sections: list[str]
    """Sections the profile narrows via ``select`` — empty means "everything"."""
    job_context: dict[str, Any] | None


@dataclass
class ProjectSummary:
    """Summary of one project entry."""

    name: str
    description: str
    tags: list[str]


def list_profiles(root: Path) -> list[ProfileSummary]:
    """Return a summary for each ``profiles/*.yaml`` under *root*.

    Raises ``FileNotFoundError`` if the ``profiles/`` directory is absent.
    """
    profiles_dir = root / "profiles"
    if not profiles_dir.exists():
        raise FileNotFoundError(profiles_dir)

    summaries: list[ProfileSummary] = []
    for pf in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(pf.read_text()) or {}
        summaries.append(
            ProfileSummary(
                name=pf.stem,
                template=data.get("template", ""),
                output_filename=data.get("output_filename") or pf.stem,
                selected_sections=sorted(data.get("select") or {}),
                job_context=data.get("job_context"),
            )
        )
    return summaries


def list_projects(root: Path, tags: list[str] | None = None) -> list[ProjectSummary]:
    """Return a summary for each ``data/projects/*.yaml`` under *root*.

    When *tags* is given, only projects sharing at least one tag are returned.
    Raises ``FileNotFoundError`` if the ``data/projects/`` directory is absent.
    """
    projects_dir = root / "data" / "projects"
    if not projects_dir.exists():
        raise FileNotFoundError(projects_dir)

    tag_set = set(tags) if tags else None
    summaries: list[ProjectSummary] = []
    for pf in sorted(projects_dir.glob("*.yaml")):
        data = yaml.safe_load(pf.read_text()) or {}
        ptags: list[str] = data.get("tags") or []
        if tag_set and not (set(ptags) & tag_set):
            continue
        summaries.append(
            ProjectSummary(
                name=data.get("name", pf.stem),
                description=str(data.get("description") or ""),
                tags=ptags,
            )
        )
    return summaries
