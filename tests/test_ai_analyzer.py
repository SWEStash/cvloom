"""Tests for cvloom.ai.analyzer — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.analyzer import _build_review_prompt, _parse_review_result
from cvloom.locale import default_pack

# ---------------------------------------------------------------------------
# _parse_review_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps(
        {
            "sections": [
                {
                    "section": "work",
                    "band": "strong",
                    "strengths": ["Good metrics"],
                    "weaknesses": ["Too verbose"],
                    "suggestions": ["Add more numbers"],
                }
            ],
            "top_priorities": ["Quantify impact", "Tighten summary", "Add LinkedIn"],
        }
    )
    result = _parse_review_result(raw)
    assert result.overall_band == "strong"
    assert len(result.sections) == 1
    assert result.sections[0].section == "work"
    assert result.sections[0].band == "strong"
    assert result.sections[0].strengths == ["Good metrics"]
    assert result.sections[0].weaknesses == ["Too verbose"]
    assert result.sections[0].suggestions == ["Add more numbers"]
    assert result.top_priorities == ["Quantify impact", "Tighten summary", "Add LinkedIn"]


def test_parse_missing_sections_key() -> None:
    raw = json.dumps({"top_priorities": []})
    result = _parse_review_result(raw)
    assert result.overall_band == "", "nothing was assessed, so there is nothing to aggregate"
    assert result.sections == []
    assert result.top_priorities == []


def test_parse_section_missing_optional_fields() -> None:
    raw = json.dumps(
        {
            "sections": [{"section": "skills", "band": "adequate"}],
        }
    )
    result = _parse_review_result(raw)
    assert result.sections[0].strengths == []
    assert result.sections[0].weaknesses == []
    assert result.sections[0].suggestions == []


def test_parse_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_review_result("not valid json")


def test_parse_normalises_band_case_and_padding() -> None:
    raw = json.dumps({"sections": [{"section": "work", "band": "  Needs Work "}]})
    result = _parse_review_result(raw)
    assert result.sections[0].band == "needs work"


def test_parse_keeps_an_off_rubric_band_verbatim() -> None:
    """Coercing it would hide a model answering outside the rubric."""
    raw = json.dumps({"sections": [{"section": "work", "band": "excellent"}]})
    result = _parse_review_result(raw)
    assert result.sections[0].band == "excellent"


def test_overall_band_is_the_worst_section() -> None:
    raw = json.dumps(
        {
            "sections": [
                {"section": "work", "band": "strong"},
                {"section": "skills", "band": "needs work"},
                {"section": "education", "band": "adequate"},
            ]
        }
    )
    assert _parse_review_result(raw).overall_band == "needs work"


def test_an_off_rubric_band_does_not_drag_the_aggregate_down() -> None:
    raw = json.dumps(
        {
            "sections": [
                {"section": "work", "band": "adequate"},
                {"section": "skills", "band": "sublime"},
            ]
        }
    )
    assert _parse_review_result(raw).overall_band == "adequate"


# ---------------------------------------------------------------------------
# _build_review_prompt
# ---------------------------------------------------------------------------


def test_prompt_contains_cv_text() -> None:
    prompt = _build_review_prompt("Jane Doe | Senior Engineer", ["work", "skills"], default_pack())
    assert "Jane Doe | Senior Engineer" in prompt


def test_prompt_contains_sections_list() -> None:
    prompt = _build_review_prompt("cv text", ["education", "projects"], default_pack())
    assert "education" in prompt
    assert "projects" in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_review_prompt("cv text", ["work"], default_pack())
    assert "sections" in prompt
    assert "top_priorities" in prompt
    assert "overall_score" not in prompt, "the aggregate is cvloom's to compute"


def test_prompt_states_what_each_band_means() -> None:
    """A relabelled score is still unanchored; the criteria are what changed."""
    prompt = _build_review_prompt("cv text", ["work"], default_pack())
    for band in ("strong", "adequate", "needs work"):
        assert f'"{band}"' in prompt
    assert "would cost an interview" in prompt


def test_prompt_asks_for_at_most_three_points_per_section() -> None:
    prompt = _build_review_prompt("cv text", ["work"], default_pack())
    assert "At most 3 items in each of strengths, weaknesses and suggestions" in prompt
    assert "not three padded ones" in prompt, "the cap must not read as a quota"


def test_parse_truncates_a_model_that_ignores_the_cap() -> None:
    """The instruction alone is unenforceable, and an unbounded section buries
    top_priorities under it."""
    raw = json.dumps(
        {
            "sections": [
                {
                    "section": "work",
                    "band": "adequate",
                    "strengths": [f"s{i}" for i in range(9)],
                    "weaknesses": [f"w{i}" for i in range(5)],
                    "suggestions": [f"g{i}" for i in range(4)],
                }
            ],
            "top_priorities": ["p1"],
        }
    )
    section = _parse_review_result(raw).sections[0]
    assert section.strengths == ["s0", "s1", "s2"], "keeps the model's own ordering"
    assert len(section.weaknesses) == 3
    assert len(section.suggestions) == 3
