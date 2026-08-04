"""Read the text layer back out of a built PDF.

A PDF carries several independent reading orders, and an extractor picks one. The
engines here are chosen to cover that spread rather than to agree. None of them is
any particular ATS. See ``docs/dev/architecture.md``.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

POPPLER = "poppler"
PYPDF = "pypdf"
PDFMINER = "pdfminer"
CONSTRUCTION = "construction"
STRUCTURE = "structure"

# Worst-case reader first, standards-defined reader last.
ENGINES: tuple[str, ...] = (CONSTRUCTION, POPPLER, PYPDF, PDFMINER, STRUCTURE)


@dataclass(frozen=True)
class Extraction:
    """Text pulled from a PDF by one engine."""

    engine: str
    text: str


class EngineUnavailable(RuntimeError):
    """Raised when the requested engine is not installed."""


class UntaggedPDF(RuntimeError):
    """Raised when a structure-order read is asked of a PDF with no structure tree."""


def _has_module(module: str) -> bool:
    try:
        __import__(module)
    except ImportError:
        return False
    return True


def available_engines() -> list[str]:
    """Return the engines usable in this environment, in ``ENGINES`` order."""
    pdfminer_ok = _has_module("pdfminer.high_level")
    pypdf_ok = _has_module("pypdf")
    usable = {
        POPPLER: bool(shutil.which("pdftotext")),
        PYPDF: pypdf_ok,
        PDFMINER: pdfminer_ok,
        CONSTRUCTION: pdfminer_ok,
        STRUCTURE: pdfminer_ok and pypdf_ok,
    }
    return [e for e in ENGINES if usable[e]]


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


def _collect(pdf: Path) -> tuple[str, dict[int, dict[int, str]]]:
    """Return construction-order text and, per page, the text of each MCID.

    One pdfminer pass serves both: the characters arrive in content-stream order,
    and each is attributed to the marked-content sequence that was open when it
    was painted.
    """
    from pdfminer.converter import PDFLayoutAnalyzer
    from pdfminer.layout import LTChar
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
    from pdfminer.pdfpage import PDFPage

    class Collector(PDFLayoutAnalyzer):
        def __init__(self, rsrcmgr: PDFResourceManager) -> None:
            super().__init__(rsrcmgr)
            self.page_index = -1
            self.painted: list[str] = []
            self.by_mcid: dict[int, dict[int, str]] = {}
            self._mcid: int | None = None
            self._mcid_stack: list[int | None] = []
            self._baseline: float | None = None

        def begin_tag(self, tag: Any, props: Any = None) -> None:
            self._mcid_stack.append(self._mcid)
            mcid = props.get("MCID") if isinstance(props, dict) else None
            if isinstance(mcid, int):
                self._mcid = mcid

        def end_tag(self) -> None:
            self._mcid = self._mcid_stack.pop() if self._mcid_stack else None

        def render_char(self, *args: Any, **kwargs: Any) -> float:
            adv = super().render_char(*args, **kwargs)
            # `_objs` is pdfminer's own child list; reading its tail is the only
            # way to reach the LTChar that super() just created.
            objs = self.cur_item._objs
            char = objs[-1] if objs else None
            if isinstance(char, LTChar):
                text = char.get_text()
                # A change of baseline is a line break. Without one every glyph on
                # the page concatenates and words weld across lines.
                baseline = round(char.y0, 1)
                if self._baseline is not None and baseline != self._baseline:
                    self.painted.append("\n")
                self._baseline = baseline
                self.painted.append(text)
                if self._mcid is not None:
                    page = self.by_mcid.setdefault(self.page_index, {})
                    page[self._mcid] = page.get(self._mcid, "") + text
            return float(adv)

    rsrcmgr = PDFResourceManager()
    device = Collector(rsrcmgr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    with pdf.open("rb") as fh:
        for i, page in enumerate(PDFPage.get_pages(fh)):
            device.page_index = i
            device._baseline = None
            interpreter.process_page(page)
    return "".join(device.painted), device.by_mcid


def _structure_order(pdf: Path) -> list[tuple[int, int]]:
    """Return ``(page_index, mcid)`` pairs in structure-tree order."""
    import pypdf
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NumberObject

    reader = pypdf.PdfReader(str(pdf))
    root = cast(DictionaryObject, reader.trailer["/Root"])
    if "/StructTreeRoot" not in root:
        raise UntaggedPDF(str(pdf))
    pages = {
        page.indirect_reference.idnum: i
        for i, page in enumerate(reader.pages)
        if page.indirect_reference is not None
    }
    seq: list[tuple[int, int]] = []
    seen: set[int] = set()

    def walk(node: object, page: int | None) -> None:
        if isinstance(node, IndirectObject):
            if node.idnum in seen:
                return
            seen.add(node.idnum)
            node = node.get_object()
        if isinstance(node, (ArrayObject, list)):
            for kid in node:
                walk(kid, page)
        elif isinstance(node, (NumberObject, int)):
            if page is not None:
                seq.append((page, int(node)))
        elif isinstance(node, DictionaryObject):
            pg = node.get("/Pg")
            if isinstance(pg, IndirectObject):
                page = pages.get(pg.idnum, page)
            mcid = node.get("/MCID")
            if mcid is not None and page is not None:
                seq.append((page, int(mcid)))
            kids = node.get("/K")
            if kids is not None:
                walk(kids, page)

    walk(root["/StructTreeRoot"], None)
    return seq


def _construction(pdf: Path) -> str:
    return _collect(pdf)[0]


def _structure(pdf: Path) -> str:
    order = _structure_order(pdf)
    _, by_mcid = _collect(pdf)
    return "\n".join(
        text for page, mcid in order if (text := by_mcid.get(page, {}).get(mcid, "").strip())
    )


_READERS = {
    POPPLER: _poppler,
    PYPDF: _pypdf,
    PDFMINER: _pdfminer,
    CONSTRUCTION: _construction,
    STRUCTURE: _structure,
}


def extract(pdf: Path, engine: str) -> Extraction:
    """Extract *pdf*'s text layer with *engine*."""
    if engine not in _READERS:
        raise ValueError(f"Unknown engine {engine!r}; expected one of {', '.join(ENGINES)}")
    if engine not in available_engines():
        raise EngineUnavailable(engine)
    return Extraction(engine=engine, text=_READERS[engine](pdf))


def extract_all(pdf: Path, engines: list[str] | None = None) -> list[Extraction]:
    """Extract with every requested engine that is installed.

    Returns the list of engines that actually ran, so a caller never reports
    "clean" off a single engine.
    """
    wanted = engines or available_engines()
    out = []
    for engine in wanted:
        if engine not in available_engines():
            continue
        try:
            out.append(extract(pdf, engine))
        except UntaggedPDF:
            # Only the structure engine raises this, and only for a PDF cvloom
            # did not build. Omitting it is reported by the caller.
            continue
    return out
