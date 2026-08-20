"""Partial-date arithmetic — the parser the linter and the tenure suffix share.

``today`` is injected in every span test rather than left to default. A duration
counted to "now" is the one piece of this codebase whose correct answer changes
every month, so a test that reads the clock passes in August and fails in
September for reasons that have nothing to do with the code.
"""

from __future__ import annotations

from datetime import date

import pytest

from cvloom import dates
from cvloom.locale import Ongoing

_EN = Ongoing(render="Present", accepts=("Present",))
_ES = Ongoing(render="Actualidad", accepts=("Actualidad", "Presente", "Actual"))

# Every span case below is read against this, not against date.today().
_TODAY = date(2026, 8, 7)


# ── parse_partial ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2020-01", (2020, 1)),
        ("2020-12", (2020, 12)),
        ("  2020-03  ", (2020, 3)),
        ("2020", (2020, 1)),
        ("summer 2020", None),
        ("2020/13", None),
        ("Present", None),
        ("", None),
    ],
)
def test_parse_partial_opens_a_range(value: str, expected: tuple[int, int] | None) -> None:
    assert dates.parse_partial(value) == expected


def test_a_bare_year_is_january_opening_and_december_closing() -> None:
    """The asymmetry that keeps `2020` - `2020-05` from reading as inverted."""
    assert dates.parse_partial("2020") == (2020, 1)
    assert dates.parse_partial("2020", as_end=True) == (2020, 12)


def test_an_explicit_month_ignores_as_end() -> None:
    assert dates.parse_partial("2020-03", as_end=True) == (2020, 3)


# ── granularity ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2020-01", "YYYY-MM"), ("2020", "YYYY"), ("summer 2020", "other"), ("", "other")],
)
def test_granularity_classifies_what_wl_012_compares(value: str, expected: str) -> None:
    assert dates.granularity(value) == expected


# ── span_months: closed ranges ──────────────────────────────────────


def test_a_closed_range_counts_inclusively() -> None:
    """January to March is three months in the role, not two elapsed."""
    assert dates.span_months("2020-01", "2020-03", _EN, today=_TODAY) == 3


def test_a_single_month_role_is_one_month() -> None:
    assert dates.span_months("2020-01", "2020-01", _EN, today=_TODAY) == 1


def test_bare_years_span_the_whole_of_both() -> None:
    """A 2013-2017 degree is five years, not one — January 2013 to December 2017."""
    assert dates.span_months("2013", "2017", _EN, today=_TODAY) == 60


def test_mixed_granularity_resolves_each_end_its_own_way() -> None:
    assert dates.span_months("2020", "2020-05", _EN, today=_TODAY) == 5
    assert dates.span_months("2020-05", "2020", _EN, today=_TODAY) == 8


def test_a_two_year_three_month_tenure() -> None:
    assert dates.span_months("2020-01", "2022-03", _EN, today=_TODAY) == 27


# ── span_months: the current-month ceiling ──────────────────────────


def test_a_missing_end_counts_to_the_current_month() -> None:
    assert dates.span_months("2025-06", None, _EN, today=_TODAY) == 15


def test_an_empty_end_is_treated_like_a_missing_one() -> None:
    assert dates.span_months("2025-06", "", _EN, today=_TODAY) == 15


@pytest.mark.parametrize("word", ["Present", "present", "  Present  "])
def test_the_locales_ongoing_word_counts_to_the_current_month(word: str) -> None:
    assert dates.span_months("2025-06", word, _EN, today=_TODAY) == 15


@pytest.mark.parametrize("word", ["Actualidad", "Presente", "Actual"])
def test_a_spanish_project_reads_its_own_ongoing_words(word: str) -> None:
    """Reading only `Present` would make every current es role uncomputable."""
    assert dates.span_months("2025-06", word, _ES, today=_TODAY) == 15


def test_an_english_ongoing_word_is_unparseable_under_an_es_pack() -> None:
    assert dates.span_months("2025-06", "Present", _ES, today=_TODAY) is None


def test_the_current_year_clamps_back_from_december() -> None:
    """`parse_partial(as_end=True)` pushes a bare year to December; the ceiling
    pulls it back, so a role does not claim months that have not happened."""
    assert dates.span_months("2026-01", "2026", _EN, today=_TODAY) == 8


def test_a_future_end_date_clamps_rather_than_inflating() -> None:
    assert dates.span_months("2026-01", "2027-01", _EN, today=_TODAY) == 8


def test_a_past_year_still_resolves_to_its_december() -> None:
    """The ceiling only bites at the top; it must not shorten a finished role."""
    assert dates.span_months("2025-01", "2025", _EN, today=_TODAY) == 12


# ── span_months: what is not computable ─────────────────────────────


@pytest.mark.parametrize("start", ["summer 2020", "2020/13", "", "Q1 2020"])
def test_an_unparseable_start_has_no_span(start: str) -> None:
    assert dates.span_months(start, "2022-03", _EN, today=_TODAY) is None


@pytest.mark.parametrize("end", ["summer 2022", "2022/13", "ongoing"])
def test_an_unparseable_end_that_is_not_the_ongoing_word_has_no_span(end: str) -> None:
    assert dates.span_months("2020-01", end, _EN, today=_TODAY) is None


def test_a_range_that_ends_before_it_starts_has_no_span() -> None:
    assert dates.span_months("2020-01", "2019-01", _EN, today=_TODAY) is None


def test_a_start_date_in_the_future_has_no_span() -> None:
    assert dates.span_months("2027-01", None, _EN, today=_TODAY) is None


# ── month range ──────────────────────────────────────────────────────


@pytest.mark.parametrize("value", ["2020-00", "2020-13", "2020-99"])
def test_out_of_range_months_are_not_dates(value: str) -> None:
    """`\\d{2}` is a shape, not a month.

    This module calls itself the one place cvloom reads a CV date, and nothing
    downstream re-validates: the linter compares the tuples it returns and
    `span_months` does base-12 arithmetic on them, so `2020-13` silently became
    a real date one month before 2021-01.
    """
    assert dates.parse_partial(value) is None
    assert dates.granularity(value) == "other"
