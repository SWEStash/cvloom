"""What the four AI features actually return, from a real model.

Every other `test_ai_*.py` file feeds an orchestrator a hand-written JSON string
and checks it parses. That is correct and worth keeping, but it means no prompt
change can be shown to have helped or hurt — the whole layer's quality rested on
a handful of invocations someone ran by hand and remembered.

Opt-in, and deselected by default (`addopts` in pyproject). Two gates, so neither
a contributor with a backend exported nor one without a backend gets a surprise:
`-m evals` is required to select these at all, and they skip if no backend is
configured even then.

**What is a gate and what is only measured.** Language, groundedness, citation,
unusable-input handling and cover-letter shape are gates: they are contract
violations, and a model that fails them is not usable for this feature at all.
Restatement is measured and printed, never asserted — the prompt asks the model
not to repeat findings the user already saw, and small models ignore that
reliably enough that gating on it would paint every pre-release run red while
saying nothing about the prompt.

Run: `CVLOOM_AI_BASE_URL=http://localhost:11434/v1 CVLOOM_AI_MODEL=... \
uv run pytest -m evals -s`
"""

from __future__ import annotations

import os

import pytest

from cvloom.ai.align import align
from cvloom.ai.analysis import SCOPE_BRIEF, SCOPE_EVIDENCE, SCOPE_FULL, analysis_context_block
from cvloom.ai.analyzer import review
from cvloom.ai.cover import generate_cover
from cvloom.ai.provider import cv_to_text
from cvloom.ai.suggest import suggest
from cvloom.linter import lint
from tests.ai_corpus import NOT_A_JD, REAL_JD, Case, cases
from tests.ai_rubrics import (
    answers_in,
    cites_a_real_rule,
    invents_no_numbers,
    leaks_no_analysis_labels,
    reports_unusable_input,
    restates_verbatim,
)

pytestmark = [
    pytest.mark.evals,
    pytest.mark.skipif(
        not os.environ.get("CVLOOM_AI_BASE_URL"),
        reason="no AI backend configured (set CVLOOM_AI_BASE_URL)",
    ),
]


@pytest.fixture(scope="session")
def model() -> tuple[object, str]:
    from cvloom.ai import get_client, get_model

    return get_client(), get_model()


def _case(name: str) -> Case:
    return next(case for case in cases() if case.name == name)


def _cv(case: Case) -> str:
    return cv_to_text(case.resolved.data, case.resolved.show_sections, case.resolved.locale)


def _analysis(case: Case, scope: str = SCOPE_FULL) -> str:
    return analysis_context_block(case.resolved, _cv(case), scope=scope).text


def _check(*results: str | None, sample: str = "") -> None:
    """Fail once, naming every gate that failed rather than only the first.

    *sample* is the text that was graded, echoed on failure. Without it a report
    like "answered in en, expected es" cannot be told apart from a rubric
    misfiring on prose too technical to classify, and the run is 40 minutes long
    — far too expensive to repeat just to see what the model actually said.
    """
    failures = [reason for reason in results if reason]
    if failures and sample:
        print(f"\n[graded output]\n{sample[:800]}\n")
    assert not failures, "\n".join(f"  - {reason}" for reason in failures)


def _report(name: str, measured: str | None) -> None:
    print(f"\n[measured] {name}: {measured or 'clean'}")


# ── review ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["examples", "no-metrics", "spanish-no-metrics"])
def test_review_is_grounded_cited_and_in_the_right_language(name: str, model) -> None:  # type: ignore[no-untyped-def]
    client, model_name = model
    case = _case(name)
    result = review(case.resolved, client, model_name)
    prose = " ".join(
        [*result.top_priorities, *(item for sec in result.sections for item in sec.suggestions)]
    )

    _check(
        answers_in(prose, case.resolved.locale.code),
        invents_no_numbers(prose, _cv(case), _analysis(case)),
        cites_a_real_rule([sec.related_findings for sec in result.sections], _analysis(case)),
        leaks_no_analysis_labels(prose, case.resolved),
        sample=prose,
    )
    _report(
        f"review/{name} restatement",
        restates_verbatim(
            [item for sec in result.sections for item in sec.weaknesses],
            [finding.message for finding in lint(case.resolved)],
        ),
    )


@pytest.mark.parametrize("name", ["empty-cv", "one-line"])
def test_review_reports_an_unusable_cv_rather_than_assessing_it(name: str, model) -> None:  # type: ignore[no-untyped-def]
    """The failure the grounding contract exists to prevent: a confident
    assessment of a CV that is not there."""
    client, model_name = model
    case = _case(name)
    result = review(case.resolved, client, model_name)
    # The prompt routes the report into the first item of top_priorities, review
    # having no prose field of its own.
    _check(
        reports_unusable_input(" ".join(result.top_priorities), result.sections),
        sample=" ".join(result.top_priorities),
    )


def test_review_bands_every_section_it_returns(model) -> None:  # type: ignore[no-untyped-def]
    """An unrecognised band is kept rather than coerced, so nothing downstream
    would notice a model ignoring the rubric."""
    client, model_name = model
    case = _case("examples")
    result = review(case.resolved, client, model_name)
    off_rubric = [
        s.section for s in result.sections if s.band not in ("strong", "adequate", "needs work")
    ]
    assert not off_rubric, f"sections banded off-rubric: {off_rubric}"


# ── suggest ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["weak-openers", "no-metrics", "spanish-no-metrics"])
def test_suggest_is_grounded_cited_and_in_the_right_language(name: str, model) -> None:  # type: ignore[no-untyped-def]
    client, model_name = model
    case = _case(name)
    result = suggest(case.resolved, client, model_name)
    prose = " ".join([s.suggested for s in result.suggestions] + [result.summary])

    _check(
        answers_in(prose, case.resolved.locale.code),
        invents_no_numbers(prose, _cv(case), _analysis(case)),
        cites_a_real_rule([s.related_findings for s in result.suggestions], _analysis(case)),
        leaks_no_analysis_labels(prose, case.resolved),
        sample=prose,
    )
    _report(
        f"suggest/{name} restatement",
        restates_verbatim(
            [s.rationale for s in result.suggestions],
            [finding.message for finding in lint(case.resolved)],
        ),
    )


def test_suggest_does_not_rewrite_one_flagged_opener_into_another(model) -> None:  # type: ignore[no-untyped-def]
    """The reason the analysis block carries the whole wl-004 set.

    Told only that *this* opener is weak, a model rewrites `was responsible for`
    into `participated in` and the finding fires again on the bullet it just
    fixed. This is the rubric that measures whether sending the set works.
    """
    from cvloom import linter_locales

    client, model_name = model
    case = _case("weak-openers")
    result = suggest(case.resolved, client, model_name)
    openers = linter_locales.pack_for(case.resolved.locale.code).weak_openers

    relanded = [
        s.suggested
        for s in result.suggestions
        if s.suggested and s.suggested.lower().lstrip("- ").startswith(tuple(openers))
    ]
    assert not relanded, "rewrote a flagged opener into another flagged opener:\n" + "\n".join(
        f"  - {text}" for text in relanded
    )


# ── cover ───────────────────────────────────────────────────────────


def test_cover_is_grounded_and_leaks_no_analysis_labels(model) -> None:  # type: ignore[no-untyped-def]
    """A live run once emitted `[work/Acme Corp]` into the prose as though it were
    a placeholder to fill in. Nothing else catches that."""
    client, model_name = model
    case = _case("examples")
    result = generate_cover(case.resolved, REAL_JD, client, model_name)

    _check(
        answers_in(result.letter, case.resolved.locale.code),
        invents_no_numbers(result.letter, _cv(case), REAL_JD, _analysis(case, SCOPE_EVIDENCE)),
        leaks_no_analysis_labels(result.letter, case.resolved),
        sample=result.letter,
    )
    assert result.word_count <= 400, f"cover letter ran to {result.word_count} words"


def test_body_only_omits_greeting_closing_and_heading(model) -> None:  # type: ignore[no-untyped-def]
    """`--body-only` output is pasted into a template that supplies its own
    furniture, so a greeting here is duplicated in the rendered letter."""
    client, model_name = model
    case = _case("examples")
    result = generate_cover(case.resolved, REAL_JD, client, model_name, body_only=True)

    lowered = result.letter.lower()
    furniture = [
        token
        for token in ("dear ", "sincerely", "yours faithfully", "kind regards", "best regards")
        if token in lowered
    ]
    assert not furniture, f"body-only output carries letter furniture: {furniture}"
    assert not result.letter.lstrip().startswith("#"), "body-only output carries a heading"
    assert result.body_only


def test_cover_refuses_a_job_description_that_is_not_one(model) -> None:  # type: ignore[no-untyped-def]
    client, model_name = model
    case = _case("examples")
    result = generate_cover(case.resolved, NOT_A_JD, client, model_name)
    _check(
        reports_unusable_input(result.letter, list(result.key_alignments)),
        sample=result.letter,
    )


# ── align ───────────────────────────────────────────────────────────


def test_align_is_grounded_and_bands_the_fit(model) -> None:  # type: ignore[no-untyped-def]
    client, model_name = model
    case = _case("examples")
    result = align(case.resolved, REAL_JD, client, model_name)

    _check(
        answers_in(result.narrative, case.resolved.locale.code),
        invents_no_numbers(
            " ".join([result.narrative, *result.repositioning]),
            _cv(case),
            REAL_JD,
            _analysis(case, SCOPE_BRIEF),
        ),
        leaks_no_analysis_labels(result.narrative, case.resolved),
        sample=result.narrative,
    )
    assert result.alignment_band in ("strong", "adequate", "needs work"), (
        f"off-rubric band: {result.alignment_band!r}"
    )


def test_align_reports_a_job_description_that_is_not_one(model) -> None:  # type: ignore[no-untyped-def]
    client, model_name = model
    case = _case("jd-is-a-privacy-policy")
    result = align(case.resolved, NOT_A_JD, client, model_name)
    _check(
        reports_unusable_input(result.narrative, list(result.repositioning)),
        sample=result.narrative,
    )


# ── the analysis block reaches the model at all ─────────────────────


def test_the_worst_case_cv_still_fits_its_budget() -> None:
    """No model call — a cheap guard that runs alongside the rest, since a block
    that blew its budget would push the grounding contract out of the request
    before it pushed anything else.

    Only `SCOPE_FULL` is bounded. The narrow scopes render no per-finding detail
    at all, so they have nothing to shed and their header may legitimately exceed
    `budget_chars` — asserting otherwise tests the fixture, not the budget.
    """
    case = _case("four-pages")
    full = analysis_context_block(case.resolved, _cv(case), scope=SCOPE_FULL)
    assert len(full.text) <= full.budget_chars

    # Not asserted: that anything was shed. 139 findings fit at `grouped`,
    # because the per-rule instance cap ("... and 61 more of wl-013") is the
    # normal rendering rather than a concession, and deliberately produces no
    # note. A healthy run shows the user no notice at all.
    assert full.findings_total == 139, "the fixture stopped being the worst case"

    for scope in (SCOPE_BRIEF, SCOPE_EVIDENCE):
        block = analysis_context_block(case.resolved, _cv(case), scope=scope)
        assert block.findings_total == full.findings_total, scope
