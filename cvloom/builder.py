"""Orchestrate: load → validate → render → write HTML + PDF."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from cvloom import loader, overlays, renderer, schema
from cvloom.models import BuildResult, ResolvedProfile


def _estimate_pages(html: str) -> tuple[int, int]:
    """Strip HTML tags, count words, estimate pages at 350 words/page."""
    # Strip <style> blocks before removing tags so CSS tokens aren't counted.
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    words = len(text.split())
    pages = max(1, round(words / 350))
    return words, pages


def _section_summary(data: dict[str, Any], show: dict[str, bool]) -> str:
    """Return a compact string summarising section item counts."""
    parts: list[str] = []
    if show.get("work") and data.get("work"):
        parts.append(f"work×{len(data['work'])}")
    if show.get("education") and data.get("education"):
        parts.append(f"edu×{len(data['education'])}")
    if show.get("skills") and data.get("skills"):
        parts.append(f"skills×{len(data['skills'])}")
    if show.get("projects") and data.get("projects"):
        parts.append(f"projects×{len(data['projects'])}")
    return "  ".join(parts)


def _apply_force_includes(
    data: dict[str, Any],
    unfiltered: dict[str, Any],
    include_entries: dict[str, list[dict[str, str]]],
) -> None:
    """Re-add entries from *unfiltered* that match *include_entries* specs."""
    for section, matchers in include_entries.items():
        existing = data.get(section, [])
        pool = unfiltered.get(section, [])
        for match in matchers:
            # Skip if already present
            already = any(
                all(e.get(k) == v for k, v in match.items()) for e in existing
            )
            if already:
                continue
            for entry in pool:
                if all(entry.get(k) == v for k, v in match.items()):
                    existing.append(entry)
                    break
        data[section] = existing


def _word_count_by_section(
    data: dict[str, Any], show: dict[str, bool]
) -> dict[str, int]:
    """Count words per visible section from the data model."""
    counts: dict[str, int] = {}
    for section in ("work", "education", "projects"):
        if not show.get(section):
            continue
        words = 0
        for entry in data.get(section, []):
            for key in ("title", "company", "institution", "name", "description",
                        "location", "degree", "field"):
                val = entry.get(key)
                if isinstance(val, str):
                    words += len(val.split())
            for hl in entry.get("highlights", []):
                text = hl if isinstance(hl, str) else hl.get("text", "")
                words += len(text.split())
        counts[section] = words

    if show.get("skills"):
        words = 0
        for group in data.get("skills", []):
            words += len(group.get("category", "").split())
            for item in group.get("items", []):
                if isinstance(item, str):
                    words += len(item.split())
                else:
                    words += len(item.get("name", "").split())
        counts["skills"] = words

    # basics (headline + summary)
    basics = data.get("basics", {})
    bw = 0
    for key in ("headline", "summary"):
        val = basics.get(key)
        if isinstance(val, str):
            bw += len(val.split())
    counts["basics"] = bw

    return counts


def resolve(
    data_dir: Path,
    private_dir: Path,
    profiles_dir: Path,
    profile_name: str = "general",
    template_override: str | None = None,
    public: bool = False,
) -> ResolvedProfile:
    """Run the pipeline up to rendering: load, filter, overlay, validate.

    Returns a :class:`ResolvedProfile` with fully resolved data.
    """
    # Load profile
    profile_path = profiles_dir / f"{profile_name}.yaml"
    profile = loader.load_profile(profile_path)

    # Validate profile against schema
    profile_errors = schema.validate(
        "profile", profile, source_path=f"profiles/{profile_name}.yaml"
    )
    if profile_errors:
        from rich.console import Console
        _err = Console(stderr=True)
        _err.print("[bold red]Profile validation errors:[/bold red]")
        for err in profile_errors:
            _err.print(f"  [red]✗[/red] {err}")
        raise SystemExit(1)

    template_name = template_override or profile.get("template", "cv/ats-single")

    if not renderer.template_exists(template_name):
        available = renderer.list_templates()
        raise SystemExit(
            f"Template '{template_name}' not found.\n"
            f"Available templates: {', '.join(available) or 'none'}"
        )

    output_filename = profile.get("output_filename") or profile_name
    include_tags: list[str] = profile.get("include_tags", []) or []
    sections_cfg: dict[str, bool] = profile.get("sections", {}) or {}

    # Load data
    data = loader.load_data(
        data_dir=data_dir,
        private_dir=private_dir,
        public=public,
        include_tags=include_tags if include_tags else None,
    )

    # Force-include entries that were excluded by tag filtering
    include_entries = profile.get("include_entries")
    if include_entries and include_tags:
        unfiltered = loader.load_data(
            data_dir=data_dir,
            private_dir=private_dir,
            public=public,
            include_tags=None,
        )
        _apply_force_includes(data, unfiltered, include_entries)

    # Normalize highlights to {id, text} for overlay processing
    for section in ("work", "education", "projects"):
        entries = data.get(section, [])
        if entries:
            loader.normalize_highlights(entries)

    # Validate overlays before applying
    overlay_warnings = overlays.validate_overlays(data, profile)
    if overlay_warnings:
        from rich.console import Console
        _warn = Console(stderr=True)
        for w in overlay_warnings:
            _warn.print(f"[yellow]Warning:[/yellow] {w}")

    # Apply overlays
    overlays.apply_overlays(data, profile)

    # Flatten highlights back to plain strings for templates
    for section in ("work", "education", "projects"):
        entries = data.get(section, [])
        if entries:
            loader.flatten_highlights(entries)

    # Apply section visibility
    section_defaults = {"work": True, "education": True, "skills": True, "projects": True}
    show_sections = {**section_defaults, **sections_cfg}

    # Section ordering
    default_order = ["skills", "work", "education", "projects"]
    section_order = profile.get("section_order", default_order)

    # Validate data
    schema.validate_all(data, private_path=str(private_dir / "contact.yaml"))

    return ResolvedProfile(
        profile=profile,
        data=data,
        show_sections=show_sections,
        section_order=section_order,
        template_name=template_name,
        output_filename=output_filename,
    )


def _pdf_filename(resolved: ResolvedProfile) -> str:
    """Derive the PDF output stem from profile format string or contact name."""
    fmt = resolved.profile.get("pdf_filename_format")
    if fmt:
        name = resolved.data.get("contact", {}).get("name", "")
        parts = name.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        return str(fmt.format(first=first, last=last, name=name.replace(" ", "_")))

    name = resolved.data.get("contact", {}).get("name", "")
    if name:
        parts = name.split()
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        return f"{first}_{last}_Resume" if last else f"{first}_Resume"

    return resolved.output_filename


def build(
    data_dir: Path,
    private_dir: Path,
    profiles_dir: Path,
    output_dir: Path,
    profile_name: str = "general",
    template_override: str | None = None,
    public: bool = False,
    templates_dir: Path | None = None,
    skip_pdf: bool = False,
) -> BuildResult:
    """Full build pipeline for one profile. Returns structured result."""
    resolved = resolve(
        data_dir=data_dir,
        private_dir=private_dir,
        profiles_dir=profiles_dir,
        profile_name=profile_name,
        template_override=template_override,
        public=public,
    )

    job_context: dict[str, Any] = resolved.profile.get("job_context", {}) or {}

    # Build render context
    context: dict[str, Any] = {
        **resolved.data,
        "profile": resolved.profile,
        "show": resolved.show_sections,
        "section_order": resolved.section_order,
        "job_context": job_context,
        "public": public,
        "today": date.today().strftime("%B %d, %Y"),
    }

    # Render HTML
    html = renderer.render_template(
        resolved.template_name, context, templates_dir=templates_dir
    )

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{resolved.output_filename}.html"
    html_path.write_text(html, encoding="utf-8")

    pdf_path: Path | None = None
    if not skip_pdf:
        pdf_path = output_dir / f"{_pdf_filename(resolved)}.pdf"
        _render_pdf(html, pdf_path)

    words, pages = _estimate_pages(html)
    section_word_counts = _word_count_by_section(resolved.data, resolved.show_sections)

    return BuildResult(
        resolved=resolved,
        html=html,
        html_path=html_path,
        pdf_path=pdf_path,
        words=words,
        pages=pages,
        section_word_counts=section_word_counts,
    )


def _render_pdf(html: str, output_path: Path) -> None:
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError:
        raise SystemExit(
            "WeasyPrint is not installed. Install it with: uv pip install weasyprint"
        )
    HTML(string=html).write_pdf(str(output_path))
