"""Tests for the text-layer recall report behind `build --extract-text`.

The extraction itself is covered by `test_extraction_fidelity.py`, which builds
real PDFs. What is tested here is the arithmetic on top: which of two very
different failures a missing word is attributed to, and what each engine's
denominator is once that attribution is made.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cvloom import extract as extract_mod
from cvloom import fidelity
from cvloom.models import ResolvedProfile
from tests.conftest import make_resolved


def _resolved(**data: Any) -> ResolvedProfile:
    """A CV whose only prose is what the test puts in it.

    `make_resolved` seeds a headline and summary, and those tokens would show up
    in every denominator here and make the arithmetic hard to read.
    """
    return make_resolved(basics={}, contact={}, **data)


def _fake_extractions(monkeypatch: pytest.MonkeyPatch, texts: dict[str, str]) -> None:
    """Stand in for the real engines so attribution can be driven directly."""

    def fake(pdf_path: Path, engines: list[str] | None = None) -> list[extract_mod.Extraction]:
        return [extract_mod.Extraction(engine=e, text=t) for e, t in texts.items()]

    monkeypatch.setattr(extract_mod, "extract_all", fake)


def test_source_tokens_are_deduplicated() -> None:
    """Recall asks whether a word arrived, not how often.

    Counted with repeats, a term appearing in ten bullets would bank ten
    successes and bury a rarer term that failed.
    """
    resolved = _resolved(
        work=[{"company": "Acme", "title": "Acme Engineer", "highlights": ["Acme again"]}]
    )
    assert fidelity.source_tokens(resolved).count("acme") == 1


def test_single_character_tokens_are_dropped() -> None:
    """`a` turns up inside almost any extraction by accident."""
    resolved = _resolved(work=[{"company": "A B Corporation"}])
    tokens = fidelity.source_tokens(resolved)
    assert "corporation" in tokens
    assert "a" not in tokens and "b" not in tokens


def test_a_word_no_engine_found_is_blamed_on_the_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """All five engines missing the same word means it is not on the page.

    `cv/sidebar-compact` renders no education detail, and scoring that against
    the extractors marks five of them down for a word none was ever shown.
    """
    resolved = _resolved(work=[{"company": "Acme", "title": "Engineer", "location": "Berlin"}])
    _fake_extractions(monkeypatch, {"poppler": "acme engineer", "pypdf": "acme engineer"})

    report = fidelity.recall(resolved, tmp_path / "x.pdf")

    assert report.unrendered == ("berlin",)
    assert all(r.missing == () for r in report.engines)
    assert all(r.percentage == 100.0 for r in report.engines)


def test_an_unrendered_word_leaves_every_engine_denominator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The template's omission must not be charged to the extractors."""
    resolved = _resolved(work=[{"company": "Acme", "title": "Engineer", "location": "Berlin"}])
    _fake_extractions(monkeypatch, {"poppler": "acme engineer", "pypdf": "acme engineer"})

    report = fidelity.recall(resolved, tmp_path / "x.pdf")

    assert report.source_total == 3
    assert all(r.total == 2 for r in report.engines)


def test_a_word_one_engine_missed_is_an_extraction_loss(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Disagreement between engines is the signal the text layer is ambiguous."""
    resolved = _resolved(work=[{"company": "Acme", "title": "Engineer", "location": "Berlin"}])
    _fake_extractions(
        monkeypatch,
        {"poppler": "acme engineer berlin", "pypdf": "acme engineer"},
    )

    report = fidelity.recall(resolved, tmp_path / "x.pdf")
    by_engine = {r.engine: r for r in report.engines}

    assert report.unrendered == ()
    assert by_engine["poppler"].missing == ()
    assert by_engine["pypdf"].missing == ("berlin",)
    assert by_engine["pypdf"].found == 2


def test_matching_ignores_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Most templates uppercase headings; that is styling, not a lost word."""
    resolved = _resolved(work=[{"company": "Acme", "title": "Engineer"}])
    _fake_extractions(monkeypatch, {"poppler": "ACME ENGINEER"})

    report = fidelity.recall(resolved, tmp_path / "x.pdf")

    assert report.unrendered == ()
    assert report.engines[0].percentage == 100.0


def test_no_installed_engine_yields_an_empty_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nothing to divide by, and nothing to blame the template for either."""
    resolved = _resolved(work=[{"company": "Acme"}])
    _fake_extractions(monkeypatch, {})

    report = fidelity.recall(resolved, tmp_path / "x.pdf")

    assert report.engines == ()
    assert report.unrendered == ()
    assert report.source_total == 1


# ── attribution needs corroboration ──────────────────────────────────


def test_a_single_engine_attributes_nothing_to_the_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One engine cannot tell "never rendered" from "this engine lost it".

    Agreement is what separates the two failures, and one engine agrees with
    nobody. Attributing its misses to the template empties the denominator of
    exactly the tokens it just failed on, so the engine scores 100% *because*
    it did badly — worst on a bare install, where poppler is the only engine.
    """
    resolved = _resolved(work=[{"company": "Alpha", "highlights": ["Beta gamma."]}])
    _fake_extractions(monkeypatch, {"poppler": "Alpha"})
    report = fidelity.recall(resolved, tmp_path / "cv.pdf")

    assert report.attribution_available is False
    assert report.unrendered == ()
    (only,) = report.engines
    assert set(only.missing) == {"beta", "gamma"}
    assert only.percentage < 100.0


def test_two_engines_agreeing_still_blame_the_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The corroborated case is unchanged: two engines agreeing is evidence."""
    resolved = _resolved(work=[{"company": "Alpha", "highlights": ["Beta gamma."]}])
    _fake_extractions(monkeypatch, {"poppler": "Alpha beta", "pypdf": "Alpha beta"})
    report = fidelity.recall(resolved, tmp_path / "cv.pdf")

    assert report.attribution_available is True
    assert report.unrendered == ("gamma",)
    for engine in report.engines:
        assert engine.missing == ()
        assert engine.percentage == 100.0


def test_a_short_token_needs_a_word_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`ai` inside `domain` is a coincidence, not evidence the token survived.

    Short tokens are where a substring test stops discriminating, and they are
    disproportionately the ones that matter — `ai`, `ml`, `aws`, `js`, `sql` are
    skill names. On a real CV, 28 of 60 short tokens occur inside some longer
    token, so their recall could not fail.
    """
    resolved = _resolved(skills=[{"category": "Stack", "items": ["AI", "Rust"]}])
    _fake_extractions(monkeypatch, {"poppler": "Stack domain Rust", "pypdf": "Stack domain Rust"})
    report = fidelity.recall(resolved, tmp_path / "cv.pdf")

    # No engine found `ai` as a word, so it is the template's omission, not theirs.
    assert "ai" in report.unrendered


def test_a_long_token_still_matches_inside_a_welded_word(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Words welded to a neighbour are `extract`'s problem, not a recall failure."""
    resolved = _resolved(skills=[{"category": "Stack", "items": ["Engineer"]}])
    _fake_extractions(
        monkeypatch, {"poppler": "Stack SeniorEngineerLead", "pypdf": "Stack Engineer"}
    )
    report = fidelity.recall(resolved, tmp_path / "cv.pdf")

    assert report.unrendered == ()
    for engine in report.engines:
        assert engine.missing == ()
