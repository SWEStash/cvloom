"""The groundedness checker, and its assertions against the AI orchestrators.

`cvloom.ai.prompts.GROUNDING` is a promise made in a prompt string, which is to say
a promise with nothing enforcing it. This module supplies the enforcement: a
reference-free check that every number a model writes traces back to the CV it was
given. No labelling, no backend, and it catches the single highest-harm failure —
an invented metric the user pastes into a real CV and is asked about in an interview.

`ungrounded_numbers` is the reusable half. The live evaluation suite reuses it for
`cover` and `align`, where the same exposure exists in free prose.
"""

from __future__ import annotations

import json
import re

import pytest

from cvloom.ai.analysis import SCOPE_FULL, analysis_context_block
from cvloom.ai.prompts import GROUNDING
from cvloom.ai.provider import cv_to_text
from cvloom.ai.suggest import suggest
from cvloom.models import ResolvedProfile
from tests.ai_fakes import FakeClient
from tests.conftest import make_resolved

# A number, with optional thousands separators and decimal part. The leading
# currency symbol and trailing percent are matched so they can be stripped —
# "$1,200", "1200" and "1200%" are the same claim about the same fact.
#
# The lookbehind keeps digits that are glued to a preceding letter out: `p99`,
# `S3` and `IPv6` are identifiers, not claims about magnitude, and treating them
# as metrics would flag a rewrite that merely mentions the same system.
_NUMBER = re.compile(r"(?<![A-Za-z0-9])[$€£]?\d[\d,.]*%?")

# Text the model is invited to emit in place of a number it does not have. Numbers
# inside one are the user's to fill in, not a fabrication.
_PLACEHOLDER = re.compile(r"\[[^\]]*\]")


def numeric_tokens(text: str) -> set[str]:
    """Every number in *text*, normalized so formatting differences do not matter."""
    tokens = set()
    for raw in _NUMBER.findall(text):
        token = raw.strip("$€£%").replace(",", "").rstrip(".")
        if token:
            tokens.add(token)
    return tokens


def ungrounded_numbers(generated: str, source: str) -> set[str]:
    """Numbers in *generated* that are absent from *source* and not placeheld.

    Empty means grounded. A non-empty result is the exact set of figures the model
    invented, which is what makes the failure message useful.
    """
    outside_placeholders = _PLACEHOLDER.sub(" ", generated)
    return numeric_tokens(outside_placeholders) - numeric_tokens(source)


# ---------------------------------------------------------------------------
# The checker itself
# ---------------------------------------------------------------------------


def test_a_figure_from_the_cv_is_grounded() -> None:
    assert ungrounded_numbers("Handled 10k requests", "Designed a system for 10k requests") == set()


def test_an_invented_figure_is_caught() -> None:
    """The `99` in `p99` is a name, not a claim; the `40%` is the fabrication."""
    assert ungrounded_numbers("Cut p99 latency by 40%", "Improved latency") == {"40"}


def test_formatting_is_not_fabrication() -> None:
    """`$1,200` and `1200` are the same claim; the checker must not flag the rewrite."""
    assert ungrounded_numbers("Saved $1,200 per month", "Saved 1200 monthly") == set()


def test_a_placeholder_is_not_fabrication() -> None:
    """GROUNDING invites exactly this shape, so flagging it would punish compliance."""
    generated = "Cut deploy time [add metric: e.g. 40% faster]"
    assert ungrounded_numbers(generated, "Improved deploys") == set()


def test_a_year_outside_the_cv_is_caught() -> None:
    assert ungrounded_numbers("Led the 2019 migration", "Led a migration") == {"2019"}


# ---------------------------------------------------------------------------
# The orchestrator, checked against it
# ---------------------------------------------------------------------------


def _metric_free_cv() -> ResolvedProfile:
    """A CV with no numbers anywhere — the condition under which a model invents them."""
    return make_resolved(
        basics={"headline": "Backend Engineer", "summary": "Builds services."},
        contact={"name": "Jane Smith"},
        work=[
            {
                "company": "Acme Corp",
                "title": "Engineer",
                "start_date": "",
                "end_date": "",
                "highlights": [
                    "Responsible for the payments service.",
                    "Worked on reducing deployment friction.",
                ],
            }
        ],
        skills=[{"category": "Languages", "items": ["Python"]}],
        show={"work": True, "skills": True},
        section_order=["work", "skills"],
    )


def _suggest_response(suggested: str) -> str:
    return json.dumps(
        {
            "suggestions": [
                {
                    "section": "work",
                    "entry": "Acme Corp",
                    "type": "reword",
                    "current": "Responsible for the payments service.",
                    "suggested": suggested,
                    "rationale": "Leads with an outcome.",
                }
            ],
            "missing_skills": [],
            "summary": "Reframe as outcomes.",
        }
    )


def _run_suggest(resolved: ResolvedProfile, suggested: str) -> tuple[list[str], str]:
    client = FakeClient(_suggest_response(suggested))
    result = suggest(resolved, client, "test-model")
    return [s.suggested for s in result.suggestions], cv_to_text(
        resolved.data, resolved.show_sections, resolved.locale
    )


def test_a_fabricated_suggestion_does_not_pass_the_check() -> None:
    """The checker's own regression test: it has to fail on the case it exists for.

    Written against a model response rather than a bare string so the whole path —
    prompt build, parse, serialize the source CV — is what gets checked.
    """
    resolved = _metric_free_cv()
    suggestions, source = _run_suggest(resolved, "Owned payments, cutting failures 40%.")
    assert ungrounded_numbers(suggestions[0], source) == {"40"}


def test_a_placeheld_suggestion_passes_the_check() -> None:
    resolved = _metric_free_cv()
    suggested = "Owned the payments service, cutting failures [add metric: e.g. % decline]."
    suggestions, source = _run_suggest(resolved, suggested)
    assert ungrounded_numbers(suggestions[0], source) == set()


@pytest.mark.parametrize(
    "suggested", ["Owned payments end to end.", "Shipped the payments service."]
)
def test_every_suggestion_is_grounded(suggested: str) -> None:
    """The assertion the live evaluation suite runs against a real backend."""
    resolved = _metric_free_cv()
    suggestions, source = _run_suggest(resolved, suggested)
    for text in suggestions:
        assert ungrounded_numbers(text, source) == set(), f"invented figures in: {text}"


# ── Citations must trace to a finding the model was actually shown ──


def _cited_response(rule_ids: list[str]) -> str:
    return json.dumps(
        {
            "suggestions": [
                {
                    "section": "work",
                    "entry": "Acme Corp",
                    "type": "reword",
                    "current": "Responsible for the payments service.",
                    "suggested": "Owned the payments service end to end.",
                    "rationale": "Leads with an outcome.",
                    "related_findings": rule_ids,
                }
            ],
            "missing_skills": [],
            "summary": "Reframe as outcomes.",
        }
    )


def _rule_ids_in_context(resolved: ResolvedProfile) -> set[str]:
    """The rule ids the model could legitimately have read."""
    cv_text = cv_to_text(resolved.data, resolved.show_sections, resolved.locale)
    block = analysis_context_block(resolved, cv_text, scope=SCOPE_FULL)
    return set(re.findall(r"wl-\d{3}", block.text))


def test_the_analysis_block_offers_rule_ids_to_cite() -> None:
    """Without this the two tests below pass for the wrong reason — an empty set is
    trivially a subset of anything."""
    assert _rule_ids_in_context(_metric_free_cv())


def test_a_citation_the_model_was_shown_is_accepted() -> None:
    resolved = _metric_free_cv()
    offered = sorted(_rule_ids_in_context(resolved))
    result = suggest(resolved, FakeClient(_cited_response(offered[:1])), "test-model")
    assert set(result.suggestions[0].related_findings) <= _rule_ids_in_context(resolved)


def test_a_citation_the_model_invented_is_visible_rather_than_dropped() -> None:
    """The parser deliberately does not filter unknown ids: silently dropping one
    hides a misbehaving model, whereas a rule id absent from `cvloom check` is a
    symptom the user can see and report."""
    resolved = _metric_free_cv()
    result = suggest(resolved, FakeClient(_cited_response(["wl-999"])), "test-model")
    assert result.suggestions[0].related_findings == ["wl-999"]
    assert not set(result.suggestions[0].related_findings) <= _rule_ids_in_context(resolved)


def test_the_contract_forbids_deriving_a_figure_from_the_cvs_own_numbers() -> None:
    """Rule 2 covers a metric the CV lacks and rule 1 permits recombining what it
    has, so nothing forbade calculating a new one. A live run turned "800ms to
    120ms" into "by 83%" — unsourced, and wrong arithmetic besides."""
    assert "Do not work out a new figure from figures the CV states" in GROUNDING
    assert "Quote the figures the CV gives" in GROUNDING


def test_a_derived_percentage_is_caught_as_ungrounded() -> None:
    """The rubric already treats it as invented, which is how it was found."""
    source = "Reduced p99 latency from 800ms to 120ms"
    assert ungrounded_numbers("Reduced backend response time by 83%", source) == {"83"}
    assert ungrounded_numbers("Reduced p99 latency from 800ms to 120ms", source) == set()
