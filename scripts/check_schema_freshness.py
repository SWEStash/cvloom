#!/usr/bin/env python
"""Report whether the vendored JSON Resume schema has drifted from upstream.

`tests/test_export_jsonresume_conformance.py` validates cvloom's export against a
copy of the JSON Resume schema vendored at `tests/fixtures/jsonresume-schema.json`,
so the suite stays hermetic. Nothing notices when upstream moves, and a schema that
silently ages turns the conformance suite into a test of last year's spec.

The vendored copy carries two deliberate annotation-only edits (`examples` blocks
removed, one `description` neutralised, because upstream embeds a third party's real
email address that cvloom's own PII hook rejects). A byte comparison would therefore
report drift on every run and be ignored within a month. This compares the parts that
can change validation instead: both documents are stripped of `examples`, `description`
and `title` before diffing, so only structural change is reported.

Run locally:

    uv run python scripts/check_schema_freshness.py

Compare against a file instead of the network (used by the tests):

    uv run python scripts/check_schema_freshness.py --upstream some-schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

UPSTREAM_URL = "https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json"

_VENDORED = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "jsonresume-schema.json"

# Annotation keywords. JSON Schema gives these no validation role, and the vendored
# copy edits two of them on purpose — see the module docstring.
_ANNOTATIONS = frozenset({"examples", "description", "title", "$comment"})


def structural(node: Any) -> Any:
    """Return *node* with annotation keywords removed, recursively."""
    if isinstance(node, dict):
        return {k: structural(v) for k, v in node.items() if k not in _ANNOTATIONS}
    if isinstance(node, list):
        return [structural(item) for item in node]
    return node


def _paths(node: Any, prefix: str = "") -> set[str]:
    """Flatten *node* to a set of `path=value` strings, for a readable diff."""
    if isinstance(node, dict):
        return {p for k, v in node.items() for p in _paths(v, f"{prefix}.{k}")}
    if isinstance(node, list):
        return {p for i, v in enumerate(node) for p in _paths(v, f"{prefix}[{i}]")}
    return {f"{prefix}={node!r}"}


def compare(vendored: Any, upstream: Any) -> list[str]:
    """Return human-readable drift lines; empty means the two agree structurally."""
    ours, theirs = _paths(structural(vendored)), _paths(structural(upstream))
    return [f"- upstream only: {p}" for p in sorted(theirs - ours)] + [
        f"- vendored only: {p}" for p in sorted(ours - theirs)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        type=Path,
        help="read upstream from this file instead of fetching UPSTREAM_URL",
    )
    parser.add_argument("--vendored", type=Path, default=_VENDORED)
    args = parser.parse_args()

    vendored = json.loads(args.vendored.read_text())
    if args.upstream:
        upstream = json.loads(args.upstream.read_text())
    else:
        with urllib.request.urlopen(UPSTREAM_URL, timeout=30) as response:
            upstream = json.loads(response.read())

    drift = compare(vendored, upstream)
    if not drift:
        print(f"{args.vendored.name} is structurally current with upstream.")
        return 0

    print(f"{args.vendored.name} has drifted from upstream ({len(drift)} differences):")
    print("\n".join(drift))
    print(
        "\nRefresh it from:\n"
        f"  {UPSTREAM_URL}\n"
        "then re-apply the two annotation-only edits described in "
        "tests/test_export_jsonresume_conformance.py's module docstring."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
