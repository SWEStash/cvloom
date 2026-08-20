"""The root Click group and the exception-to-message translation around it."""

from __future__ import annotations

import traceback
from typing import Any

import click
import yaml

from cvloom import (
    builder,
)
from cvloom.cli.shared import (
    _err,
)


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
