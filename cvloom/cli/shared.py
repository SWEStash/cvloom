"""Consoles, project-root resolution, and the resolve wrapper every command uses.

Imported by every command module and importing none of them, which is what
keeps the package acyclic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape

from cvloom import (
    builder,
    linter,
    sections,
    templates_meta,
)
from cvloom import trim as trim_mod
from cvloom.models import ResolvedProfile

_console = Console()

# Page ceiling before `build` nags.
_MAX_PAGES = trim_mod.MAX_PAGES

# How a template's extraction rating is shown. Colour carries the same ordering as
# the words, for anyone piping this through a pager that drops it.
_ATS_LABEL = {
    templates_meta.ATS_SAFE: "[green]safe[/green]",
    templates_meta.ATS_CAUTION: "[yellow]caution[/yellow]",
    templates_meta.ATS_UNSAFE: "[red]unsafe[/red]",
}
_err = Console(stderr=True)


def _root() -> Path:
    """Return the project root — the directory from which cvloom is invoked."""
    return Path.cwd()


def _render_resolve_error(exc: builder.ResolveError) -> None:
    """Print a ResolveError's messages to stderr.

    Messages are escaped: they quote schema patterns and user data, and rich
    would read a bracketed run like ``[a-z]`` as a style tag and drop it.
    """
    _err.print("[bold red]Validation errors:[/bold red]")
    for e in exc.errors:
        _err.print(f"  [red]✗[/red] {escape(e)}")


def _emit_warnings(warnings: list[str]) -> None:
    for w in warnings:
        _err.print(f"[yellow]Warning:[/yellow] {escape(w)}")


def _resolve(root: Path, profile: str, *, public: bool) -> ResolvedProfile:
    """Resolve a profile, rendering ResolveError to stderr and warnings after."""
    try:
        resolved = builder.resolve_project(root, profile, public=public)
    except builder.ResolveError as exc:
        _render_resolve_error(exc)
        raise SystemExit(1) from None
    _emit_warnings(resolved.warnings)
    return resolved


def _section_summary(data: dict[str, Any], show: dict[str, bool]) -> str:
    """Return a compact string summarising section item counts."""
    labels = {"skills": "skills", **{s.name: s.summary_label for s in sections.SECTIONS}}
    parts = [
        f"{labels[name]}×{len(data[name])}"
        for name in sections.DEFAULT_SECTION_ORDER
        if show.get(name) and data.get(name)
    ]
    return "  ".join(parts)


_MAX_NAMED_MISSING = 6


def _named(tokens: tuple[str, ...]) -> str:
    """Name the first few tokens and count the rest."""
    named = ", ".join(tokens[:_MAX_NAMED_MISSING])
    extra = len(tokens) - _MAX_NAMED_MISSING
    return f"{named}, +{extra} more" if extra > 0 else named


def _warn_if_not_a_job_posting(jd_text: str, jd_path: str, locale_code: str) -> None:
    """Say so when the ``--jd`` file does not read like a job posting.

    A warning rather than a refusal: the check is a word list, so it is the
    user — who can see the file — who should decide, not cvloom. It runs before
    the AI call because the model will not make this call reliably from inside
    the generation prompt, and a confident cover letter written from someone's
    privacy policy is a worse outcome than a warning they ignore.
    """
    from cvloom.match import looks_like_a_job_posting

    if looks_like_a_job_posting(jd_text, locale_code):
        return
    _console.print(
        f"[yellow]warning:[/yellow] {jd_path} does not read like a job posting — "
        "none of the usual phrases (responsibilities, requirements, what you'll do) "
        "appear in it. Continuing anyway; check you passed the right file."
    )


def _warn_template_parse_risk(template_name: str) -> None:
    """Warn at build time when the chosen layout does not survive extraction.

    Fires on `build`, not only `list-templates`: the failure is invisible in the
    rendered PDF and only appears in the text layer an ATS reads.
    """
    meta = templates_meta.info_for(template_name)
    if meta is None or meta.ats == templates_meta.ATS_SAFE:
        return
    label = (
        "does not parse reliably"
        if meta.ats == templates_meta.ATS_UNSAFE
        else "parses with caveats"
    )
    colour = "red" if meta.ats == templates_meta.ATS_UNSAFE else "yellow"
    _console.print(f"[{colour}]Note:[/{colour}] {template_name} {label}. {meta.caveat}")
    _console.print(
        "[dim]      For an ATS portal, upload the DOCX instead — "
        "`cvloom export --format docx`. Reading order is guaranteed by that format, "
        "not inferred from the page.[/dim]"
    )


def _lint_breakdown(findings: list[linter.LintFinding]) -> str:
    """Render the per-category writing-lint breakdown (no single 0–100 score)."""
    counts = linter.category_counts(findings)
    return ", ".join(f"{cat}: {n}" for cat, n in counts.items())
