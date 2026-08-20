"""The `list-*` commands: projects, profiles, templates, locales."""

from __future__ import annotations

import click
from rich.table import Table

from cvloom import (
    config,
    linter,
    linter_locales,
    projects,
    renderer,
    templates_meta,
)
from cvloom import locale as locale_mod
from cvloom.cli.group import cli
from cvloom.cli.shared import (
    _ATS_LABEL,
    _console,
    _err,
    _root,
)


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
