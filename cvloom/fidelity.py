"""How much of a CV's own text survives into the built PDF's text layer.

The first thing any consumer of a PDF does is extract its text, and the engines
in :mod:`cvloom.extract` disagree about the result. ``build --extract-text``
already writes one file per engine; reading five files side by side to find the
one word that went missing is not a thing anyone does. This scores them instead.

**This is not an ATS score, and the distinction is the point.** What is measured
here has a stated denominator — the tokens in the user's own resolved data — and
a mechanical definition: did this exact token come back out. There is no model of
recruiter behaviour, no weighting, no composite, and no number spanning engines.
``docs/reference/ats-readiness.md`` argues at length against invented aggregates;
a per-engine recall against a source the user can read is the opposite of one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from cvloom import extract as extract_mod
from cvloom import match, sections
from cvloom.models import ResolvedProfile

# Single characters carry no evidence: `a` occurs inside almost any extraction by
# accident, so counting it would inflate every engine's score identically.
_MIN_TOKEN_LENGTH = 2

# Below this length a substring test stops discriminating — `ai` occurs inside
# `domain`, `ml` inside `html` — and short tokens are disproportionately the ones
# worth measuring, since `ai`, `ml`, `aws`, `js` and `sql` are skill names. These
# must match as whole words; longer tokens keep the substring test, which is what
# lets a word welded to its neighbour still count as found.
_BOUNDARY_BELOW = 4


@cache
def _boundary_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(token)}(?!\w)")


def _found(token: str, haystack: str) -> bool:
    """Whether *token* survived into *haystack*, both already case-folded."""
    if len(token) < _BOUNDARY_BELOW:
        return _boundary_re(token).search(haystack) is not None
    return token in haystack


@dataclass(frozen=True)
class EngineRecall:
    """One engine's result against the tokens the template actually rendered."""

    engine: str
    found: int
    total: int
    missing: tuple[str, ...]

    @property
    def percentage(self) -> float:
        return 100.0 * self.found / self.total if self.total else 100.0


@dataclass(frozen=True)
class RecallReport:
    """Two different failures, separated, because the fixes are different.

    A word in the user's data can fail to reach a parser two ways, and reporting
    one number for both sends people to the wrong place. ``unrendered`` is a word
    no engine found, which means the *template* never put it on the page — a
    layout that omits a field, not a text-layer defect, and no extractor could
    have helped. ``engines`` is what happened to the rest, where a disagreement
    between engines is the signal that the text layer is ambiguous.

    They are told apart by engine agreement, which works because the engines read
    the document by genuinely different means: all of them missing the same word
    is not several failures, it is the word not being there.

    Agreement needs at least two engines. With one installed there is nothing to
    corroborate it, so nothing is attributed to the template and ``unrendered``
    stays empty — see ``attribution_available``.
    """

    unrendered: tuple[str, ...]
    engines: tuple[EngineRecall, ...]
    source_total: int

    @property
    def attribution_available(self) -> bool:
        """Whether a missing word could be blamed on the template at all.

        False when fewer than two engines ran. Callers should say so rather than
        present ``unrendered`` as empty because the template rendered everything.
        """
        return len(self.engines) >= 2


def source_tokens(resolved: ResolvedProfile) -> list[str]:
    """The distinct word tokens of the CV's *prose*, in document order.

    Deduplicated because recall asks whether a word reached the text layer, not
    how often. A term repeated in ten bullets that extracts correctly would
    otherwise count ten successes and hide a rarer term that failed.

    The denominator is ``sections.iter_visible_text``: entry sections, skills,
    the headline and summary, profile link labels, and the contact block. The
    header is in there because it is the most extraction-fragile text on the page
    — a name and an email, set apart from the body — and scoring the document
    without it measured everything except the region most likely to fail.

    Link *URLs* are excluded: they are not prose, and tokenising them turns one
    address into a handful of tokens that say nothing about the text layer.
    """
    seen: dict[str, None] = {}
    for _, text in sections.iter_visible_text(resolved):
        for token in match.tokenize(text):
            if len(token) >= _MIN_TOKEN_LENGTH:
                seen.setdefault(token, None)
    return list(seen)


def recall(resolved: ResolvedProfile, pdf_path: Path) -> RecallReport:
    """Score every installed engine's extraction of *pdf_path* against *resolved*.

    Case-insensitive, because most templates uppercase their headings and a
    template's styling is not the user's content going missing. Substring rather
    than token matching on the extracted side: the failure being measured is a
    word that vanished or was split, and a word welded to its neighbour is caught
    by :mod:`cvloom.extract`'s own tests rather than counted as absent here. Short
    tokens are the exception — see ``_BOUNDARY_BELOW``.

    Words no engine found are attributed to the template and excluded from every
    engine's denominator — see :class:`RecallReport`. Scoring them against the
    extractors would mark every engine down for a word none of them was ever
    shown, and `cv/sidebar-compact`, which renders no education detail at all,
    would read as a 95% extraction failure it is not responsible for.

    That attribution requires corroboration, so it is skipped below two engines.
    A lone engine's misses are indistinguishable from words the template never
    drew; blaming the template for them would remove exactly those tokens from
    the denominator and score the engine 100% for having lost them.
    """
    tokens = source_tokens(resolved)
    extractions = extract_mod.extract_all(pdf_path)
    if not extractions:
        return RecallReport(unrendered=(), engines=(), source_total=len(tokens))

    per_engine = {
        e.engine: {t for t in tokens if not _found(t, e.text.casefold())} for e in extractions
    }
    unrendered = set.intersection(*per_engine.values()) if len(per_engine) >= 2 else set()
    rendered = [t for t in tokens if t not in unrendered]

    engines = tuple(
        EngineRecall(
            engine=engine,
            found=len(rendered) - len(missing - unrendered),
            total=len(rendered),
            missing=tuple(t for t in rendered if t in missing),
        )
        for engine, missing in per_engine.items()
    )
    return RecallReport(
        unrendered=tuple(t for t in tokens if t in unrendered),
        engines=engines,
        source_total=len(tokens),
    )
