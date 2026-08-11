"""Tests for cvloom.ai.align — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.align import _build_align_prompt, _parse_align_result
from cvloom.locale import default_pack
from cvloom.match import KeywordMatch, MatchReport

# ---------------------------------------------------------------------------
# _parse_align_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps(
        {
            "alignment_band": "strong",
            "narrative": "The CV is a strong match. The candidate has relevant experience.",
            "repositioning": ["Lead with cloud infrastructure experience", "Quantify team size"],
            "tone_gaps": ["JD emphasises leadership; CV is task-focused"],
            "strengths": ["Strong backend experience matches JD requirements"],
        }
    )
    result = _parse_align_result(raw)
    assert result.alignment_band == "strong"
    assert "strong match" in result.narrative
    assert len(result.repositioning) == 2
    assert len(result.tone_gaps) == 1
    assert len(result.strengths) == 1


def test_parse_missing_optional_fields() -> None:
    raw = json.dumps({})
    result = _parse_align_result(raw)
    assert result.alignment_band == ""
    assert result.narrative == ""
    assert result.repositioning == []
    assert result.tone_gaps == []
    assert result.strengths == []


def test_parse_normalises_band_case_and_padding() -> None:
    result = _parse_align_result(json.dumps({"alignment_band": " Needs Work "}))
    assert result.alignment_band == "needs work"


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_align_result("not valid json")


def test_parse_empty_lists() -> None:
    raw = json.dumps(
        {
            "alignment_band": "adequate",
            "narrative": "Moderate fit.",
            "repositioning": [],
            "tone_gaps": [],
            "strengths": [],
        }
    )
    result = _parse_align_result(raw)
    assert result.repositioning == []
    assert result.tone_gaps == []
    assert result.strengths == []


# ---------------------------------------------------------------------------
# _build_align_prompt
# ---------------------------------------------------------------------------


def _make_match_report(gaps: list[str] | None = None) -> MatchReport:
    return MatchReport(
        matched=[KeywordMatch(keyword="python", found_in=["skills"], frequency_jd=3)],
        gaps=gaps or ["kubernetes", "terraform"],
        jd_word_count=300,
        cv_keywords_coverage=0.65,
        reorder_hints=["Move cloud experience entry higher"],
    )


def test_prompt_contains_cv_text() -> None:
    prompt = _build_align_prompt(
        "Jane Doe | Backend Engineer",
        "We need a Python developer.",
        _make_match_report(),
        default_pack(),
    )
    assert "Jane Doe | Backend Engineer" in prompt


def test_prompt_contains_jd_text() -> None:
    prompt = _build_align_prompt(
        "cv text", "We need a Python developer.", _make_match_report(), default_pack()
    )
    assert "We need a Python developer." in prompt


def test_prompt_contains_match_data() -> None:
    prompt = _build_align_prompt(
        "cv text", "jd text", _make_match_report(gaps=["kubernetes", "terraform"]), default_pack()
    )
    assert "kubernetes" in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_align_prompt("cv text", "jd text", _make_match_report(), default_pack())
    assert "alignment_band" in prompt
    assert "narrative" in prompt
    assert "repositioning" in prompt
    assert "tone_gaps" in prompt
    assert "strengths" in prompt


def test_prompt_states_what_each_band_means() -> None:
    prompt = _build_align_prompt("cv text", "jd text", _make_match_report(), default_pack())
    for band in ("strong", "adequate", "needs work"):
        assert f'"{band}"' in prompt


def test_prompt_bands_the_fit_not_the_cv() -> None:
    """Shared rubric, different subject — align grades a pairing, review a document."""
    prompt = _build_align_prompt("cv text", "jd text", _make_match_report(), default_pack())
    assert "a strong CV for other roles can align badly with this one" in prompt


def test_prompt_includes_coverage() -> None:
    prompt = _build_align_prompt("cv text", "jd text", _make_match_report(), default_pack())
    assert "65%" in prompt
