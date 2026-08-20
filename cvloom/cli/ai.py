"""The `ai` subgroup: config, review, cover, suggest, align."""

from __future__ import annotations

from pathlib import Path

import click
from rich.markup import escape

from cvloom.cli.group import cli
from cvloom.cli.shared import (
    _console,
    _resolve,
    _root,
    _warn_if_not_a_job_posting,
)


def _cited(rule_ids: list[str]) -> str:
    """Render a rule-id citation as provenance, not content."""
    return f"  [dim](addresses {', '.join(rule_ids)})[/dim]" if rule_ids else ""


_BAND_COLOUR = {"strong": "green", "adequate": "yellow", "needs work": "red"}


def _band(band: str) -> str:
    """Colour an assessment band, leaving an unrecognised one legible.

    The AI layer keeps an off-rubric label rather than coercing it, so this has to
    render one. It falls through to no colour instead of guessing a severity: a
    model that answered outside the rubric is a thing the user should be able to
    see, not something to normalise away at the last step.
    """
    colour = _BAND_COLOUR.get(band)
    return f"[{colour}]{band}[/{colour}]" if colour else band or "unrated"


def _notes_block(text: str) -> str:
    """Render *text* as a pasteable ``job_context.notes`` YAML block.

    Hand-formatted rather than ``yaml.dump``: PyYAML needs a custom representer to
    emit a ``|`` literal block, and would still requote and reflow the rest. What
    the user wants is the exact fragment to paste into a file cvloom deliberately
    does not rewrite — every writer in this repo replaces a whole file and drops
    comments, which a hand-maintained profile cannot survive.

    Trailing whitespace is stripped per line: it survives a literal block and shows
    up as invisible drift in the next diff of the user's profile.
    """
    body = "\n".join(f"    {line}".rstrip() for line in text.strip().splitlines())
    return f"job_context:\n  notes: |\n{body}"


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

    _console.print()
    _emit_context_notes(result.context_notes)
    _console.print(f"[bold]CV Review[/bold]  profile: {profile}")
    _console.print(f"Overall: {_band(result.overall_band)} [dim](weakest section)[/dim]\n")

    for sec in result.sections:
        _console.print(f"[bold]{sec.section}[/bold]  {_band(sec.band)}")
        for s in sec.strengths:
            _console.print(f"  [green]+[/green] {s}")
        for w in sec.weaknesses:
            _console.print(f"  [red]–[/red] {w}")
        for sg in sec.suggestions:
            _console.print(f"  [dim]→[/dim] {sg}")
        if sec.related_findings:
            _console.print(_cited(sec.related_findings))
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
@click.option(
    "--body-only",
    is_flag=True,
    default=False,
    help="Write body paragraphs only, as a pasteable job_context.notes block.",
)
def ai_cover(profile: str, jd_file: str, output: str | None, body_only: bool) -> None:
    """Generate a tailored cover letter from your CV and a job description.

    With --body-only the model writes the letter's argument and nothing else, and
    the output is a job_context.notes block to paste into the profile. A
    cover-letter/* template then renders the greeting, closing and signature from
    the locale pack, so the finished letter has exactly one of each. cvloom does
    not edit the profile itself: it has no comment-preserving YAML writer, and a
    hand-maintained profile would lose its comments and key order to one.
    """
    from cvloom.ai import AINotConfiguredError, get_client, get_model, is_configured
    from cvloom.ai.cover import generate_cover

    root = _root()
    if not is_configured(root):
        _console.print("[yellow]AI provider not configured.[/yellow] Run: cvloom ai config")
        raise SystemExit(1)

    jd_text = Path(jd_file).read_text(encoding="utf-8")
    resolved = _resolve(root, profile, public=True)
    _warn_if_not_a_job_posting(jd_text, jd_file, resolved.locale.code)
    try:
        client = get_client(root)
        result = generate_cover(resolved, jd_text, client, get_model(root), body_only=body_only)
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    payload = _notes_block(result.letter) if body_only else result.letter

    _console.print()
    _emit_context_notes(result.context_notes)
    if body_only and (resolved.profile.get("job_context") or {}).get("notes"):
        _console.print(
            f"[yellow]Warning:[/yellow] {profile} already has job_context.notes — "
            "pasting this replaces it.\n"
        )

    if output:
        Path(output).write_text(payload, encoding="utf-8")
        _console.print(
            f"[green]✓[/green] Cover letter written to {output}  ({result.word_count} words)"
        )
    else:
        _console.print(f"[bold]Cover Letter[/bold]  profile: {profile}\n")
        # Escaped: the letter is model output, and rich reads a bracketed run like
        # [placeholder] as a style tag and prints nothing where it stood.
        _console.print(escape(payload))
        _console.print(f"\n[dim]{result.word_count} words[/dim]")

    if body_only:
        _console.print(f"[dim]Paste the block above into profiles/{profile}.yaml[/dim]")
    if result.key_alignments:
        _console.print("\n[bold]Key alignments:[/bold]")
        for a in result.key_alignments:
            _console.print(f"  • {escape(a)}")


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
    _console.print()
    _emit_context_notes(result.context_notes)
    _console.print(f"[bold]Improvement Suggestions[/bold]  profile: {profile}{role_label}\n")

    if result.summary:
        _console.print(result.summary)
        _console.print()

    _TYPE_COLOUR = {"bullet": "cyan", "skill": "green", "reword": "yellow", "remove": "red"}

    for s in result.suggestions:
        colour = _TYPE_COLOUR.get(s.type, "white")
        # The type is escaped because rich reads a bare `[bullet]` as a style tag
        # and renders it as nothing — the badge this line exists to print was
        # invisible for every suggestion cvloom has ever shown.
        badge = f"[{colour}]{escape(f'[{s.type}]')}[/{colour}]"
        context = s.section + (f" / {s.entry}" if s.entry else "")
        _console.print(f"  {badge} [dim]{context}[/dim]{_cited(s.related_findings)}")
        if s.current:
            _console.print(f"    [dim]before:[/dim] {escape(s.current)}")
        if s.suggested:
            _console.print(f"    [green]{escape(s.suggested)}[/green]")
        _console.print(f"    [dim]{escape(s.rationale)}[/dim]")
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
    _warn_if_not_a_job_posting(jd_text, jd_file, resolved.locale.code)
    try:
        client = get_client(root)
        result = align(resolved, jd_text, client, get_model(root))
    except AINotConfiguredError as exc:
        _console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        _console.print(f"[red]AI error:[/red] {exc}")
        raise SystemExit(1)

    _console.print()
    _emit_context_notes(result.context_notes)
    _console.print(f"[bold]JD Alignment[/bold]  profile: {profile}\n")
    _console.print(f"[bold]Alignment:[/bold] {_band(result.alignment_band)}")
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


def _emit_context_notes(notes: list[str]) -> None:
    """Report what the AI layer had to leave out of the model's context.

    Not gated on ``--verbose``: the whole point is to surface the trade when it
    bites, and a note only exists when something was actually given up. This
    cannot go through ``_emit_warnings``, which runs inside ``_resolve`` — before
    the AI call that produces these.
    """
    for note in notes:
        _console.print(f"[dim]note: {note}[/dim]")
    if notes:
        _console.print()
