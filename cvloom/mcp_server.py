"""MCP server — expose cvloom's build pipeline as typed tools for LLMs.

Agent-safety guarantees (see docs/reference/mcp-server.md):

- **Schema-validated writes.** Every mutating tool (``create_profile``,
  ``upsert_project``) validates its input against the JSON Schema *before*
  writing anything and returns a structured ``{"error", "details"}`` on failure —
  so a malformed write never lands a partial file.
- **PII fence.** Read/analysis tools resolve in *public* mode (placeholder
  contact; email and phone stripped) so agent context never sees the most
  sensitive contact fields. The only tools that can surface real contact PII are
  ``get_section("contact")`` — an explicit, named request — and
  ``export_json_resume(public=False)`` — an explicit opt-out. Both require the
  caller to ask for it deliberately.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from cvloom import builder, linter, loader, projects, schema, sections
from cvloom import trim as trim_mod
from cvloom.diff import compare
from cvloom.export import to_json_resume
from cvloom.match import analyze_match

mcp = FastMCP("cvloom")


def _root(project_root: str | None) -> Path:
    return Path(project_root) if project_root else Path.cwd()


@mcp.tool()
def list_profiles(project_root: str | None = None) -> str:
    """List all build profiles with their configuration."""
    root = _root(project_root)
    try:
        summaries = projects.list_profiles(root)
    except FileNotFoundError:
        return json.dumps({"error": "No profiles/ directory found."})
    return json.dumps([dataclasses.asdict(s) for s in summaries], indent=2)


@mcp.tool()
def list_projects(
    project_root: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """List all projects, optionally filtered by tags."""
    root = _root(project_root)
    try:
        summaries = projects.list_projects(root, tags)
    except FileNotFoundError:
        return json.dumps({"error": "No data/projects/ directory found."})
    return json.dumps([dataclasses.asdict(s) for s in summaries], indent=2)


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
        result = builder.build_project(
            root,
            profile_name=profile,
            public=public,
            skip_pdf=skip_pdf,
        )
        return json.dumps(
            {
                "html_path": str(result.html_path),
                "pdf_path": str(result.pdf_path) if result.pdf_path else None,
                "words": result.words,
                "pages": result.pages,
                "section_word_counts": result.section_word_counts,
            },
            indent=2,
        )
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})
    except SystemExit as e:
        return json.dumps({"error": str(e.code)})


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
    slug = sections.slugify(name)
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
    )
    if errors:
        return json.dumps({"valid": False, "errors": errors}, indent=2)
    return json.dumps({"valid": True})


@mcp.tool()
def export_json_resume(
    profile: str = "general",
    public: bool = True,
    project_root: str | None = None,
) -> str:
    """Export CV data as JSON Resume format.

    PII fence: ``public`` defaults to True, so email and phone are stripped from
    the returned document. Pass ``public=False`` to include real contact PII —
    an explicit opt-out only.
    """
    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=public)
        resume = to_json_resume(resolved)
        return json.dumps(resume, indent=2, ensure_ascii=False)
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})


@mcp.tool()
def check_cv(
    profile: str = "general",
    rule_ids: list[str] | None = None,
    project_root: str | None = None,
) -> str:
    """Run the writing lint on a profile. Returns lint findings as JSON.

    Each finding carries a ``category`` (writing / structure / ats-parse); there
    is no single "ATS score". See docs/reference/ats-readiness.md.
    """
    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        findings = linter.lint(resolved, rule_ids=rule_ids)
        return json.dumps(
            [
                {
                    "rule_id": f.rule_id,
                    "category": f.category,
                    "severity": f.severity,
                    "section": f.section,
                    "entry": f.entry,
                    "message": f.message,
                    "fix_hint": f.fix_hint,
                }
                for f in findings
            ],
            indent=2,
        )
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})


@mcp.tool()
def trim_report(
    profile: str = "general",
    target_pages: int = 1,
    project_root: str | None = None,
) -> str:
    """Get per-section word count breakdown and trim recommendations."""
    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        report = trim_mod.analyze(resolved, target_pages=target_pages)
        return json.dumps(
            {
                "total_words": report.total_words,
                "estimated_pages": report.estimated_pages,
                "words_to_cut": report.words_to_cut,
                "sections": [
                    {
                        "section": s.section,
                        "total_words": s.total_words,
                        "entries": [
                            {"label": e.label, "total_words": e.total_words} for e in s.entries
                        ],
                    }
                    for s in report.sections
                ],
                "recommendations": report.recommendations,
            },
            indent=2,
        )
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})


@mcp.tool()
def diff_profiles(
    profile_a: str,
    profile_b: str,
    project_root: str | None = None,
) -> str:
    """Compare two profiles side by side. Returns structural differences."""
    root = _root(project_root)
    try:
        resolved_a = builder.resolve_project(root, profile_a, public=True)
        resolved_b = builder.resolve_project(root, profile_b, public=True)
        result = compare(resolved_a, resolved_b, name_a=profile_a, name_b=profile_b)
        return json.dumps(
            {
                "template_a": result.template_a,
                "template_b": result.template_b,
                "sections_only_in_a": result.sections_only_in_a,
                "sections_only_in_b": result.sections_only_in_b,
                "entries_only_in_a": result.entries_only_in_a,
                "entries_only_in_b": result.entries_only_in_b,
                "word_count_a": result.word_count_a,
                "word_count_b": result.word_count_b,
                "highlight_count_a": result.highlight_count_a,
                "highlight_count_b": result.highlight_count_b,
            },
            indent=2,
        )
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})


@mcp.tool()
def match_jd(
    jd_text: str,
    profile: str = "general",
    project_root: str | None = None,
) -> str:
    """Analyze keyword gaps between CV and a job description text."""
    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        report = analyze_match(resolved, jd_text)
        return json.dumps(
            {
                "coverage": round(report.cv_keywords_coverage, 3),
                "jd_word_count": report.jd_word_count,
                "matched": [
                    {
                        "keyword": m.keyword,
                        "found_in": m.found_in,
                        "frequency_jd": m.frequency_jd,
                    }
                    for m in report.matched
                ],
                "gaps": report.gaps,
                "top_jd_keywords": report.top_jd_keywords,
            },
            indent=2,
        )
    except builder.ResolveError as e:
        return json.dumps({"error": "resolve failed", "details": e.errors})


@mcp.tool()
def ai_review_cv(profile: str = "general", project_root: str | None = None) -> str:
    """AI-powered scoring and feedback for each CV section.

    Requires CVLOOM_AI_BASE_URL environment variable.
    Returns JSON with overall_score, per-section scores, and top_priorities.
    """
    from cvloom.ai import get_client, get_model, is_configured
    from cvloom.ai.analyzer import review
    from cvloom.ai.provider import AINotConfiguredError

    if not is_configured():
        return json.dumps({"error": "AI provider not configured. Set CVLOOM_AI_BASE_URL."})

    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        client = get_client()
        result = review(resolved, client, get_model())
    except builder.ResolveError as exc:
        return json.dumps({"error": "resolve failed", "details": exc.errors})
    except (AINotConfiguredError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(dataclasses.asdict(result), indent=2)


@mcp.tool()
def ai_generate_cover(
    profile: str = "general", jd_text: str = "", project_root: str | None = None
) -> str:
    """Generate a tailored cover letter from the CV and a job description.

    Requires CVLOOM_AI_BASE_URL environment variable.
    Pass the full job description text as jd_text.
    Returns JSON with letter, word_count, and key_alignments.
    """
    from cvloom.ai import get_client, get_model, is_configured
    from cvloom.ai.cover import generate_cover
    from cvloom.ai.provider import AINotConfiguredError

    if not is_configured():
        return json.dumps({"error": "AI provider not configured. Set CVLOOM_AI_BASE_URL."})

    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        client = get_client()
        result = generate_cover(resolved, jd_text, client, get_model())
    except builder.ResolveError as exc:
        return json.dumps({"error": "resolve failed", "details": exc.errors})
    except (AINotConfiguredError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(dataclasses.asdict(result), indent=2)


@mcp.tool()
def ai_suggest_improvements(
    profile: str = "general",
    role: str = "",
    project_root: str | None = None,
) -> str:
    """Suggest content improvements for the CV: new bullets, skills, rewordings.

    Requires CVLOOM_AI_BASE_URL environment variable.
    Pass role to target suggestions for a specific position.
    Returns JSON with suggestions, missing_skills, and summary.
    """
    from cvloom.ai import get_client, get_model, is_configured
    from cvloom.ai.provider import AINotConfiguredError
    from cvloom.ai.suggest import suggest

    if not is_configured():
        return json.dumps({"error": "AI provider not configured. Set CVLOOM_AI_BASE_URL."})

    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        client = get_client()
        result = suggest(resolved, client, get_model(), role_context=role)
    except builder.ResolveError as exc:
        return json.dumps({"error": "resolve failed", "details": exc.errors})
    except (AINotConfiguredError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(dataclasses.asdict(result), indent=2)


@mcp.tool()
def ai_align_to_jd(
    profile: str = "general",
    jd_text: str = "",
    project_root: str | None = None,
) -> str:
    """Qualitative AI analysis of how well the CV aligns to a job description.

    Requires CVLOOM_AI_BASE_URL environment variable.
    jd_text is the full text of the job description.
    Returns JSON with alignment_score, narrative, repositioning, tone_gaps, strengths.
    """
    from cvloom.ai import get_client, get_model, is_configured
    from cvloom.ai.align import align
    from cvloom.ai.provider import AINotConfiguredError

    if not is_configured():
        return json.dumps({"error": "AI provider not configured. Set CVLOOM_AI_BASE_URL."})

    root = _root(project_root)
    try:
        resolved = builder.resolve_project(root, profile, public=True)
        result = align(resolved, jd_text, get_client(), get_model())
    except builder.ResolveError as exc:
        return json.dumps({"error": "resolve failed", "details": exc.errors})
    except (AINotConfiguredError, RuntimeError) as exc:
        return json.dumps({"error": str(exc)})

    return json.dumps(dataclasses.asdict(result), indent=2)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
