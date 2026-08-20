"""The `build` command, plus the text-extraction and lint reporting it prints."""

from __future__ import annotations

from pathlib import Path

import click

from cvloom import (
    builder,
    fidelity,
    linter,
    projects,
)
from cvloom import extract as extract_mod
from cvloom.cli.group import cli
from cvloom.cli.shared import (
    _MAX_PAGES,
    _console,
    _emit_warnings,
    _err,
    _lint_breakdown,
    _named,
    _render_resolve_error,
    _root,
    _section_summary,
    _warn_template_parse_risk,
)
from cvloom.models import ResolvedProfile


def _write_extracted_text(pdf_path: Path, resolved: ResolvedProfile) -> None:
    """Write the PDF's text layer beside it, once per available engine, and score it.

    The engine is named in each filename because they disagree about reading order.
    See docs/dev/architecture.md.
    """
    engines = extract_mod.available_engines()
    if not engines:
        _err.print(
            "[yellow]Warning:[/yellow] no PDF text extractor available. "
            "Install poppler-utils for `pdftotext`, or `uv sync --extra extract`."
        )
        return
    for result in extract_mod.extract_all(pdf_path):
        out = pdf_path.with_name(f"{pdf_path.stem}.{result.engine}.txt")
        out.write_text(result.text, encoding="utf-8")
        _console.print(f"[green]✓[/green] TEXT  → {out}  [dim]({result.engine})[/dim]")
    _print_recall(fidelity.recall(resolved, pdf_path))


# How many missing tokens to name before summarising the rest. Naming them is the
# useful half — a count alone tells the user something broke without telling them


def _print_recall(report: fidelity.RecallReport) -> None:
    """Print per-engine recall of the tokens the template rendered.

    Per engine and never averaged. The engines disagree by design, and a single
    figure across them would average away the disagreement that *is* the
    measurement — see docs/reference/ats-readiness.md.
    """
    if not report.engines:
        return
    if not report.attribution_available:
        _console.print(
            "\n[dim]One extraction engine installed, so a missing word cannot be "
            "told apart from one the template never drew — every loss below is "
            "counted against the engine. Install the `extract` extra for more.[/dim]"
        )
    if report.unrendered:
        _console.print(
            f"\n[yellow]{len(report.unrendered)} of {report.source_total} source token(s) "
            f"are not on the page[/yellow] [dim]— this template does not render them, "
            f"so no extractor can find them: {_named(report.unrendered)}[/dim]"
        )
    total = report.engines[0].total
    _console.print(f"\n[bold]Text layer[/bold], {total} rendered token(s):")
    for r in report.engines:
        colour = "green" if not r.missing else "yellow" if r.percentage >= 99 else "red"
        line = f"  {r.engine:<14}[{colour}]{r.found}/{r.total}  {r.percentage:5.1f}%[/{colour}]"
        if r.missing:
            line += f"  [dim](lost: {_named(r.missing)})[/dim]"
        _console.print(line)
    _console.print(
        "[dim]Recall of your own words in the extracted text, per engine. Not a "
        "score — see docs/reference/ats-readiness.md.[/dim]"
    )


@cli.command()
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Override template (e.g. cv/modern-single).",
)
@click.option(
    "--output-dir",
    "-o",
    default="dist",
    show_default=True,
    help="Output directory.",
)
@click.option(
    "--public",
    is_flag=True,
    default=False,
    help="Use placeholder contact data (safe for CI/GitHub Pages).",
)
@click.option(
    "--skip-pdf",
    is_flag=True,
    default=False,
    help="Skip PDF generation (HTML only).",
)
@click.option(
    "--check",
    "run_check",
    is_flag=True,
    default=False,
    help="Run the writing lint after build and print a category breakdown.",
)
@click.option(
    "--strict",
    default=None,
    type=int,
    metavar="N",
    help="Exit non-zero if more than N lint findings (implies --check).",
)
@click.option(
    "--extract-text",
    "extract_text",
    is_flag=True,
    default=False,
    help="Also write the PDF's extracted text layer — what an ATS actually reads.",
)
@click.option(
    "--all",
    "build_all",
    is_flag=True,
    default=False,
    help="Build every profile in profiles/ instead of one.",
)
def build(
    profile: str,
    template: str | None,
    output_dir: str,
    public: bool,
    skip_pdf: bool,
    run_check: bool,
    strict: int | None,
    extract_text: bool,
    build_all: bool,
) -> None:
    """Build CV outputs for a given profile."""
    root = _root()
    if build_all:
        _build_every_profile(
            root,
            output_dir=output_dir,
            template=template,
            public=public,
            skip_pdf=skip_pdf,
            run_check=run_check,
            strict=strict,
            extract_text=extract_text,
        )
        return
    _build_one(
        root,
        profile=profile,
        output_dir=output_dir,
        template=template,
        public=public,
        skip_pdf=skip_pdf,
        run_check=run_check,
        strict=strict,
        extract_text=extract_text,
    )


def _build_one(
    root: Path,
    *,
    profile: str,
    output_dir: str,
    template: str | None,
    public: bool,
    skip_pdf: bool,
    run_check: bool,
    strict: int | None,
    extract_text: bool = False,
) -> int:
    """Build one profile and report it. Returns the lint finding count."""
    try:
        result = builder.build_project(
            root,
            output_dir=root / output_dir,
            profile_name=profile,
            template_override=template,
            public=public,
            skip_pdf=skip_pdf,
        )
    except builder.ResolveError as exc:
        _render_resolve_error(exc)
        raise SystemExit(1) from None
    _emit_warnings(result.resolved.warnings)
    _console.print(f"[green]\u2713[/green] HTML  \u2192 {result.html_path}")
    if result.pdf_path:
        _console.print(f"[green]\u2713[/green] PDF   \u2192 {result.pdf_path}")
    summary = _section_summary(result.resolved.data, result.resolved.show_sections)
    # The opening bracket is escaped for Rich, which would otherwise read
    # "[skills\u00d74 \u2026]" as a markup tag and silently drop the whole summary.
    stats = f"{result.words} words \u00b7 ~{result.pages} page(s)"
    bracketed = "  \\[" + summary + "]" if summary else ""
    _console.print(f"[dim]  {stats}{bracketed}[/dim]")
    if result.pages > _MAX_PAGES and not result.resolved.template_name.startswith("cv/academic"):
        _console.print(
            f"[yellow]Warning:[/yellow] Output exceeds {_MAX_PAGES} pages. "
            "Consider trimming content or using `select` to narrow sections."
        )
    _warn_template_parse_risk(result.resolved.template_name)
    if extract_text and result.pdf_path:
        _write_extracted_text(result.pdf_path, result.resolved)

    if run_check or strict is not None:
        findings = linter.lint(result.resolved)
        count = len(findings)
        color = "green" if count == 0 else "yellow" if count <= 5 else "red"
        _console.print(
            f"[{color}]Writing lint: {count} issue(s)[/{color}] \u2014 {_lint_breakdown(findings)}"
        )
        if strict is not None and count > strict:
            _console.print(f"[red]{count} findings exceed the --strict budget of {strict}.[/red]")
            raise SystemExit(1)
        return count
    return 0


def _build_every_profile(
    root: Path,
    *,
    output_dir: str,
    template: str | None,
    public: bool,
    skip_pdf: bool,
    run_check: bool,
    strict: int | None,
    extract_text: bool = False,
) -> None:
    """Build every profile in profiles/.

    One failing profile stops the run rather than being skipped.
    """
    try:
        summaries = projects.list_profiles(root)
    except FileNotFoundError:
        _err.print("[yellow]No profiles/ directory found.[/yellow]")
        raise SystemExit(1) from None
    if not summaries:
        _err.print("[yellow]No profiles found in profiles/.[/yellow]")
        raise SystemExit(1)

    for i, summary in enumerate(summaries):
        if i:
            _console.print()
        _console.print(f"[bold]{summary.name}[/bold] [dim]({summary.template})[/dim]")
        _build_one(
            root,
            profile=summary.name,
            output_dir=output_dir,
            template=template,
            public=public,
            skip_pdf=skip_pdf,
            run_check=run_check,
            strict=strict,
            extract_text=extract_text,
        )
    _console.print(f"\n[green]Built {len(summaries)} profile(s).[/green]")
