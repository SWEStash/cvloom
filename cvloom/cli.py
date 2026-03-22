"""cvloom CLI entry point."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from cvloom import builder

_console = Console()
_err = Console(stderr=True)

def _root() -> Path:
    """Return the project root — the directory from which cvloom is invoked."""
    return Path.cwd()


@click.group()
@click.version_option()
def cli() -> None:
    """cvloom — manage your CV as YAML, build tailored PDF/HTML outputs."""


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--profile", "-p", default="general",
    show_default=True, help="Profile name (without .yaml extension).",
)
@click.option(
    "--template", "-t", default=None,
    help="Override template (e.g. cv/modern-single).",
)
@click.option(
    "--output-dir", "-o", default="dist",
    show_default=True, help="Output directory.",
)
@click.option(
    "--public", is_flag=True, default=False,
    help="Use placeholder contact data (safe for CI/GitHub Pages).",
)
@click.option(
    "--skip-pdf", is_flag=True, default=False,
    help="Skip PDF generation (HTML only).",
)
def build(
    profile: str, template: str | None, output_dir: str,
    public: bool, skip_pdf: bool,
) -> None:
    """Build CV outputs for a given profile."""
    root = _root()
    builder.build(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        output_dir=root / output_dir,
        profile_name=profile,
        template_override=template,
        public=public,
        skip_pdf=skip_pdf,
    )


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files.")
def init(force: bool) -> None:
    """Scaffold project structure, install pre-commit hook, verify .gitignore."""
    root = _root()
    _init_gitignore(root, force)
    _init_directories(root, force)
    _init_data_files(root, force)
    _init_profile(root, force)
    _init_private(root, force)
    _install_hook(root)
    _console.print("\n[bold green]✓ cvloom project initialised.[/bold green]")
    _console.print("  Next steps:")
    _console.print("  1. Edit files in [bold]data/[/bold] with your CV content.")
    _console.print("  2. Add your contact details to [bold]private/contact.yaml[/bold].")
    _console.print("  3. Run [bold]cvloom build[/bold].")


# ---------------------------------------------------------------------------
# list-projects
# ---------------------------------------------------------------------------

@cli.command("list-projects")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can be repeated).")
def list_projects(tag: tuple[str, ...]) -> None:
    """List all projects in data/projects/, optionally filtered by tag."""
    root = _root()
    projects_dir = root / "data" / "projects"
    if not projects_dir.exists():
        _err.print("[yellow]No data/projects/ directory found.[/yellow]")
        raise SystemExit(1)

    files = sorted(projects_dir.glob("*.yaml"))
    if not files:
        _console.print("[dim]No projects found in data/projects/.[/dim]")
        return

    count = 0
    for pf in files:
        p = yaml.safe_load(pf.read_text()) or {}
        ptags: list[str] = p.get("tags", []) or []
        if tag and not (set(ptags) & set(tag)):
            continue
        tags_str = ("  [dim]" + ", ".join(ptags) + "[/dim]") if ptags else ""
        _console.print(f"[bold]{p.get('name', pf.stem)}[/bold]{tags_str}")
        if p.get("description"):
            desc = str(p["description"]).strip()
            if len(desc) > 80:
                desc = desc[:77] + "..."
            _console.print(f"  [dim]{desc}[/dim]")
        count += 1

    if count == 0:
        _console.print(f"[dim]No projects match tag(s): {', '.join(tag)}[/dim]")
    else:
        _console.print(f"\n[dim]{count} project(s)[/dim]")


# ---------------------------------------------------------------------------
# list-profiles
# ---------------------------------------------------------------------------

@cli.command("list-profiles")
def list_profiles() -> None:
    """List all build profiles in profiles/."""
    root = _root()
    profiles_dir = root / "profiles"
    if not profiles_dir.exists():
        _err.print("[yellow]No profiles/ directory found.[/yellow]")
        raise SystemExit(1)

    files = sorted(profiles_dir.glob("*.yaml"))
    if not files:
        _console.print("[dim]No profiles found in profiles/.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Profile")
    table.add_column("Template")
    table.add_column("Output")
    table.add_column("Tags")
    table.add_column("Job context")

    for pf in files:
        p = yaml.safe_load(pf.read_text()) or {}
        tmpl = p.get("template", "")
        out = p.get("output_filename") or pf.stem
        tags = ", ".join(p.get("include_tags") or []) or "—"
        jctx = p.get("job_context") or {}
        job_str = ""
        if jctx.get("role") and jctx.get("company"):
            job_str = f"{jctx['role']} @ {jctx['company']}"
        elif jctx.get("company"):
            job_str = jctx["company"]
        table.add_row(
            f"[bold]{pf.stem}[/bold]",
            tmpl,
            out,
            tags,
            job_str or "—",
        )

    _console.print(table)
    _console.print(f"\n[dim]{len(files)} profile(s)  ·  run: cvloom build --profile NAME[/dim]")


def _init_gitignore(root: Path, force: bool) -> None:
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


def _init_directories(root: Path, force: bool) -> None:
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


def _install_hook(root: Path) -> None:
    hooks_src = Path(__file__).parent / "hooks" / "pre-commit"
    git_hooks = root / ".git" / "hooks"
    if not git_hooks.exists():
        _console.print(
            "[yellow]Warning:[/yellow] .git/hooks directory not found"
            " — is this a git repo? Skipping hook installation."
        )
        return

    dst = git_hooks / "pre-commit"
    if hooks_src.exists():
        shutil.copy2(hooks_src, dst)
        dst.chmod(0o755)
        _console.print("[green]✓[/green] Installed pre-commit PII scanner hook")
    else:
        _console.print("[yellow]Warning:[/yellow] hooks/pre-commit source not found, skipping.")


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
