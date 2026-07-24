"""cvloom CLI entry point."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from cvloom import builder, export, importer, linter, projects
from cvloom import trim as trim_mod
from cvloom.diff import compare
from cvloom.models import ResolvedProfile

_console = Console()
_err = Console(stderr=True)


def _root() -> Path:
    """Return the project root — the directory from which cvloom is invoked."""
    return Path.cwd()


def _render_resolve_error(exc: builder.ResolveError) -> None:
    """Print a ResolveError's messages to stderr."""
    _err.print("[bold red]Validation errors:[/bold red]")
    for e in exc.errors:
        _err.print(f"  [red]✗[/red] {e}")


def _emit_warnings(warnings: list[str]) -> None:
    for w in warnings:
        _err.print(f"[yellow]Warning:[/yellow] {w}")


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


@click.group()
@click.version_option()
def cli() -> None:
    """cvloom — manage your CV as YAML, build tailored PDF/HTML outputs."""


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def _lint_breakdown(findings: list[linter.LintFinding]) -> str:
    """Render the per-category writing-lint breakdown (no single 0–100 score)."""
    counts = linter.category_counts(findings)
    return ", ".join(f"{cat}: {n}" for cat, n in counts.items())


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
def build(
    profile: str,
    template: str | None,
    output_dir: str,
    public: bool,
    skip_pdf: bool,
    run_check: bool,
    strict: int | None,
) -> None:
    """Build CV outputs for a given profile."""
    root = _root()
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
    _console.print(f"[green]✓[/green] HTML  → {result.html_path}")
    if result.pdf_path:
        _console.print(f"[green]✓[/green] PDF   → {result.pdf_path}")
    summary = _section_summary(result.resolved.data, result.resolved.show_sections)
    _console.print(f"[dim]  {result.words} words · ~{result.pages} page(s)  [{summary}][/dim]")
    if result.pages > 2 and not result.resolved.template_name.startswith("cv/academic"):
        _console.print(
            "[yellow]Warning:[/yellow] Output exceeds 2 pages. "
            "Consider trimming content or using include_tags to filter sections."
        )

    if run_check or strict is not None:
        findings = linter.lint(result.resolved)
        count = len(findings)
        color = "green" if count == 0 else "yellow" if count <= 5 else "red"
        _console.print(
            f"[{color}]Writing lint: {count} issue(s)[/{color}] — {_lint_breakdown(findings)}"
        )
        if strict is not None and count > strict:
            _console.print(f"[red]{count} findings exceed the --strict budget of {strict}.[/red]")
            raise SystemExit(1)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


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
    if not findings:
        _console.print("[green]✓ No issues found.[/green]")
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
    default=1,
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


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@cli.command("export")
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json-resume", "markdown", "linkedin", "docx"]),
    required=True,
    help="Export format.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output file path (inferred from profile and format if omitted).",
)
def export_cmd(profile: str, fmt: str, output: str | None) -> None:
    """Export CV data to an external format."""
    root = _root()
    resolved = _resolve(root, profile, public=False)
    if fmt == "json-resume":
        out_path = Path(output) if output else root / "dist" / f"{profile}.resume.json"
        export.export_json_resume(resolved, out_path)
        _console.print(f"[green]✓[/green] JSON Resume → {out_path}")
    elif fmt == "markdown":
        out_path = Path(output) if output else root / "dist" / f"{profile}.resume.md"
        export.export_markdown(resolved, out_path)
        _console.print(f"[green]✓[/green] Markdown → {out_path}")
    elif fmt == "linkedin":
        out_path = Path(output) if output else root / "dist" / f"{profile}.linkedin.txt"
        warnings = export.export_linkedin(resolved, out_path)
        _console.print(f"[green]✓[/green] LinkedIn → {out_path}")
        for w in warnings:
            _console.print(f"[yellow]⚠[/yellow]  {w}")
    elif fmt == "docx":
        out_path = Path(output) if output else root / "dist" / f"{profile}.resume.docx"
        export.export_docx(resolved, out_path)
        _console.print(f"[green]✓[/green] DOCX → {out_path}")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


@cli.command("import")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json-resume"]),
    default="json-resume",
    show_default=True,
    help="Source format.",
)
@click.option("--dry-run", is_flag=True, help="Show what would be written without writing.")
@click.option("--force", is_flag=True, help="Overwrite existing data/private files.")
def import_cmd(source: Path, fmt: str, dry_run: bool, force: bool) -> None:
    """Import a JSON Resume file into cvloom's data/ and private/ layout.

    Contact details (name, email, phone, location, social handles) are written
    to private/contact.yaml; everything else to data/.
    """
    root = _root()
    data_dir = root / "data"
    private_dir = root / "private"

    try:
        doc = importer.load_json_resume(source)
        imported = importer.from_json_resume(doc)
    except importer.ImportProblem as exc:
        _err.print(f"[bold red]Import failed:[/bold red] {exc}")
        raise SystemExit(1) from exc

    errors = importer.validate_imported(imported)
    if errors:
        _err.print("[bold red]Imported data failed validation:[/bold red]")
        for err in errors:
            _err.print(f"  [red]✗[/red] {err}")
        raise SystemExit(1)

    plans = importer.plan_writes(imported, data_dir, private_dir)
    conflicts = [p for p in plans if p.exists]

    if dry_run:
        _console.print("[bold]Would write:[/bold]")
        for p in plans:
            tag = " [yellow](overwrites)[/yellow]" if p.exists else ""
            fence = " [dim](private)[/dim]" if p.is_private else ""
            _console.print(f"  {p.path.relative_to(root)}{fence}{tag}")
        return

    if conflicts and not force:
        _err.print("[bold red]Refusing to overwrite existing files:[/bold red]")
        for p in conflicts:
            _err.print(f"  [red]✗[/red] {p.path.relative_to(root)}")
        _err.print("Re-run with [bold]--force[/bold] to overwrite, or [bold]--dry-run[/bold].")
        raise SystemExit(1)

    written = importer.write_imported(imported, data_dir, private_dir)
    for path in written:
        _console.print(f"[green]✓[/green] {path.relative_to(root)}")
    _console.print(
        f"\n[green]Imported {len(written)} file(s).[/green] "
        "Contact PII (if any) went to [bold]private/contact.yaml[/bold]."
    )


# ---------------------------------------------------------------------------
# match
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files.")
def init(force: bool) -> None:
    """Scaffold project structure, install pre-commit hook, verify .gitignore."""
    root = _root()
    _init_gitignore(root)
    _init_directories(root)
    _init_data_files(root, force)
    _init_profile(root, force)
    _init_private(root, force)
    for mf in _MANAGED_FILES:
        _scaffold_managed(mf, root, force)
    _console.print("\n[bold green]✓ cvloom project initialised.[/bold green]")
    _console.print("  Next steps:")
    _console.print("  1. Edit files in [bold]data/[/bold] with your CV content.")
    _console.print("  2. Add your contact details to [bold]private/contact.yaml[/bold].")
    _console.print("  3. Run [bold]cvloom build[/bold].")
    _console.print(
        "  4. To publish to GitHub Pages: Settings → Pages → Source"
        " [bold]GitHub Actions[/bold], then add the repo variable"
        " [bold]DEPLOY_PAGES=true[/bold] (see .github/workflows/publish-cv.yml)."
    )


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--force", is_flag=True, help="Overwrite out-of-date/missing files with the packaged versions."
)
def sync(force: bool) -> None:
    """Refresh cvloom-managed scaffold files (pre-commit hook, publish workflow).

    After `uv tool upgrade cvloom`, run this to bring the scaffolded files up to
    the installed version. Without --force it only reports status.
    """
    root = _root()
    _status_style = {
        "current": ("green", "up to date"),
        "outdated": ("yellow", "out of date"),
        "missing": ("yellow", "missing"),
        "unavailable": ("dim", "unavailable (not a git repo?)"),
    }
    stale: list[_ManagedFile] = []
    for mf in _MANAGED_FILES:
        status = _managed_status(mf, root)
        color, text = _status_style[status]
        _console.print(f"[{color}]•[/{color}] {mf.dest_rel} — {text}")
        if status in ("outdated", "missing"):
            stale.append(mf)

    if not stale:
        _console.print("\n[green]✓ All managed files are up to date.[/green]")
        return

    if not force:
        _console.print(
            f"\n[yellow]{len(stale)} file(s) need updating.[/yellow]"
            " Re-run with [bold]--force[/bold] to overwrite them."
        )
        return

    for mf in stale:
        _write_managed(mf, root)
        _console.print(f"[green]✓[/green] Updated {mf.dest_rel}")


# ---------------------------------------------------------------------------
# list-projects
# ---------------------------------------------------------------------------


@cli.command("list-projects")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can be repeated).")
def list_projects(tag: tuple[str, ...]) -> None:
    """List all projects in data/projects/, optionally filtered by tag."""
    root = _root()
    try:
        summaries = projects.list_projects(root, list(tag) if tag else None)
    except FileNotFoundError:
        _err.print("[yellow]No data/projects/ directory found.[/yellow]")
        raise SystemExit(1) from None

    if not summaries:
        if tag:
            _console.print(f"[dim]No projects match tag(s): {', '.join(tag)}[/dim]")
        else:
            _console.print("[dim]No projects found in data/projects/.[/dim]")
        return

    for p in summaries:
        tags_str = ("  [dim]" + ", ".join(p.tags) + "[/dim]") if p.tags else ""
        _console.print(f"[bold]{p.name}[/bold]{tags_str}")
        if p.description:
            desc = p.description.strip()
            if len(desc) > 80:
                desc = desc[:77] + "..."
            _console.print(f"  [dim]{desc}[/dim]")

    _console.print(f"\n[dim]{len(summaries)} project(s)[/dim]")


# ---------------------------------------------------------------------------
# list-profiles
# ---------------------------------------------------------------------------


@cli.command("list-profiles")
def list_profiles() -> None:
    """List all build profiles in profiles/."""
    root = _root()
    try:
        summaries = projects.list_profiles(root)
    except FileNotFoundError:
        _err.print("[yellow]No profiles/ directory found.[/yellow]")
        raise SystemExit(1) from None

    if not summaries:
        _console.print("[dim]No profiles found in profiles/.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Profile")
    table.add_column("Template")
    table.add_column("Output")
    table.add_column("Tags")
    table.add_column("Job context")

    for p in summaries:
        tags = ", ".join(p.include_tags) or "—"
        jctx = p.job_context or {}
        job_str = ""
        if jctx.get("role") and jctx.get("company"):
            job_str = f"{jctx['role']} @ {jctx['company']}"
        elif jctx.get("company"):
            job_str = jctx["company"]
        table.add_row(
            f"[bold]{p.name}[/bold]",
            p.template,
            p.output_filename,
            tags,
            job_str or "—",
        )

    _console.print(table)
    _console.print(f"\n[dim]{len(summaries)} profile(s)  ·  run: cvloom build --profile NAME[/dim]")


# ---------------------------------------------------------------------------
# ai
# ---------------------------------------------------------------------------


@cli.group()
def ai() -> None:
    """AI-powered CV analysis features (requires AI provider configuration)."""


@ai.command("config")
def ai_config() -> None:
    """Show current AI provider configuration and setup instructions."""
    from cvloom.ai.provider import get_config

    cfg = get_config()
    if cfg["configured"]:
        _console.print("[green]AI provider: configured[/green]")
        _console.print(f"  Base URL:  {cfg['base_url']}")
        _console.print(f"  Model:     {cfg['model']}")
        key_status = "***set***" if cfg["api_key_set"] else "[yellow]not set[/yellow]"
        _console.print(f"  API key:   {key_status}")
    else:
        _console.print("[yellow]AI provider: not configured[/yellow]")
        _console.print()
        _console.print("Set the following environment variables to enable AI features:")
        env_rows = [
            ("CVLOOM_AI_BASE_URL", "e.g. http://localhost:11434/v1  (Ollama)"),
            ("CVLOOM_AI_API_KEY", 'your API key (use "ollama" for local Ollama)'),
            ("CVLOOM_AI_MODEL", "e.g. gemma3:27b, gpt-4o, claude-sonnet-4-6"),
        ]
        for var_name, hint in env_rows:
            _console.print(f"  [bold]{var_name:<21}[/bold]  {hint}")
        _console.print()
        _console.print("[dim]Quickstart options:[/dim]")
        _console.print("  [dim]• Local (Ollama):    https://ollama.ai[/dim]")
        _console.print(
            "  [dim]• Cloud proxy:       https://litellm.vercel.app/docs/proxy/quick_start[/dim]"
        )


@ai.command("review")
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
def ai_review(profile: str) -> None:
    """Score each CV section with AI-powered feedback."""
    from cvloom.ai import AINotConfiguredError, get_client, get_model, is_configured
    from cvloom.ai.analyzer import review

    if not is_configured():
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    root = _root()
    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client()
        result = review(resolved, client, get_model())
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    score_color = (
        "green" if result.overall_score >= 7 else "yellow" if result.overall_score >= 5 else "red"
    )
    _console.print(f"\n[bold]CV Review[/bold]  profile: {profile}")
    _console.print(f"Overall score: [{score_color}]{result.overall_score:.1f}/10[/{score_color}]\n")

    for sec in result.sections:
        color = "green" if sec.score >= 7 else "yellow" if sec.score >= 5 else "red"
        _console.print(f"[bold]{sec.section}[/bold]  [{color}]{sec.score:.1f}/10[/{color}]")
        for s in sec.strengths:
            _console.print(f"  [green]+[/green] {s}")
        for w in sec.weaknesses:
            _console.print(f"  [red]–[/red] {w}")
        for sg in sec.suggestions:
            _console.print(f"  [dim]→[/dim] {sg}")
        _console.print()

    if result.top_priorities:
        _console.print("[bold]Top priorities:[/bold]")
        for i, p in enumerate(result.top_priorities, 1):
            _console.print(f"  {i}. {p}")


@ai.command("cover")
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--jd",
    "jd_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to job description file.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write cover letter to this file instead of printing.",
)
def ai_cover(profile: str, jd_file: str, output: str | None) -> None:
    """Generate a tailored cover letter from your CV and a job description."""
    from cvloom.ai import AINotConfiguredError, get_client, get_model, is_configured
    from cvloom.ai.cover import generate_cover

    if not is_configured():
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    jd_text = Path(jd_file).read_text(encoding="utf-8")
    root = _root()
    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client()
        result = generate_cover(resolved, jd_text, client, get_model())
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    if output:
        Path(output).write_text(result.letter, encoding="utf-8")
        _console.print(
            f"[green]✓[/green] Cover letter written to {output}  ({result.word_count} words)"
        )
    else:
        _console.print(f"\n[bold]Cover Letter[/bold]  profile: {profile}\n")
        _console.print(result.letter)
        _console.print(f"\n[dim]{result.word_count} words[/dim]")
        if result.key_alignments:
            _console.print("\n[bold]Key alignments:[/bold]")
            for a in result.key_alignments:
                _console.print(f"  • {a}")


@ai.command("suggest")
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--role",
    "role_context",
    default="",
    help="Target role description (e.g. 'Senior Backend Engineer').",
)
def ai_suggest(profile: str, role_context: str) -> None:
    """Suggest content improvements: new bullets, skills, rewordings for a target role."""
    from cvloom.ai import AINotConfiguredError, get_client, get_model, is_configured
    from cvloom.ai.suggest import suggest

    if not is_configured():
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    root = _root()
    resolved = _resolve(root, profile, public=True)

    effective_role = role_context or (resolved.profile.get("job_context") or {}).get("role", "")

    try:
        client = get_client()
        result = suggest(resolved, client, get_model(), role_context=effective_role)
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    role_label = f"  target role: {effective_role}" if effective_role else ""
    _console.print(f"\n[bold]Improvement Suggestions[/bold]  profile: {profile}{role_label}\n")

    if result.summary:
        _console.print(result.summary)
        _console.print()

    _TYPE_COLOUR = {"bullet": "cyan", "skill": "green", "reword": "yellow", "remove": "red"}

    for s in result.suggestions:
        colour = _TYPE_COLOUR.get(s.type, "white")
        badge = f"[{colour}][{s.type}][/{colour}]"
        context = s.section + (f" / {s.entry}" if s.entry else "")
        _console.print(f"  {badge} [dim]{context}[/dim]")
        if s.current:
            _console.print(f"    [dim]before:[/dim] {s.current}")
        _console.print(f"    [green]{s.suggested}[/green]")
        _console.print(f"    [dim]{s.rationale}[/dim]")
        _console.print()

    if result.missing_skills:
        _console.print("[bold]Missing skills worth adding:[/bold]")
        for skill in result.missing_skills:
            _console.print(f"  [yellow]•[/yellow] {skill}")


@ai.command("align")
@click.option(
    "--profile",
    "-p",
    default="general",
    show_default=True,
    help="Profile name (without .yaml extension).",
)
@click.option(
    "--jd",
    "jd_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to job description file.",
)
def ai_align(profile: str, jd_file: str) -> None:
    """Qualitative AI analysis of how well your CV aligns with a job description."""
    from cvloom.ai import AINotConfiguredError, get_client, get_model, is_configured
    from cvloom.ai.align import align

    if not is_configured():
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    jd_text = Path(jd_file).read_text(encoding="utf-8")
    root = _root()
    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client()
        result = align(resolved, jd_text, client, get_model())
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    score = result.alignment_score
    score_colour = "green" if score >= 7 else ("yellow" if score >= 5 else "red")
    _console.print(f"\n[bold]JD Alignment[/bold]  profile: {profile}\n")
    _console.print(f"[bold]Alignment Score:[/bold] [{score_colour}]{score:.1f}/10[/{score_colour}]")
    _console.print()
    _console.print(result.narrative)
    if result.strengths:
        _console.print("\n[bold]Strengths:[/bold]")
        for s in result.strengths:
            _console.print(f"  [green]✓[/green] {s}")
    if result.tone_gaps:
        _console.print("\n[bold]Tone & Framing Gaps:[/bold]")
        for g in result.tone_gaps:
            _console.print(f"  [yellow]⚠[/yellow] {g}")
    if result.repositioning:
        _console.print("\n[bold]Repositioning Actions:[/bold]")
        for i, r in enumerate(result.repositioning, 1):
            _console.print(f"  {i}. {r}")


def _init_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    private_line = "private/"
    if gi.exists():
        content = gi.read_text()
        if private_line not in content:
            gi.write_text(private_line + "\n" + content)
            _console.print(f"[green]✓[/green] Prepended '{private_line}' to .gitignore")
        else:
            _console.print(f"[dim]  .gitignore already contains '{private_line}'[/dim]")
    else:
        gi.write_text(f"{private_line}\ndist/\n__pycache__/\n*.pyc\n")
        _console.print("[green]✓[/green] Created .gitignore")


def _init_directories(root: Path) -> None:
    for d in ("data/projects", "profiles", "dist", "templates"):
        (root / d).mkdir(parents=True, exist_ok=True)
    _console.print("[green]✓[/green] Created directory structure")


def _init_data_files(root: Path, force: bool) -> None:
    files = {
        "data/basics.yaml": _SAMPLE_BASICS,
        "data/work.yaml": _SAMPLE_WORK,
        "data/education.yaml": _SAMPLE_EDUCATION,
        "data/skills.yaml": _SAMPLE_SKILLS,
    }
    for rel, content in files.items():
        path = root / rel
        if not path.exists() or force:
            path.write_text(content)
            _console.print(f"[green]✓[/green] Created {rel}")
        else:
            _console.print(f"[dim]  {rel} already exists, skipping[/dim]")


def _init_profile(root: Path, force: bool) -> None:
    profiles = {
        "profiles/general.yaml": _SAMPLE_PROFILE,
        "profiles/cover-letter.yaml": _SAMPLE_COVER_LETTER_PROFILE,
    }
    for rel, content in profiles.items():
        path = root / rel
        if not path.exists() or force:
            path.write_text(content)
            _console.print(f"[green]✓[/green] Created {rel}")
        else:
            _console.print(f"[dim]  {rel} already exists, skipping[/dim]")


def _init_private(root: Path, force: bool) -> None:
    private_dir = root / "private"
    private_dir.mkdir(exist_ok=True)
    contact = private_dir / "contact.yaml"
    if not contact.exists() or force:
        contact.write_text(_SAMPLE_CONTACT)
        _console.print("[green]✓[/green] Created private/contact.yaml (GITIGNORED)")
    else:
        _console.print("[dim]  private/contact.yaml already exists, skipping[/dim]")

    cover_letters = private_dir / "cover-letters"
    cover_letters.mkdir(exist_ok=True)

    gitignore_private = private_dir / ".gitignore"
    if not gitignore_private.exists():
        gitignore_private.write_text("*\n")


# ---------------------------------------------------------------------------
# Managed scaffold files (shared by `init` and `sync`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ManagedFile:
    """A file cvloom scaffolds into a project and can later re-sync."""

    label: str
    src: Path  # source inside the installed package
    dest_rel: str  # destination relative to the project root
    executable: bool = False
    requires_git_dir: bool = False  # dest lives under .git/ (per-clone; needs a git repo)


_PKG_DIR = Path(__file__).parent

_MANAGED_FILES: list[_ManagedFile] = [
    _ManagedFile(
        "pre-commit PII scanner hook",
        _PKG_DIR / "hooks" / "pre-commit",
        ".git/hooks/pre-commit",
        executable=True,
        requires_git_dir=True,
    ),
    _ManagedFile(
        "GitHub Pages publish workflow",
        _PKG_DIR / "scaffold" / "workflows" / "publish-cv.yml",
        ".github/workflows/publish-cv.yml",
    ),
]


def _managed_status(mf: _ManagedFile, root: Path) -> str:
    """Status of a managed file: unavailable / missing / current / outdated."""
    if not mf.src.exists():
        return "unavailable"
    if mf.requires_git_dir and not (root / ".git" / "hooks").exists():
        return "unavailable"
    dest = root / mf.dest_rel
    if not dest.exists():
        return "missing"
    if dest.read_bytes() == mf.src.read_bytes():
        return "current"
    return "outdated"


def _write_managed(mf: _ManagedFile, root: Path) -> None:
    dest = root / mf.dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mf.src, dest)
    if mf.executable:
        dest.chmod(0o755)


def _scaffold_managed(mf: _ManagedFile, root: Path, force: bool) -> None:
    """Write a managed file during `init` (create-if-absent; overwrite on --force)."""
    status = _managed_status(mf, root)
    if status == "unavailable":
        if mf.requires_git_dir:
            _console.print(
                f"[yellow]Warning:[/yellow] .git/hooks not found — skipping {mf.label}"
                " (not a git repo?)."
            )
        else:
            _console.print(f"[yellow]Warning:[/yellow] {mf.label} source not found, skipping.")
        return
    if status in ("current", "outdated") and not force:
        _console.print(f"[dim]  {mf.dest_rel} already exists, skipping[/dim]")
        return
    _write_managed(mf, root)
    _console.print(f"[green]✓[/green] Created {mf.dest_rel}")


# ---------------------------------------------------------------------------
# Sample file content
# ---------------------------------------------------------------------------

_SAMPLE_BASICS = """\
headline: "Senior Software Engineer"
summary: >
  Experienced backend engineer with 8+ years building scalable distributed systems.
  Passionate about developer tooling, open-source, and clean architecture.
public_links:
  - label: GitHub
    url: https://github.com/SWEStash
  - label: Website
    url: https://yourwebsite.example.com
"""

_SAMPLE_WORK = """\
- company: Acme Corp
  title: Senior Backend Engineer
  location: Remote
  start_date: "2021-03"
  end_date: Present
  highlights:
    - Led migration of monolith to microservices, reducing deploy time by 60%.
    - Designed event-driven pipeline processing 50k events/sec with Kafka.
  tags: [python, kafka, microservices, aws]

- company: Previous Inc
  title: Software Engineer
  location: "New York, USA"
  start_date: "2018-06"
  end_date: "2021-02"
  highlights:
    - Built REST API serving 2M daily active users.
    - Reduced p99 latency from 800ms to 120ms through query optimization.
  tags: [python, postgresql, redis]
"""

_SAMPLE_EDUCATION = """\
- institution: State University
  degree: "Bachelor of Science"
  field: Computer Science
  location: "Anytown, USA"
  start_date: "2014"
  end_date: "2018"
  highlights:
    - GPA 3.8/4.0
    - Teaching assistant for Data Structures course
"""

_SAMPLE_SKILLS = """\
- category: Languages
  items:
    - name: Python
      level: expert
    - name: Go
      level: advanced
    - name: SQL
      level: advanced

- category: Frameworks & Tools
  items: [FastAPI, Django, PostgreSQL, Redis, Kafka, Docker, Kubernetes]

- category: Cloud
  items: [AWS, GCP, Terraform]
"""

_SAMPLE_PROFILE = """\
template: cv/ats-single
output_filename: cv
sections:
  work: true
  education: true
  skills: true
  projects: true
"""

_SAMPLE_COVER_LETTER_PROFILE = """\
template: cover-letter/standard
output_filename: cover-letter
job_context:
  company: "Target Company"
  role: "Senior Software Engineer"
  hiring_manager: "Hiring Manager"
  notes: |
    I am writing to express my interest in the **Senior Software Engineer** position
    at Target Company.

    My experience building scalable systems and developer tooling makes me a strong
    fit for this role. I would welcome the opportunity to discuss further.
"""

_SAMPLE_CONTACT = """\
name: "Your Name"
email: "your.email@example.com"
phone: "+1 (555) 000-0000"
location: "City, Country"
website: "https://yourwebsite.example.com"
linkedin: "yourlinkedin"
github: "SWEStash"
"""
