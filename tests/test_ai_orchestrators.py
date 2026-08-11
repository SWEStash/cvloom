"""Tests for the AI orchestration functions using a fake client.

Covers the full call path — context assembly, ``chat.completions.create``
invocation, and response parsing — for all four orchestrators, including
malformed-JSON responses.
"""

from __future__ import annotations

import json

import pytest

from cvloom.ai.align import align
from cvloom.ai.analyzer import review
from cvloom.ai.cover import generate_cover
from cvloom.ai.prompts import GROUNDING, SYSTEM_ANALYSIS, SYSTEM_CREATIVE
from cvloom.ai.suggest import suggest
from cvloom.locale import LocalePack, load_pack
from cvloom.models import ResolvedProfile
from tests.ai_fakes import FakeClient
from tests.conftest import make_resolved


def _make_resolved(locale_pack: LocalePack | None = None) -> ResolvedProfile:
    return make_resolved(
        locale_pack=locale_pack,
        profile={"job_context": {"company": "Acme", "role": "Backend Engineer"}},
        basics={
            "headline": "Backend Engineer",
            "summary": "Engineer with Python and cloud experience.",
        },
        contact={"name": "Jane Doe"},
        work=[
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": ["Designed a distributed system handling 10k requests."],
            }
        ],
        skills=[{"category": "Languages", "items": ["Python"]}],
        show={"work": True, "skills": True},
        section_order=["work", "skills"],
    )


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


def test_review_success() -> None:
    client = FakeClient(
        json.dumps(
            {
                "overall_score": 7.5,
                "sections": [
                    {
                        "section": "work",
                        "score": 8.0,
                        "strengths": ["quantified"],
                        "weaknesses": [],
                        "suggestions": ["add metrics"],
                    }
                ],
                "top_priorities": ["quantify more bullets"],
            }
        )
    )
    result = review(_make_resolved(), client, "test-model")
    assert result.overall_score == 7.5
    assert result.sections[0].section == "work"
    assert result.top_priorities == ["quantify more bullets"]


def test_review_passes_model_and_system_prompt() -> None:
    client = FakeClient(json.dumps({"overall_score": 5.0, "sections": [], "top_priorities": []}))
    review(_make_resolved(), client, "test-model")
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "test-model"
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_ANALYSIS}
    assert "Jane Doe" in call["messages"][1]["content"]


def test_review_malformed_json_raises() -> None:
    client = FakeClient("this is not { json")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        review(_make_resolved(), client, "test-model")


# ---------------------------------------------------------------------------
# generate_cover
# ---------------------------------------------------------------------------


def test_generate_cover_success() -> None:
    client = FakeClient(
        json.dumps(
            {
                "letter": "Dear Hiring Manager, I am excited to apply.",
                "word_count": 8,
                "key_alignments": ["Python experience"],
            }
        )
    )
    result = generate_cover(_make_resolved(), "We need a Python developer.", client, "test-model")
    assert result.letter.startswith("Dear Hiring Manager")
    assert result.word_count == 8
    assert result.key_alignments == ["Python experience"]


def test_generate_cover_uses_creative_system_prompt() -> None:
    client = FakeClient(json.dumps({"letter": "Hi.", "word_count": 1, "key_alignments": []}))
    generate_cover(_make_resolved(), "jd text", client, "test-model")
    call = client.calls[0]
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_CREATIVE}
    assert "jd text" in call["messages"][1]["content"]


def test_generate_cover_malformed_json_raises() -> None:
    client = FakeClient("{broken")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        generate_cover(_make_resolved(), "jd text", client, "test-model")


# ---------------------------------------------------------------------------
# suggest
# ---------------------------------------------------------------------------


def test_suggest_success() -> None:
    client = FakeClient(
        json.dumps(
            {
                "suggestions": [
                    {
                        "section": "work",
                        "entry": "Acme",
                        "type": "bullet",
                        "current": None,
                        "suggested": "Reduced latency by 40%.",
                        "rationale": "Adds a metric.",
                    }
                ],
                "missing_skills": ["Kubernetes"],
                "summary": "Solid CV, add metrics.",
            }
        )
    )
    result = suggest(_make_resolved(), client, "test-model", role_context="Senior Backend")
    assert result.suggestions[0].suggested == "Reduced latency by 40%."
    assert result.missing_skills == ["Kubernetes"]
    assert "Senior Backend" in client.calls[0]["messages"][1]["content"]


def test_suggest_malformed_json_raises() -> None:
    client = FakeClient("not json at all")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        suggest(_make_resolved(), client, "test-model")


# ---------------------------------------------------------------------------
# align
# ---------------------------------------------------------------------------


def test_align_success() -> None:
    client = FakeClient(
        json.dumps(
            {
                "alignment_score": 6.5,
                "narrative": "The CV aligns reasonably well.",
                "repositioning": ["Lead with cloud experience."],
                "tone_gaps": ["JD emphasizes leadership."],
                "strengths": ["Python match"],
            }
        )
    )
    result = align(_make_resolved(), "We need a Python developer.", client, "test-model")
    assert result.alignment_score == 6.5
    assert result.repositioning == ["Lead with cloud experience."]


def test_align_prompt_includes_keyword_analysis() -> None:
    client = FakeClient(json.dumps({"alignment_score": 5.0, "narrative": "ok"}))
    align(_make_resolved(), "We need Python and Kubernetes experience.", client, "test-model")
    prompt = client.calls[0]["messages"][1]["content"]
    assert "<keyword_analysis>" in prompt
    assert "coverage:" in prompt


def test_align_malformed_json_raises() -> None:
    client = FakeClient("<html>error</html>")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        align(_make_resolved(), "jd text", client, "test-model")


# ---------------------------------------------------------------------------
# The grounding contract
# ---------------------------------------------------------------------------


def test_every_orchestrator_sends_the_grounding_contract() -> None:
    """The one thing standing between a creative model and a fabricated CV.

    Asserted per orchestrator rather than on the constants alone: a future feature
    that assembles its own system prompt would pass a constants-only test while
    shipping an ungrounded command.
    """
    resolved = _make_resolved()
    for call in (
        lambda c: review(resolved, c, "test-model"),
        lambda c: suggest(resolved, c, "test-model"),
        lambda c: generate_cover(resolved, "jd text", c, "test-model"),
        lambda c: align(resolved, "jd text", c, "test-model"),
    ):
        client = FakeClient(json.dumps({"narrative": "ok", "letter": "ok"}))
        call(client)
        system = client.calls[0]["messages"][0]["content"]
        assert GROUNDING in system
        assert "[add metric" in system


def test_every_orchestrator_sends_the_projects_own_language() -> None:
    """Asserted through the orchestrator, not the builder, because the pack has to be
    read off ``ResolvedProfile`` and passed down — a builder-only test passes while
    an orchestrator quietly hands over the default."""
    resolved = _make_resolved(locale_pack=load_pack("es")[0])
    for call in (
        lambda c: review(resolved, c, "test-model"),
        lambda c: suggest(resolved, c, "test-model"),
        lambda c: generate_cover(resolved, "jd text", c, "test-model"),
        lambda c: align(resolved, "jd text", c, "test-model"),
    ):
        client = FakeClient(json.dumps({"narrative": "ok", "letter": "ok"}))
        call(client)
        prompt = client.calls[0]["messages"][1]["content"]
        assert prompt.startswith("<locale>\n")
        assert "Spanish (es)" in prompt


def test_suggest_runs_cold() -> None:
    """Variety in a reworded achievement is fabrication, not style."""
    client = FakeClient(json.dumps({"suggestions": []}))
    suggest(_make_resolved(), client, "test-model")
    assert client.calls[0]["temperature"] == 0.2
