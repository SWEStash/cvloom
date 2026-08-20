"""Tests for the PDF text-layer readers behind `build --extract-text`.

`test_extraction_fidelity.py` drives these engines over real cvloom-built PDFs and
asserts what comes back out. This file covers the parts that a well-formed cvloom
PDF cannot reach: engine dispatch, the availability gate, and the marked-content
bookkeeping that only a hand-built PDF can provoke.

The PDFs here are written byte by byte rather than built by cvloom, because the
cases worth testing are the ones cvloom's own templates do not currently produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cvloom import extract


def _pdf(objects: list[str], root: int) -> bytes:
    """Assemble numbered PDF objects into a minimal single-file PDF.

    Written out rather than pulled from a fixture library so each test can state
    the exact content stream it needs; the offsets and xref table are the only
    parts that have to be mechanical.
    """
    out = bytearray(b"%PDF-1.7\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    trailer = f"<< /Size {len(objects) + 1} /Root {root} 0 R >>"
    out += f"trailer\n{trailer}\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _stream(content: str) -> str:
    return f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"


def _tagged_pdf(content: str, mcids: list[int]) -> bytes:
    """A one-page tagged PDF whose structure tree names *mcids* in order."""
    kids = " ".join(f"<< /Type /StructElem /S /P /Pg 4 0 R /K {m} >>" for m in mcids)
    return _pdf(
        [
            "<< /Type /Catalog /Pages 2 0 R /StructTreeRoot 6 0 R >>",
            "<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
            _stream(content),
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 3 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Type /StructTreeRoot /K [{kids}] >>",
        ],
        root=1,
    )


def _write(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "made.pdf"
    path.write_bytes(data)
    return path


# ── engine dispatch ──────────────────────────────────────────────────


def test_unknown_engine_names_the_real_ones(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        extract.extract(tmp_path / "absent.pdf", "tesseract")
    message = str(excinfo.value)
    assert "tesseract" in message
    for engine in extract.ENGINES:
        assert engine in message


def test_an_uninstalled_engine_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`extract` re-checks availability; `extract_all` filters before calling it."""
    monkeypatch.setattr(extract, "available_engines", lambda: [])
    with pytest.raises(extract.EngineUnavailable):
        extract.extract(tmp_path / "absent.pdf", extract.POPPLER)


def test_extract_all_runs_only_installed_engines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extract, "available_engines", lambda: [extract.CONSTRUCTION])
    pdf = _write(tmp_path, _tagged_pdf("BT /F1 12 Tf 10 100 Td (Hello) Tj ET", []))
    assert [e.engine for e in extract.extract_all(pdf)] == [extract.CONSTRUCTION]


def test_an_untagged_pdf_drops_the_structure_engine_only(tmp_path: Path) -> None:
    """A PDF cvloom did not build has no structure tree; the rest still read it."""
    untagged = _pdf(
        [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
            _stream("BT /F1 12 Tf 10 100 Td (Hello) Tj ET"),
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 3 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ],
        root=1,
    )
    pdf = _write(tmp_path, untagged)
    with pytest.raises(extract.UntaggedPDF):
        extract.extract(pdf, extract.STRUCTURE)
    ran = [e.engine for e in extract.extract_all(pdf)]
    assert extract.STRUCTURE not in ran
    assert extract.CONSTRUCTION in ran


# ── marked content ───────────────────────────────────────────────────


def test_artifact_text_stays_out_of_the_structure_reading_order(tmp_path: Path) -> None:
    """An /Artifact carries no MCID, and its glyphs belong to no structure element.

    `/Artifact BMC` is the exact form WeasyPrint emits (15 of them in a built
    three-page CV), so this is the real operator, not a constructed one.

    Page furniture — running headers, rules, page numbers — is marked as an
    artifact precisely so a consumer skips it. Leaving the enclosing MCID in
    place across a nested untagged tag welds that furniture onto the previous
    paragraph, which is the one thing the structure engine exists to avoid.

    cvloom's own templates emit artifacts that hold no text, so this cannot be
    provoked from a built CV today; the PDF is written by hand for that reason.
    """
    # The artifact is *nested inside* the tagged paragraph. Sequentially the two
    # cannot collide — the paragraph's own EMC has already cleared the MCID — so
    # nesting is what the bookkeeping has to survive.
    content = (
        "/P << /MCID 0 >> BDC BT /F1 12 Tf 10 150 Td (Real) Tj ET\n"
        "/Artifact BMC BT /F1 12 Tf 10 100 Td (Furniture) Tj ET EMC\n"
        "EMC\n"
    )
    pdf = _write(tmp_path, _tagged_pdf(content, [0]))

    structured = extract.extract(pdf, extract.STRUCTURE).text
    assert "Real" in structured
    assert "Furniture" not in structured

    # The raw construction order still sees it — that engine reports the page as
    # painted, artifacts included, which is what makes disagreement informative.
    assert "Furniture" in extract.extract(pdf, extract.CONSTRUCTION).text


def test_an_explicit_empty_engine_list_runs_nothing(tmp_path: Path) -> None:
    """`engines=[]` means none, not "unset" — `or` read the two the same way."""
    pdf = _write(tmp_path, _tagged_pdf("BT /F1 12 Tf 10 100 Td (Hello) Tj ET", []))
    assert extract.extract_all(pdf, []) == []
    assert extract.extract_all(pdf) != []
