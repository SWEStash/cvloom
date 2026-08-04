"""Project scaffolding for ``cvloom init`` / ``cvloom sync``.

Writes the sample ``data/``, ``profiles/`` and ``private/`` files (content under
:mod:`cvloom.scaffold.samples`), and owns the managed-file registry — the
pre-commit PII hook and the Pages publish workflow — shared by ``init`` and ``sync``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

_console = Console()

_SAMPLES_DIR = Path(__file__).parent / "samples"
_WORKFLOWS_DIR = Path(__file__).parent / "workflows"
_PKG_DIR = Path(__file__).parent.parent  # the cvloom/ package root


def _sample(name: str) -> str:
    return (_SAMPLES_DIR / name).read_text()


def init_gitignore(root: Path) -> None:
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


def init_directories(root: Path) -> None:
    for d in ("data/projects", "profiles", "dist", "templates"):
        (root / d).mkdir(parents=True, exist_ok=True)
    _console.print("[green]✓[/green] Created directory structure")


def init_data_files(root: Path, force: bool) -> None:
    files = {
        "data/basics.yaml": _sample("basics.yaml"),
        "data/work.yaml": _sample("work.yaml"),
        "data/education.yaml": _sample("education.yaml"),
        "data/skills.yaml": _sample("skills.yaml"),
    }
    for rel, content in files.items():
        path = root / rel
        if not path.exists() or force:
            path.write_text(content)
            _console.print(f"[green]✓[/green] Created {rel}")
        else:
            _console.print(f"[dim]  {rel} already exists, skipping[/dim]")


def init_profile(root: Path, force: bool) -> None:
    profiles = {
        "profiles/general.yaml": _sample("profile-general.yaml"),
        "profiles/cover-letter.yaml": _sample("profile-cover-letter.yaml"),
    }
    for rel, content in profiles.items():
        path = root / rel
        if not path.exists() or force:
            path.write_text(content)
            _console.print(f"[green]✓[/green] Created {rel}")
        else:
            _console.print(f"[dim]  {rel} already exists, skipping[/dim]")


def init_private(root: Path, force: bool) -> None:
    private_dir = root / "private"
    private_dir.mkdir(exist_ok=True)
    contact = private_dir / "contact.yaml"
    if not contact.exists() or force:
        contact.write_text(_sample("contact.yaml"))
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
class ManagedFile:
    """A file cvloom scaffolds into a project and can later re-sync."""

    label: str
    src: Path  # source inside the installed package
    dest_rel: str  # destination relative to the project root
    executable: bool = False
    requires_git_dir: bool = False  # dest lives under .git/ (per-clone; needs a git repo)


MANAGED_FILES: list[ManagedFile] = [
    ManagedFile(
        "pre-commit PII scanner hook",
        _PKG_DIR / "hooks" / "pre-commit",
        ".git/hooks/pre-commit",
        executable=True,
        requires_git_dir=True,
    ),
    ManagedFile(
        "GitHub Pages publish workflow",
        _WORKFLOWS_DIR / "publish-cv.yml",
        ".github/workflows/publish-cv.yml",
    ),
]


def managed_status(mf: ManagedFile, root: Path) -> str:
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


def write_managed(mf: ManagedFile, root: Path) -> None:
    dest = root / mf.dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mf.src, dest)
    if mf.executable:
        dest.chmod(0o755)


def scaffold_managed(mf: ManagedFile, root: Path, force: bool) -> None:
    """Write a managed file during `init` (create-if-absent; overwrite on --force)."""
    status = managed_status(mf, root)
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
    write_managed(mf, root)
    _console.print(f"[green]✓[/green] Created {mf.dest_rel}")
