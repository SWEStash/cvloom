"""cvloom CLI entry point.

The commands live in one module per group rather than one module for all of them.
Importing them here is what registers them: each does ``@cli.command()`` against
the group in :mod:`cvloom.cli.group`, so a module nobody imports contributes no
command. The import order below is therefore load-bearing, not stylistic.

Nothing in the package imports this module — commands reach the group through
``cvloom.cli.group`` and the shared helpers through ``cvloom.cli.shared`` — which
is what keeps the package acyclic while still letting ``cvloom.cli:cli`` be the
single entry point ``pyproject.toml`` names.
"""

from __future__ import annotations

# Registration side effects. Ordered as the commands are grouped, not
# alphabetically; `noqa: F401` because the import *is* the registration.
from cvloom.cli import (
    ai,  # noqa: F401
    analyse,  # noqa: F401
    build,  # noqa: F401
    data,  # noqa: F401
    listing,  # noqa: F401
)
from cvloom.cli.ai import _notes_block
from cvloom.cli.build import _write_extracted_text
from cvloom.cli.group import _friendly, cli
from cvloom.cli.shared import (
    _MAX_PAGES,
    _emit_warnings,
    _render_resolve_error,
    _resolve,
    _root,
    _section_summary,
    _warn_template_parse_risk,
)

__all__ = [
    "cli",
    # Re-exported because the test suite imports them from `cvloom.cli` directly.
    # They moved modules; the name they are imported by did not.
    "_MAX_PAGES",
    "_emit_warnings",
    "_friendly",
    "_notes_block",
    "_render_resolve_error",
    "_resolve",
    "_root",
    "_section_summary",
    "_warn_template_parse_risk",
    "_write_extracted_text",
]
