"""Commands that read a resolved CV and report on it: check, trim, diff, match."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from cvloom import (
    linter,
)
from cvloom import trim as trim_mod
from cvloom.cli.group import cli
from cvloom.cli.shared import (
    _console,
    _lint_breakdown,
    _resolve,
    _root,
    _warn_if_not_a_job_posting,
    _warn_template_parse_risk,
)
from cvloom.diff import compare


def _lint_coverage(code: str) -> str:
    """Render which rules ran under *code*, and which could not.

    Partial per-locale coverage is a documentation problem rather than a
    correctness one — ``check`` gates nothing — but a clean run that quietly
    skipped rules claims more than it earned, so say so. Counts come from the
    registry, never a literal.
    """
    active, skipped = linter.rules_for(code)
    total = len(active) + len(skipped)
    line = f"{len(active)} of {total} rules ran"
    if skipped:
        names = ", ".join(f"{r.rule_id} {r.name}" for r in skipped)
        line += f" · {len(skipped)} skipped (no {code} support: {names})"
    return line


@cli.command()
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
def check(profile: str) -> None:
    """Run the writing lint on a profile's resolved data.

    Findings are grouped into three honest axes — writing, structure, and
    ats-parse — with no single "ATS score". See docs/reference/ats-readiness.md.
    """
    root = _root()
    resolved = _resolve(root, profile, public=True)
    findings = linter.lint(resolved)
    _warn_template_parse_risk(resolved.template_name)
    coverage = _lint_coverage(resolved.locale.code)
    if not findings:
        _console.print("[green]✓ No writing issues found.[/green]")
        _console.print(f"[dim]{coverage}[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 1),
    )
    table.add_column("Rule")
    table.add_column("Category")
    table.add_column("Section")
    table.add_column("Entry")
    table.add_column("Message")
    table.add_column("Fix hint")

    for f in findings:
        table.add_row(
            f.rule_id,
            f.category,
            f.section,
            f.entry,
            f.message,
            f.fix_hint,
        )

    _console.print(table)
    _console.print(
        f"\n[yellow]{len(findings)} issue(s) found.[/yellow] [dim]{_lint_breakdown(findings)}[/dim]"
    )
    _console.print(f"[dim]{coverage}[/dim]")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# trim
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--target-pages",
    default=3,
    show_default=True,
    help="Target page count.",
)
def trim(profile: str, target_pages: int) -> None:
    """Show per-section word breakdown and trim recommendations."""
    root = _root()
    resolved = _resolve(root, profile, public=True)
    report = trim_mod.analyze(resolved, target_pages=target_pages)

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 1),
    )
    table.add_column("Section")
    table.add_column("Words", justify="right")
    table.add_column("Entries", justify="right")

    for sec in report.sections:
        entry_count = str(len(sec.entries)) if sec.entries else "—"
        table.add_row(sec.section, str(sec.total_words), entry_count)

    _console.print(table)
    _console.print(
        f"\n[dim]Total: {report.total_words} words · "
        f"~{report.estimated_pages} page(s) · "
        f"target: {report.target_pages}[/dim]"
    )

    if report.words_to_cut > 0:
        _console.print(f"\n[yellow]Cut ~{report.words_to_cut} words to reach target.[/yellow]")

    if report.recommendations:
        _console.print("\n[bold]Recommendations:[/bold]")
        for rec in report.recommendations:
            _console.print(f"  • {rec}")


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("profile_a")
@click.argument("profile_b")
def diff(profile_a: str, profile_b: str) -> None:
    """Compare two profiles side by side."""
    root = _root()
    resolved_a = _resolve(root, profile_a, public=True)
    resolved_b = _resolve(root, profile_b, public=True)
    result = compare(resolved_a, resolved_b, profile_a, profile_b)

    # Template
    if result.template_a != result.template_b:
        _console.print(f"[bold]Template:[/bold] {result.template_a} → {result.template_b}")

    # Sections
    if result.sections_only_in_a:
        _console.print(
            f"[red]Sections only in {profile_a}:[/red] " + ", ".join(result.sections_only_in_a)
        )
    if result.sections_only_in_b:
        _console.print(
            f"[green]Sections only in {profile_b}:[/green] " + ", ".join(result.sections_only_in_b)
        )

    # Entries
    for section, labels in result.entries_only_in_a.items():
        _console.print(f"[red]{section} only in {profile_a}:[/red] " + ", ".join(labels))
    for section, labels in result.entries_only_in_b.items():
        _console.print(f"[green]{section} only in {profile_b}:[/green] " + ", ".join(labels))

    # Word counts
    delta = result.word_count_b - result.word_count_a
    sign = "+" if delta > 0 else ""
    color = "green" if delta <= 0 else "yellow"
    _console.print(
        f"\n[bold]Words:[/bold] {result.word_count_a} vs {result.word_count_b} "
        f"[{color}]({sign}{delta})[/{color}]"
    )
    _console.print(
        f"[bold]Highlights:[/bold] {result.highlight_count_a} vs {result.highlight_count_b}"
    )


@cli.command()
@click.option("--profile", "-p", default="general", help="Build profile name.")
@click.option(
    "--jd",
    required=True,
    type=click.Path(exists=True),
    help="Path to a plain-text job description file.",
)
def match(profile: str, jd: str) -> None:
    """Match CV keywords against a job description."""
    from cvloom.match import analyze_match

    root = _root()
    resolved = _resolve(root, profile, public=True)

    jd_text = Path(jd).read_text(encoding="utf-8")
    _warn_if_not_a_job_posting(jd_text, jd, resolved.locale.code)
    report = analyze_match(resolved, jd_text)

    _console.print(
        f"[bold]Coverage:[/bold] {report.cv_keywords_coverage:.0%} "
        f"({len(report.matched)} of {len(report.matched) + len(report.gaps)} JD keywords found)"
    )
    _console.print(f"[bold]JD keyword count:[/bold] {report.jd_word_count}")
    _console.print()

    if report.top_jd_keywords:
        table = Table(title="Top JD Keywords")
        table.add_column("Keyword", style="bold")
        table.add_column("JD Freq", justify="right")
        table.add_column("In CV?", justify="center")
        table.add_column("CV Sections")
        for kw, freq in report.top_jd_keywords:
            cv_sections = ""
            in_cv = "[red]✗[/red]"
            for m in report.matched:
                if m.keyword == kw:
                    in_cv = "[green]✓[/green]"
                    cv_sections = ", ".join(m.found_in)
                    break
            table.add_row(kw, str(freq), in_cv, cv_sections)
        _console.print(table)

    if report.gaps:
        _console.print()
        _console.print(f"[bold yellow]Gaps ({len(report.gaps)}):[/bold yellow]")
        for gap in report.gaps[:30]:
            hint = report.suggestions.get(gap, "")
            suffix = f"  [dim]→ add to {hint}[/dim]" if hint else ""
            _console.print(f"  [red]✗[/red] {gap}{suffix}")
        if len(report.gaps) > 30:
            _console.print(f"  ... and {len(report.gaps) - 30} more")

    if report.reorder_hints:
        _console.print()
        _console.print("[bold]Reorder Suggestions[/bold]")
        for hint in report.reorder_hints:
            _console.print(f"  [cyan]↕[/cyan]  {hint}")
