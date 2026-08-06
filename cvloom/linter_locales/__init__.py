"""Per-locale linter data — lexicons, compiled patterns and thresholds.

Deliberately Python rather than YAML (decision F8). The boundary is
config-vs-opinion, not data-vs-code: ``section_titles`` is content the user
legitimately owns and so lives in ``cvloom/locales/<code>.yaml``, while a
weak-verb list is an editorial judgement the tool holds. Exposing these in a
file users edit would create a linter-configuration API by accident, before the
configuration model has been designed.

``match``'s stop words live here for the same reason and by the same key.

Data every locale meaningfully has sits on :class:`LintLocale`. Data that exists
only for one locale — the Spanish style classifier's verb endings, the diacritic
list — stays a module constant in that locale's module and is read directly by
the locale-specific rule that needs it, so ``LintLocale`` does not grow fields
that are empty everywhere but one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── The per-locale data contract ────────────────────────────────────


@dataclass(frozen=True)
class LintLocale:
    """Lexicons, patterns and thresholds for one locale's writing lint."""

    code: str

    # wl-001 — passive voice. A tuple because Spanish needs two constructions
    # (pasiva refleja and periphrastic) where English needs one.
    passive_patterns: tuple[re.Pattern[str], ...]
    passive_false_positives: frozenset[str]

    # wl-003 — skills that add no signal.
    noise_skills: frozenset[str]

    # wl-004 — openers that bury the achievement, and the verbs to suggest
    # instead. The examples are data because the fix hint is user-facing prose.
    weak_openers: tuple[str, ...]
    strong_verb_examples: tuple[str, ...]

    # wl-005 — highlight length in words.
    min_highlight_words: int
    max_highlight_words: int

    # wl-007 — explicit first-person pronouns.
    first_person_pattern: re.Pattern[str]

    # wl-008 — vague buzzwords.
    buzzwords_pattern: re.Pattern[str]

    # wl-009 — skill counts.
    min_skills: int
    max_skills: int

    # wl-011 — words a rendered page holds, measured from a real render.
    words_per_page: int

    # wl-014 — summary length in words.
    min_summary_words: int
    max_summary_words: int

    # wl-015 — a quantified metric, and the framing that turns it into impact.
    metric_pattern: re.Pattern[str]
    result_framing_pattern: re.Pattern[str]

    # match — tokens carrying no keyword signal.
    stop_words: frozenset[str]


# ── Registry ────────────────────────────────────────────────────────


def _registry() -> dict[str, LintLocale]:
    # Imported inside the function because each locale module imports
    # ``LintLocale`` from here.
    from cvloom.linter_locales import en

    return {"en": en.LOCALE}


def available_locales() -> tuple[str, ...]:
    """Locale codes that have linter data, sorted."""
    return tuple(sorted(_registry()))


def pack_for(code: str) -> LintLocale:
    """Linter data for *code*, falling back to ``en``.

    A document locale pack can exist without linter data — someone contributing
    ``cvloom/locales/fr.yaml`` gets a French document before anyone has written
    French lexicons. The linter grades that CV with English heuristics rather
    than crashing; the rules it cannot honestly run are reported as skipped by
    :func:`cvloom.linter.rules_for`.
    """
    registry = _registry()
    return registry.get(code, registry["en"])
