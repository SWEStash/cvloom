"""Read the text layer back out of a built PDF.

This is the only honest way to check what an ATS will see. A CV can render
perfectly and still extract wrong: a right-aligned date reads as its own text
column, and poppler flushes a column when the *page* ends rather than when the
entry does, so the last entry on each page had its date emitted after its own
bullets and fused to the next entry's title. Nothing about the rendered page
shows that. Selecting the text does.

Engines disagree, which is the point of supporting more than one:

- ``poppler`` (the ``pdftotext`` binary) rebuilds columns from glyph geometry.
  It is what most Linux PDF viewers use for copy/paste and what a great many
  ingestion pipelines shell out to, and it is the strictest of the three about
  column layout — the defects above showed up here and nowhere else.
- ``pypdf`` walks the content stream in paint order. Pure Python, common in
  Python document pipelines.
- ``pdfminer`` re-lays out characters itself. Pure Python, and the engine behind
  a lot of Python resume tooling.

None of them *is* any particular ATS. Agreement across engines that read the
document by different means is evidence the text layer is unambiguous; it is not
a certificate.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

POPPLER = "poppler"
PYPDF = "pypdf"
PDFMINER = "pdfminer"

# Preferred first: poppler is the strictest and the most widely deployed.
ENGINES: tuple[str, ...] = (POPPLER, PYPDF, PDFMINER)


@dataclass(frozen=True)
class Extraction:
    """Text pulled from a PDF by one engine."""

    engine: str
    text: str


class EngineUnavailable(RuntimeError):
    """Raised when the requested engine is not installed."""


def available_engines() -> list[str]:
    """Return the engines usable in this environment, preferred first."""
    found = []
    if shutil.which("pdftotext"):
        found.append(POPPLER)
    for name, module in ((PYPDF, "pypdf"), (PDFMINER, "pdfminer.high_level")):
        try:
            __import__(module)
        except ImportError:
            continue
        found.append(name)
    return found


def _poppler(pdf: Path) -> str:
    # -layout preserves the visual arrangement, which is exactly what we do NOT
    # want: the question is what a reader gets from the default reading order.
    proc = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {proc.stderr.strip()}")
    return proc.stdout


def _pypdf(pdf: Path) -> str:
    import pypdf

    return "\n".join(page.extract_text() for page in pypdf.PdfReader(str(pdf)).pages)


def _pdfminer(pdf: Path) -> str:
    from pdfminer.high_level import extract_text

    return str(extract_text(str(pdf)))


_READERS = {POPPLER: _poppler, PYPDF: _pypdf, PDFMINER: _pdfminer}


def extract(pdf: Path, engine: str) -> Extraction:
    """Extract *pdf*'s text layer with *engine*."""
    if engine not in _READERS:
        raise ValueError(f"Unknown engine {engine!r}; expected one of {', '.join(ENGINES)}")
    if engine not in available_engines():
        raise EngineUnavailable(engine)
    return Extraction(engine=engine, text=_READERS[engine](pdf))


def extract_all(pdf: Path, engines: list[str] | None = None) -> list[Extraction]:
    """Extract with every requested engine that is installed.

    Silently skipping a missing engine would be the wrong default here — a report
    that says "clean" because only one engine ran is the failure mode this module
    exists to prevent — so the caller gets the list of what actually ran and is
    expected to say so.
    """
    wanted = engines or available_engines()
    return [extract(pdf, e) for e in wanted if e in available_engines()]
