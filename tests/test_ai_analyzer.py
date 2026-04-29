"""Tests for cvloom.ai.analyzer — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.analyzer import _build_review_prompt, _parse_review_result


# ---------------------------------------------------------------------------
# _parse_review_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps({
        "overall_score": 7.5,
        "sections": [
            {
                "section": "work",
                "score": 8.0,
                "strengths": ["Good metrics"],
                "weaknesses": ["Too verbose"],
                "suggestions": ["Add more numbers"],
            }
        ],
        "top_priorities": ["Quantify impact", "Tighten summary", "Add LinkedIn"],
    })
    result = _parse_review_result(raw)
    assert result.overall_score == 7.5
    assert len(result.sections) == 1
    assert result.sections[0].section == "work"
    assert result.sections[0].score == 8.0
    assert result.sections[0].strengths == ["Good metrics"]
    assert result.sections[0].weaknesses == ["Too verbose"]
    assert result.sections[0].suggestions == ["Add more numbers"]
    assert result.top_priorities == ["Quantify impact", "Tighten summary", "Add LinkedIn"]


def test_parse_missing_sections_key() -> None:
    raw = json.dumps({"overall_score": 5.0})
    result = _parse_review_result(raw)
    assert result.overall_score == 5.0
    assert result.sections == []
    assert result.top_priorities == []


def test_parse_section_missing_optional_fields() -> None:
    raw = json.dumps({
        "overall_score": 6.0,
        "sections": [{"section": "skills", "score": 6}],
    })
    result = _parse_review_result(raw)
    assert result.sections[0].strengths == []
    assert result.sections[0].weaknesses == []
    assert result.sections[0].suggestions == []


def test_parse_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_review_result("not valid json")


def test_parse_score_coerced_to_float() -> None:
    raw = json.dumps({
        "overall_score": 8,
        "sections": [{"section": "work", "score": 9}],
    })
    result = _parse_review_result(raw)
    assert isinstance(result.overall_score, float)
    assert isinstance(result.sections[0].score, float)
    assert result.sections[0].score == 9.0


# ---------------------------------------------------------------------------
# _build_review_prompt
# ---------------------------------------------------------------------------


def test_prompt_contains_cv_text() -> None:
    prompt = _build_review_prompt("Jane Doe | Senior Engineer", ["work", "skills"])
    assert "Jane Doe | Senior Engineer" in prompt


def test_prompt_contains_sections_list() -> None:
    prompt = _build_review_prompt("cv text", ["education", "projects"])
    assert "education" in prompt
    assert "projects" in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_review_prompt("cv text", ["work"])
    assert "overall_score" in prompt
    assert "sections" in prompt
    assert "top_priorities" in prompt
