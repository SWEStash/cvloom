"""Orchestrate: load → validate → render → write HTML + PDF."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from rich.console import Console

from cvloom import loader, overlays, renderer, schema

_console = Console()


def _estimate_pages(html: str) -> tuple[int, int]:
    """Strip HTML tags, count words, estimate pages at 350 words/page."""
    text = re.sub(r"<[^>]+>", " ", html)
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
) -> None:
    """Full build pipeline for one profile."""
    # Load profile
    profile_path = profiles_dir / f"{profile_name}.yaml"
    profile = loader.load_profile(profile_path)

    template_name = template_override or profile.get("template", "cv/ats-single")
    output_filename = profile.get("output_filename") or profile_name
    include_tags: list[str] = profile.get("include_tags", []) or []
    sections_cfg: dict[str, bool] = profile.get("sections", {}) or {}
    job_context: dict[str, Any] = profile.get("job_context", {}) or {}

    # Load data
    data = loader.load_data(
        data_dir=data_dir,
        private_dir=private_dir if not public else None,
        public=public,
        include_tags=include_tags if include_tags else None,
    )

    # Force-include entries that were excluded by tag filtering
    include_entries = profile.get("include_entries")
    if include_entries and include_tags:
        unfiltered = loader.load_data(
            data_dir=data_dir,
            private_dir=private_dir if not public else None,
            public=public,
            include_tags=None,
        )
        _apply_force_includes(data, unfiltered, include_entries)

    # Normalize highlights to {id, text} for overlay processing
    for section in ("work", "education", "projects"):
        entries = data.get(section, [])
        if entries:
            loader.normalize_highlights(entries)

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

    # Validate
    schema.validate_all(data, private_path=str(private_dir / "contact.yaml"))

    # Build render context
    context: dict[str, Any] = {
        **data,
        "profile": profile,
        "show": show_sections,
        "section_order": section_order,
        "job_context": job_context,
        "public": public,
        "today": date.today().strftime("%B %d, %Y"),
    }

    # Render HTML
    html = renderer.render_template(template_name, context, templates_dir=templates_dir)

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{output_filename}.html"
    html_path.write_text(html, encoding="utf-8")
    _console.print(f"[green]✓[/green] HTML  → {html_path}")

    if not skip_pdf:
        pdf_path = output_dir / f"{output_filename}.pdf"
        _render_pdf(html, pdf_path)
        _console.print(f"[green]✓[/green] PDF   → {pdf_path}")

    words, pages = _estimate_pages(html)
    summary = _section_summary(data, show_sections)
    _console.print(f"[dim]  {words} words · ~{pages} page(s)  [{summary}][/dim]")
    if pages > 2 and not profile.get("template", "").startswith("cv/academic"):
        _console.print(
            "[yellow]Warning:[/yellow] Output exceeds 2 pages. "
            "Consider trimming content or using include_tags to filter sections."
        )


def _render_pdf(html: str, output_path: Path) -> None:
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError:
        raise SystemExit(
            "WeasyPrint is not installed. Install it with: uv pip install weasyprint"
        )
    HTML(string=html).write_pdf(str(output_path))
