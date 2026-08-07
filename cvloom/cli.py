"""cvloom CLI entry point."""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from cvloom import (
    builder,
    config,
    export,
    importer,
    linter,
    linter_locales,
    projects,
    renderer,
    scaffold,
    sections,
    templates_meta,
)
from cvloom import (
    extract as extract_mod,
)
from cvloom import (
    locale as locale_mod,
)
from cvloom import trim as trim_mod
from cvloom.diff import compare
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


def _friendly(exc: BaseException) -> str:
    """Return a one-line description of ``exc`` fit for someone who is not us.

    Only the exception types a user can provoke get a rewrite; anything else falls
    through to ``TypeName: message``.
    """
    if isinstance(exc, builder.ResolveError):
        return "; ".join(exc.errors)
    if isinstance(exc, FileNotFoundError):
        # loader raises these with a written message and no filename attached.
        return str(exc) if exc.filename is None else f"File not found: {exc.filename}"
    if isinstance(exc, IsADirectoryError):
        return f"Expected a file, got a directory: {exc.filename}"
    if isinstance(exc, PermissionError):
        return f"Permission denied: {exc.filename}"
    if isinstance(exc, yaml.YAMLError):
        return f"Invalid YAML — {exc}"
    return f"{type(exc).__name__}: {exc}"


class _CvloomCLI(click.Group):
    """Group that turns an unhandled exception into a message instead of a traceback.

    Handled on the group so no command can forget it. `--verbose` puts the
    traceback back. Click's own exceptions and `SystemExit` pass through untouched.

    `click.exceptions.Exit` is one of those: it subclasses `RuntimeError`, not
    `ClickException` or `SystemExit`, so it has to be named explicitly. It is what
    `--help` and `--version` raise to stop the command.
    """

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except (
            click.ClickException,
            click.exceptions.Abort,
            click.exceptions.Exit,
            SystemExit,
        ):
            raise
        except Exception as exc:
            if ctx.params.get("verbose"):
                traceback.print_exception(exc)
                raise SystemExit(1) from None
            _err.print(f"[bold red]Error:[/bold red] {_friendly(exc)}")
            _err.print("[dim]Re-run with --verbose to see the full traceback.[/dim]")
            raise SystemExit(1) from None


@click.group(cls=_CvloomCLI)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show the full traceback when a command fails.",
)
@click.version_option()
def cli(verbose: bool) -> None:
    """cvloom — manage your CV as YAML, build tailored PDF/HTML outputs."""
    # Unused here on purpose: declaring the option is what puts it in `--help` and
    # in `ctx.params`, which is where `_CvloomCLI.invoke` reads it from.


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


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


def _write_extracted_text(pdf_path: Path) -> None:
    """Write the PDF's text layer beside it, once per available engine.

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


def _lint_breakdown(findings: list[linter.LintFinding]) -> str:
    """Render the per-category writing-lint breakdown (no single 0–100 score)."""
    counts = linter.category_counts(findings)
    return ", ".join(f"{cat}: {n}" for cat, n in counts.items())


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


def _rule_cell(code: str) -> str:
    """Render rule coverage for *code* in a table cell's worth of space.

    The same partition `_lint_coverage` reports, minus the rule names — a locale
    with a dozen skips would not fit, and `check` is where the full list belongs.
    """
    active, skipped = linter.rules_for(code)
    total = len(active) + len(skipped)
    cell = f"{len(active)} of {total}"
    if len(skipped) == 1:
        cell += f" · skips {skipped[0].rule_id}"
    elif skipped:
        cell += f" · {len(skipped)} skipped"
    return cell


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
        _write_extracted_text(result.pdf_path)

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
    type=click.Choice(["json-resume", "markdown", "text", "docx"]),
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
    elif fmt == "text":
        out_path = Path(output) if output else root / "dist" / f"{profile}.resume.txt"
        export.export_text(resolved, out_path)
        _console.print(f"[green]✓[/green] Text → {out_path}")
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
@click.option(
    "--locale",
    "locale_code",
    default=config.DEFAULT_LOCALE,
    show_default=True,
    help="Language this project operates in. See `cvloom list-locales`.",
)
def init(force: bool, locale_code: str) -> None:
    """Scaffold project structure, install pre-commit hook, verify .gitignore."""
    root = _root()

    # Checked against the shipped packs, not against the config schema, which
    # validates `locale` by pattern only: `es-MX` satisfies the schema and then
    # fails at load with "Unknown locale". Better to refuse before scaffolding a
    # project that cannot build than after.
    if locale_code not in locale_mod.available_locales():
        available = ", ".join(locale_mod.available_locales())
        _err.print(
            f"[bold red]Unknown locale '{escape(locale_code)}'.[/bold red] "
            f"Available locales: {available}"
        )
        raise SystemExit(1)

    scaffold.init_gitignore(root)
    scaffold.init_directories(root)
    scaffold.init_config(root, locale_code, force)
    scaffold.init_data_files(root, force)
    scaffold.init_profile(root, force)
    scaffold.init_private(root, force)
    for mf in scaffold.MANAGED_FILES:
        scaffold.scaffold_managed(mf, root, force)
    _console.print("\n[bold green]✓ cvloom project initialised.[/bold green]")
    _console.print("  Next steps:")
    _console.print(
        f"  1. Edit files in [bold]data/[/bold] with your CV content, in"
        f" [bold]{locale_code}[/bold] (set by cvloom.yaml)."
    )
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
    """Bring a project up to date with the installed cvloom.

    After `uv tool upgrade cvloom`, run this to refresh the scaffolded files
    (pre-commit hook, publish workflow) and to create any project file a newer
    cvloom expects but your project predates — today that is `cvloom.yaml`.
    Without --force it only reports status.
    """
    root = _root()
    # Created when absent, never overwritten — not even by --force. Its content
    # is the user's own choice, which is why it is not a ManagedFile; but a
    # project scaffolded before it existed has made no choice to protect, and
    # leaving it absent is what made upgrading a two-command affair.
    config_missing = not scaffold.config_exists(root)
    if config_missing:
        _console.print(f"[yellow]•[/yellow] {config.CONFIG_FILENAME} — missing")
    _status_style = {
        "current": ("green", "up to date"),
        "outdated": ("yellow", "out of date"),
        "missing": ("yellow", "missing"),
        "unavailable": ("dim", "unavailable (not a git repo?)"),
    }
    stale: list[scaffold.ManagedFile] = []
    for mf in scaffold.MANAGED_FILES:
        status = scaffold.managed_status(mf, root)
        color, text = _status_style[status]
        _console.print(f"[{color}]•[/{color}] {mf.dest_rel} — {text}")
        if status in ("outdated", "missing"):
            stale.append(mf)

    if not stale and not config_missing:
        _console.print("\n[green]✓ Project is up to date.[/green]")
        return

    if not force:
        _console.print(
            f"\n[yellow]{len(stale) + config_missing} file(s) need updating.[/yellow]"
            " Re-run with [bold]--force[/bold] to write them."
        )
        return

    if config_missing:
        scaffold.write_config(root, config.DEFAULT_LOCALE)
        _console.print(
            f"[green]✓[/green] Created {config.CONFIG_FILENAME} (locale: {config.DEFAULT_LOCALE})"
        )
        _console.print(
            "[dim]  A project with no config already behaved as "
            f"'{config.DEFAULT_LOCALE}', so this changes nothing on its own. Set "
            "`locale:` for a project in another language — see `cvloom list-locales`.[/dim]"
        )
    for mf in stale:
        scaffold.write_managed(mf, root)
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
    table.add_column("Narrows")
    table.add_column("Job context")

    for p in summaries:
        tags = ", ".join(p.selected_sections) or "—"
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


@cli.command("list-templates")
def list_templates() -> None:
    """List built-in templates with their PDF text-extraction rating."""
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Template")
    table.add_column("Cols", justify="right")
    table.add_column("Parses")
    table.add_column("Fonts")
    table.add_column("Notes")

    for name in renderer.list_templates():
        meta = templates_meta.info_for(name)
        if meta is None:
            table.add_row(name, "—", "[dim]unrated[/dim]", "—", "")
            continue
        table.add_row(
            f"[bold]{name}[/bold]",
            str(meta.columns),
            _ATS_LABEL[meta.ats],
            meta.fonts,
            meta.summary,
        )

    _console.print(table)
    _console.print(
        "\n[dim]'Parses' is how the rendered PDF survives text extraction — the step "
        "every ATS runs first. It is a property of the layout, not of your writing, "
        "so `cvloom check` does not cover it.[/dim]"
    )
    for name in renderer.list_templates():
        meta = templates_meta.info_for(name)
        if meta is not None and meta.caveat:
            _console.print(f"\n[dim]{name}:[/dim] {meta.caveat}")

    _print_suggested_titles()


def _print_suggested_titles() -> None:
    """Print each template's suggested headings as a pasteable profile block.

    Section headings come from the locale pack, one flat default per key, and a
    profile's `section_titles` is the only way to change them. A template that
    reads better with different wording says so here rather than hardcoding it,
    and this is where a user finds out — most install from PyPI and never open a
    packaged template.
    """
    suggesting = [
        (name, info)
        for name in renderer.list_templates()
        if (info := templates_meta.info_for(name)) is not None and info.suggested_titles
    ]
    if not suggesting:
        return

    _console.print(
        "\n[dim]Headings come from your locale. These templates read better with "
        "wording of their own — paste the block into a profile to use it.[/dim]"
    )
    for name, meta in suggesting:
        _console.print(f"\n[dim]{name}:[/dim]")
        _console.print("[dim]  section_titles:[/dim]")
        for key, title in meta.suggested_titles.items():
            _console.print(f"[dim]    {key}: {title}[/dim]")


# ---------------------------------------------------------------------------
# list-locales
# ---------------------------------------------------------------------------


def _active_locale() -> str | None:
    """The locale of the project we are standing in, or None if there isn't one.

    A project with no `cvloom.yaml` is still a project, and an `en` one — absence
    of the file *is* the default. So the test for "is there a project here" is
    `data/`, not the config file, or every empty directory would report itself as
    an `en` project.

    Degrades silently rather than erroring: `list-locales` answers "what does
    cvloom support", which is true in an empty directory, and it should not
    become the one inspect command that needs a project.
    """
    root = _root()
    if not (root / "data").is_dir() and not (root / config.CONFIG_FILENAME).exists():
        return None
    try:
        return config.load_project_config(root).locale
    except config.ConfigError:
        return None


def _document_cell(code: str) -> str:
    """Render document-pack coverage for *code*, naming what it does not own."""
    try:
        cov = locale_mod.pack_coverage(code)
    except config.ConfigError:
        return "[red]unreadable[/red]"
    if cov.is_complete:
        return "complete"

    parts = []
    if cov.inherited_keys:
        defined = len(locale_mod.PACK_KEYS) - len(cov.inherited_keys)
        parts.append(f"{defined} of {len(locale_mod.PACK_KEYS)} keys")
        parts.append(f"en: {', '.join(cov.inherited_keys)}")
    if cov.missing_titles:
        parts.append(f"{len(cov.missing_titles)} heading(s) unnamed")
    return "[yellow]" + " · ".join(parts) + "[/yellow]"


@cli.command("list-locales")
def list_locales() -> None:
    """List the locales cvloom ships, and how completely each is supported."""
    native = linter_locales.available_locales()
    active = _active_locale()

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Locale")
    table.add_column("Document")
    table.add_column("Lint rules")
    table.add_column("Lint data")

    for code in locale_mod.available_locales():
        label = f"[bold]{code}[/bold]"
        if code == active:
            label += " [dim](this project)[/dim]"
        table.add_row(
            label,
            _document_cell(code),
            _rule_cell(code),
            "native" if code in native else "[yellow]en fallback[/yellow]",
        )

    _console.print(table)
    _console.print(
        "\n[dim]'Document' is what the locale pack writes into the document — the "
        "lang attribute, section headings, the open-ended date word, the --public "
        "placeholder contact, and a cover letter's greeting, sign-off and date. "
        "'Lint data' is a separate axis: the lexicons and thresholds `cvloom check` "
        "grades with.[/dim]"
    )
    _console.print(
        "[dim]The two are resolved independently, so 'en fallback' means a CV in "
        "that language is written correctly and then graded by English "
        "heuristics — not that it is not graded at all.[/dim]"
    )
    if active is None:
        _console.print(
            "\n[dim]Set a project's language with `locale:` in cvloom.yaml, or "
            "scaffold one with `cvloom init --locale CODE`.[/dim]"
        )


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

    cfg = get_config(_root())
    if cfg["configured"]:
        _console.print("[green]AI provider: configured[/green]")
        # Provenance per value, not just the value: with two layers, a stale
        # exported variable quietly beating an explicit cvloom.yaml entry is the
        # confusion this command exists to answer.
        _console.print(f"  Base URL:  {cfg['base_url']} [dim]({cfg['base_url_source']})[/dim]")
        _console.print(f"  Model:     {cfg['model']} [dim]({cfg['model_source']})[/dim]")
        key_status = (
            "***set*** [dim](CVLOOM_AI_API_KEY)[/dim]"
            if cfg["api_key_set"]
            else "[yellow]not set[/yellow]"
        )
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
        _console.print(
            "Or put the endpoint and model in [bold]cvloom.yaml[/bold], which travels with "
            "the project:"
        )
        _console.print("  [dim]ai:[/dim]")
        _console.print("  [dim]  base_url: http://localhost:11434/v1[/dim]")
        _console.print("  [dim]  model: gemma3:27b[/dim]")
        _console.print(
            "  [dim]The API key is never set there — that file is committed. "
            "The environment wins over it.[/dim]"
        )
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

    root = _root()
    if not is_configured(root):
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client(root)
        result = review(resolved, client, get_model(root))
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

    root = _root()
    if not is_configured(root):
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    jd_text = Path(jd_file).read_text(encoding="utf-8")
    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client(root)
        result = generate_cover(resolved, jd_text, client, get_model(root))
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

    root = _root()
    if not is_configured(root):
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    resolved = _resolve(root, profile, public=True)

    effective_role = role_context or (resolved.profile.get("job_context") or {}).get("role", "")

    try:
        client = get_client(root)
        result = suggest(resolved, client, get_model(root), role_context=effective_role)
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

    root = _root()
    if not is_configured(root):
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    jd_text = Path(jd_file).read_text(encoding="utf-8")
    resolved = _resolve(root, profile, public=True)
    try:
        client = get_client(root)
        result = align(resolved, jd_text, client, get_model(root))
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
