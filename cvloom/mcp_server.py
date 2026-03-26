"""MCP server — expose cvloom's build pipeline as typed tools for LLMs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from cvloom import builder, loader, schema
from cvloom.export import to_json_resume

mcp = FastMCP("cvloom")


def _root(project_root: str | None) -> Path:
    return Path(project_root) if project_root else Path.cwd()


@mcp.tool()
def list_profiles(project_root: str | None = None) -> str:
    """List all build profiles with their configuration."""
    root = _root(project_root)
    profiles_dir = root / "profiles"
    if not profiles_dir.exists():
        return json.dumps({"error": "No profiles/ directory found."})

    result: list[dict[str, Any]] = []
    for pf in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(pf.read_text()) or {}
        result.append({
            "name": pf.stem,
            "template": data.get("template", ""),
            "output_filename": data.get("output_filename", pf.stem),
            "include_tags": data.get("include_tags", []),
            "job_context": data.get("job_context"),
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def list_projects(
    project_root: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """List all projects, optionally filtered by tags."""
    root = _root(project_root)
    projects_dir = root / "data" / "projects"
    if not projects_dir.exists():
        return json.dumps({"error": "No data/projects/ directory found."})

    result: list[dict[str, Any]] = []
    tag_set = set(tags) if tags else None

    for pf in sorted(projects_dir.glob("*.yaml")):
        data = yaml.safe_load(pf.read_text()) or {}
        ptags = data.get("tags", [])
        if tag_set and not (set(ptags) & tag_set):
            continue
        result.append({
            "name": data.get("name", pf.stem),
            "description": data.get("description", ""),
            "tags": ptags,
        })
    return json.dumps(result, indent=2)


@mcp.tool()
def get_section(section: str, project_root: str | None = None) -> str:
    """Read raw YAML data for a section (basics, work, education, skills, projects, contact)."""
    root = _root(project_root)

    if section == "contact":
        contact_path = root / "private" / "contact.yaml"
        if not contact_path.exists():
            return json.dumps({"error": "private/contact.yaml not found."})
        data = yaml.safe_load(contact_path.read_text())
        return json.dumps(data, indent=2)

    if section == "projects":
        projects_dir = root / "data" / "projects"
        if not projects_dir.exists():
            return json.dumps([])
        projects: list[Any] = []
        for pf in sorted(projects_dir.glob("*.yaml")):
            p = yaml.safe_load(pf.read_text())
            if p:
                projects.append(p)
        return json.dumps(projects, indent=2)

    path = root / "data" / f"{section}.yaml"
    if not path.exists():
        return json.dumps({"error": f"data/{section}.yaml not found."})
    data = yaml.safe_load(path.read_text())
    return json.dumps(data, indent=2)


@mcp.tool()
def build_cv(
    profile: str = "general",
    public: bool = False,
    skip_pdf: bool = False,
    project_root: str | None = None,
) -> str:
    """Build CV for a profile and return build statistics."""
    root = _root(project_root)
    try:
        result = builder.build(
            data_dir=root / "data",
            private_dir=root / "private",
            profiles_dir=root / "profiles",
            output_dir=root / "dist",
            profile_name=profile,
            public=public,
            skip_pdf=skip_pdf,
        )
        return json.dumps({
            "html_path": str(result.html_path),
            "pdf_path": str(result.pdf_path) if result.pdf_path else None,
            "words": result.words,
            "pages": result.pages,
            "section_word_counts": result.section_word_counts,
        }, indent=2)
    except SystemExit as e:
        return json.dumps({"error": f"Build failed with exit code {e.code}"})


@mcp.tool()
def create_profile(
    name: str,
    config: dict[str, Any],
    project_root: str | None = None,
) -> str:
    """Create a new profile YAML file in profiles/."""
    root = _root(project_root)

    # Validate against profile schema
    errors = schema.validate("profile", config, source_path=f"profiles/{name}.yaml")
    if errors:
        return json.dumps({"error": "Validation failed", "details": errors})

    profiles_dir = root / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    path = profiles_dir / f"{name}.yaml"
    path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
    return json.dumps({"created": str(path)})


@mcp.tool()
def upsert_project(
    project: dict[str, Any],
    project_root: str | None = None,
) -> str:
    """Create or update a project YAML file in data/projects/."""
    root = _root(project_root)

    # Validate against project schema
    errors = schema.validate("project", project)
    if errors:
        return json.dumps({"error": "Validation failed", "details": errors})

    name = project.get("name", "untitled")
    slug = name.lower().replace(" ", "-")
    projects_dir = root / "data" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    path = projects_dir / f"{slug}.yaml"
    path.write_text(yaml.dump(project, default_flow_style=False, sort_keys=False))
    return json.dumps({"written": str(path)})


@mcp.tool()
def validate_data(project_root: str | None = None) -> str:
    """Run schema validation on all data files. Returns errors or 'valid'."""
    root = _root(project_root)
    data = loader.load_data(
        data_dir=root / "data",
        private_dir=root / "private",
        public=False,
    )
    errors = schema.validate_all(
        data,
        private_path=str(root / "private" / "contact.yaml"),
        raise_on_error=False,
    )
    if errors:
        return json.dumps({"valid": False, "errors": errors}, indent=2)
    return json.dumps({"valid": True})


@mcp.tool()
def export_json_resume(
    profile: str = "general",
    project_root: str | None = None,
) -> str:
    """Export CV data as JSON Resume format."""
    root = _root(project_root)
    try:
        resolved = builder.resolve(
            data_dir=root / "data",
            private_dir=root / "private",
            profiles_dir=root / "profiles",
            profile_name=profile,
        )
        resume = to_json_resume(resolved)
        return json.dumps(resume, indent=2, ensure_ascii=False)
    except SystemExit as e:
        return json.dumps({"error": f"Resolve failed with exit code {e.code}"})


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
