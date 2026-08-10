"""Every AI prompt is assembled stable-content-first.

The ordering exists for prompt caching: a provider can only reuse the prefix up to
the first byte that changed, and the JSON schema is identical on every run while the
CV is not. Nothing in the type system expresses that, so this file is the only thing
holding the order in place — without it the next edit to a builder silently puts the
CV back on top and the caching benefit disappears with no test going red.
"""

from __future__ import annotations

import pytest

from cvloom.ai.align import _build_align_prompt
from cvloom.ai.analyzer import _build_review_prompt
from cvloom.ai.cover import _build_cover_prompt
from cvloom.ai.prompts import CLOSING, JD_UNTRUSTED, assemble
from cvloom.ai.suggest import _build_suggest_prompt
from cvloom.match import KeywordMatch, MatchReport

_CV = "Jane Doe | Senior Engineer\n\n## Work Experience\n\nAcme — Engineer | 2020 – Present"
_JD = "We need a Python developer with Kubernetes experience."


def _match_report() -> MatchReport:
    return MatchReport(
        matched=[KeywordMatch(keyword="python", found_in=["skills"], frequency_jd=3)],
        gaps=["kubernetes"],
        jd_word_count=300,
        cv_keywords_coverage=0.65,
        reorder_hints=["Move Kubernetes earlier in skills"],
    )


def _block_at(prompt: str, tag: str) -> int:
    """Index of the real ``<tag>`` block, not a mention of the tag in the instructions.

    JD_UNTRUSTED names ``<job_description>`` in prose, so a bare ``index()`` finds the
    instruction rather than the block and every ordering assertion passes vacuously.
    An emitted block always opens with the tag on its own line.
    """
    return prompt.index(f"{tag}\n")


def _prompts() -> dict[str, str]:
    return {
        "review": _build_review_prompt(_CV, ["work", "skills"]),
        "suggest": _build_suggest_prompt(_CV, ["work"], "Senior Backend Engineer"),
        "align": _build_align_prompt(_CV, _JD, _match_report()),
        "cover": _build_cover_prompt(_CV, _JD, {"company": "Acme", "role": "Engineer"}),
    }


@pytest.mark.parametrize("name", ["review", "suggest", "align", "cover"])
def test_the_schema_precedes_the_cv(name: str) -> None:
    """The instruction and its JSON schema are the cacheable prefix, so they come first."""
    prompt = _prompts()[name]
    assert prompt.index('"') < _block_at(prompt, "<cv>"), f"{name}: schema must precede <cv>"


@pytest.mark.parametrize("name", ["review", "suggest", "align", "cover"])
def test_the_cv_is_not_the_first_block(name: str) -> None:
    prompt = _prompts()[name]
    assert not prompt.startswith("<cv>"), f"{name}: <cv> is volatile and must not lead"


@pytest.mark.parametrize("name", ["review", "suggest", "align", "cover"])
def test_the_closing_line_is_last(name: str) -> None:
    """CLOSING is the one deliberate exception: uncached, but it restores recency."""
    assert _prompts()[name].endswith(CLOSING)


@pytest.mark.parametrize(
    ("name", "blocks"),
    [
        ("suggest", ["<cv>", "<target_role>"]),
        ("align", ["<keyword_analysis>", "<cv>", "<job_description>"]),
        ("cover", ["<cv>", "<job_description>", "<job_context>"]),
    ],
)
def test_volatile_blocks_run_least_to_most_specific(name: str, blocks: list[str]) -> None:
    """Job-specific context trails the CV, which trails the CV-wide analysis."""
    prompt = _prompts()[name]
    positions = [_block_at(prompt, block) for block in blocks]
    assert positions == sorted(positions), f"{name}: expected {blocks} in that order"


@pytest.mark.parametrize(
    ("name", "report_field"),
    [
        ("review", "the first item of top_priorities"),
        ("suggest", "summary"),
        ("align", "narrative"),
        ("cover", "letter"),
    ],
)
def test_every_command_names_where_to_report_an_unusable_input(
    name: str, report_field: str
) -> None:
    """The field named must exist in that command's own schema, or the model cannot comply."""
    prompt = _prompts()[name]
    assert "Reporting that the input is unusable is a correct answer." in prompt
    assert f"say exactly that in {report_field}" in prompt


@pytest.mark.parametrize("name", ["align", "cover"])
def test_the_jd_is_framed_as_untrusted_before_it_arrives(name: str) -> None:
    """A downloaded JD carrying "ignore previous instructions" is a real injection surface."""
    prompt = _prompts()[name]
    assert JD_UNTRUSTED in prompt
    assert prompt.index(JD_UNTRUSTED) < _block_at(prompt, "<job_description>")


@pytest.mark.parametrize("name", ["review", "suggest"])
def test_commands_without_a_job_description_do_not_carry_the_jd_framing(name: str) -> None:
    assert JD_UNTRUSTED not in _prompts()[name]


def test_assemble_drops_empty_parts() -> None:
    """An optional block is an empty string, not a branch — and leaves no blank gap."""
    assert assemble("a", "", "b") == "a\n\nb"
    assert assemble("", "") == ""
