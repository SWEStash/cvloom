"""Commands that move data in or out: export, import, init, sync."""

from __future__ import annotations

from pathlib import Path

import click
from rich.markup import escape

from cvloom import (
    config,
    export,
    importer,
    scaffold,
)
from cvloom import locale as locale_mod
from cvloom.cli.group import cli
from cvloom.cli.shared import (
    _console,
    _err,
    _resolve,
    _root,
)


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
