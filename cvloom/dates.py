"""Partial-date arithmetic: the one place cvloom reads a CV date string.

CV dates are ``YYYY`` or ``YYYY-MM`` by convention but plain strings by schema
(``schemas/work.json`` documents the shape in prose and enforces no pattern), so
``summer 2020`` is legal data that renders fine. Everything that needs to *reason*
about a date rather than print it comes through here: the linter's chronology,
date-format and date-sanity rules, and the tenure suffix ``filters.duration``
writes after a work date range.

One module rather than two implementations, because the two callers must agree on
the awkward part — what a bare year means. A year that closes a range is December
and one that opens a range is January, so ``2020`` – ``2020-05`` is not read as
ending before it starts, and a ``2013``–``2017`` degree spans five years rather
than one.
"""

from __future__ import annotations

import re
from datetime import date

from cvloom.locale import Ongoing

# The month is range-checked in the pattern, not merely shaped: nothing
# downstream re-validates, so `2020-13` would reach base-12 arithmetic as a
# real date one month before 2021-01.
_DATE_YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE_YYYY_RE = re.compile(r"^\d{4}$")


def parse_partial(value: str, *, as_end: bool = False) -> tuple[int, int] | None:
    """Parse ``YYYY`` / ``YYYY-MM`` into a comparable ``(year, month)``.

    ``Present`` (and anything unparseable) returns ``None``; callers decide what
    an open-ended date means. A bare year resolves to December when it closes a
    range and January when it opens one.
    """
    text = value.strip()
    if _DATE_YYYY_MM_RE.match(text):
        year, month = text.split("-")
        return int(year), int(month)
    if _DATE_YYYY_RE.match(text):
        return int(text), 12 if as_end else 1
    return None


def granularity(value: str) -> str:
    """Classify *value* as ``"YYYY-MM"``, ``"YYYY"`` or ``"other"``.

    What the date-format consistency rule compares. Separate from
    :func:`parse_partial` because that one collapses ``YYYY`` and ``YYYY-MM`` into
    the same shape, which is exactly the distinction wl-012 exists to see.
    """
    text = value.strip()
    if _DATE_YYYY_MM_RE.match(text):
        return "YYYY-MM"
    if _DATE_YYYY_RE.match(text):
        return "YYYY"
    return "other"


def span_months(
    start: str, end: str | None, ongoing: Ongoing, *, today: date | None = None
) -> int | None:
    """Months from *start* to *end* inclusive, or ``None`` if that is not knowable.

    Inclusive because that is how a CV reader counts a tenure: January to March is
    three months in the role, not two elapsed.

    **The current month is the ceiling**, applied to every end date rather than
    only to open-ended ones. An absent *end*, or one this locale's ``ongoing``
    accepts, resolves to the current month; so does a bare year that is *this*
    year, which :func:`parse_partial` would otherwise push out to December; and so
    does a typo'd future end date, which would otherwise inflate the tenure. The
    future date itself is not hidden — the linter's wl-020 reports it.

    ``None`` means "do not render a duration": an unparseable *start*, an
    unparseable *end* that is not the ongoing word, or a range that ends before it
    begins (which includes a start date in the future).
    """
    today = today or date.today()
    ceiling = (today.year, today.month)

    first = parse_partial(start)
    if first is None:
        return None

    text = str(end or "").strip()
    if not text or ongoing.matches(text):
        last = ceiling
    else:
        parsed = parse_partial(text, as_end=True)
        if parsed is None:
            return None
        last = min(parsed, ceiling)

    total = (last[0] * 12 + last[1]) - (first[0] * 12 + first[1]) + 1
    return total if total > 0 else None
