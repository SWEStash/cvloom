"""The rubrics, checked against outputs written by hand to pass or fail each one.

These run everywhere, with no backend. The evaluation suite that applies them to a
live model is opt-in and skipped in CI, so without this file the checks deciding
whether a model passed would themselves be the least-tested code in the repo — and
a rubric that silently always passes is worse than no rubric, because it reports a
clean run.
"""

from __future__ import annotations

from tests.ai_rubrics import (
    answers_in,
    cites_a_real_rule,
    invents_no_numbers,
    language_of,
    leaks_no_analysis_labels,
    reports_unusable_input,
    restates_verbatim,
)
from tests.conftest import make_resolved

_EN = "The work section is clear and the achievements are specific, with metrics for most of it."
_ES = (
    "La sección de experiencia es clara y los logros son específicos, con métricas para casi todo."
)


# ── language ────────────────────────────────────────────────────────


def test_language_is_detected_in_both_directions() -> None:
    assert language_of(_EN) == "en"
    assert language_of(_ES) == "es"


def test_a_mismatch_is_reported_with_both_languages_named() -> None:
    assert answers_in(_ES, "en") == "answered in es, expected en"
    assert answers_in(_EN, "es") == "answered in en, expected es"


def test_a_match_passes() -> None:
    assert answers_in(_EN, "en") is None
    assert answers_in(_ES, "es") is None


def test_a_string_too_short_to_judge_is_not_a_failure() -> None:
    """Asserting on a guess would turn the pass rate into noise."""
    assert language_of("Add a metric.") is None
    assert answers_in("Add a metric.", "es") is None


def test_a_technical_string_with_no_function_words_is_not_judged() -> None:
    assert language_of("Python Go SQL Kubernetes Terraform PostgreSQL Redis Kafka") is None


# ── grounding ───────────────────────────────────────────────────────


def test_an_invented_figure_is_named() -> None:
    result = invents_no_numbers("Cut latency by 40%", "Cut latency across the fleet")
    assert result is not None and "40" in result


def test_a_figure_from_the_cv_passes() -> None:
    assert invents_no_numbers("Cut latency by 40%", "Reduced p99 latency by 40%") is None


# ── citation ────────────────────────────────────────────────────────


_ANALYSIS = "<analysis>\nwl-002 [writing/warning] x3 — fix: add a metric\n</analysis>"


def test_a_real_citation_passes() -> None:
    assert cites_a_real_rule([["wl-002"], []], _ANALYSIS) is None


def test_citing_nothing_anywhere_fails() -> None:
    assert cites_a_real_rule([[], []], _ANALYSIS) == "cited no rule ids at all"


def test_an_entirely_invented_citation_fails() -> None:
    result = cites_a_real_rule([["wl-999"]], _ANALYSIS)
    assert result is not None and "wl-999" in result


def test_one_real_citation_carries_an_invented_one() -> None:
    """Per-item citation is optional by design, so the rubric asks only that the
    block was read at all."""
    assert cites_a_real_rule([["wl-002"], ["wl-999"]], _ANALYSIS) is None


# ── analysis-block bleed ────────────────────────────────────────────


def _resolved() -> object:
    return make_resolved(
        work=[{"company": "Acme Corp", "title": "Engineer", "highlights": ["Shipped things."]}],
        show={"work": True},
        section_order=["work"],
    )


def test_a_leaked_label_is_caught() -> None:
    letter = "I am writing to apply. At [work/Acme Corp] I owned the pipeline."
    result = leaks_no_analysis_labels(letter, _resolved())  # type: ignore[arg-type]
    assert result is not None and "work/Acme Corp" in result


def test_a_leaked_label_is_caught_through_spacing() -> None:
    """The block renders `work / Acme Corp`; a model may echo either spacing."""
    letter = "At work / Acme Corp I owned the deployment pipeline."
    assert leaks_no_analysis_labels(letter, _resolved()) is not None  # type: ignore[arg-type]


def test_naming_the_employer_normally_is_not_a_leak() -> None:
    letter = "At Acme Corp I owned the deployment pipeline end to end."
    assert leaks_no_analysis_labels(letter, _resolved()) is None  # type: ignore[arg-type]


# ── unusable input ──────────────────────────────────────────────────


def test_saying_so_and_returning_nothing_passes() -> None:
    assert reports_unusable_input("The CV is empty; there is nothing to assess.", []) is None


def test_analysing_an_empty_input_fails() -> None:
    result = reports_unusable_input("Strong CV.", ["a suggestion"])
    assert result is not None and "1 item(s)" in result


def test_naming_the_problem_does_not_excuse_returning_items() -> None:
    """Half-compliance is still a contract failure; the echoed sample is what
    lets a reader tell it apart from silent confabulation."""
    result = reports_unusable_input("The CV is nearly empty.", ["a section"])
    assert result is not None


def test_silence_is_not_the_same_as_reporting_it() -> None:
    assert reports_unusable_input("   ", []) is not None


# ── restatement (measured, not gated) ───────────────────────────────


def test_a_verbatim_restatement_is_detected_through_whitespace_and_case() -> None:
    result = restates_verbatim(
        ["no  Quantified outcome in this entry"], ["No quantified outcome in this entry."]
    )
    assert result is not None and "1 finding" in result


def test_independent_wording_is_not_a_restatement() -> None:
    assert restates_verbatim(["Lead with the fleet migration"], ["No quantified outcome."]) is None
