"""Tests for cvloom.ai.cover — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.cover import _build_cover_prompt, _parse_cover_result


# ---------------------------------------------------------------------------
# _parse_cover_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps({
        "letter": "Dear Hiring Manager,\n\nI am writing to apply...",
        "word_count": 120,
        "key_alignments": ["5 years Python", "distributed systems experience"],
    })
    result = _parse_cover_result(raw)
    assert result.letter == "Dear Hiring Manager,\n\nI am writing to apply..."
    assert result.word_count == 120
    assert result.key_alignments == ["5 years Python", "distributed systems experience"]


def test_parse_missing_key_alignments() -> None:
    raw = json.dumps({"letter": "Hello world", "word_count": 2})
    result = _parse_cover_result(raw)
    assert result.key_alignments == []


def test_parse_missing_word_count_falls_back_to_split() -> None:
    letter = "one two three four five"
    raw = json.dumps({"letter": letter})
    result = _parse_cover_result(raw)
    assert result.word_count == 5


def test_parse_zero_word_count_falls_back_to_split() -> None:
    letter = "one two three"
    raw = json.dumps({"letter": letter, "word_count": 0})
    result = _parse_cover_result(raw)
    assert result.word_count == 3


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_cover_result("not valid json")


# ---------------------------------------------------------------------------
# _build_cover_prompt
# ---------------------------------------------------------------------------


def test_prompt_contains_cv_text() -> None:
    prompt = _build_cover_prompt("Jane Doe | Senior Engineer", "We need a backend engineer.", {})
    assert "Jane Doe | Senior Engineer" in prompt


def test_prompt_contains_jd_text() -> None:
    prompt = _build_cover_prompt("cv text", "We need a backend engineer.", {})
    assert "We need a backend engineer." in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {})
    assert "letter" in prompt
    assert "word_count" in prompt
    assert "key_alignments" in prompt


def test_prompt_includes_job_context_when_present() -> None:
    job_context = {"company": "Stripe", "role": "Senior Engineer", "hiring_manager": "Jane Smith"}
    prompt = _build_cover_prompt("cv text", "jd text", job_context)
    assert "Stripe" in prompt
    assert "Senior Engineer" in prompt
    assert "Jane Smith" in prompt


def test_prompt_excludes_job_context_block_when_empty() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {})
    assert "<job_context>" not in prompt


def test_prompt_partial_job_context_omits_missing_fields() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {"company": "Acme"})
    assert "Acme" in prompt
    assert "Hiring Manager" not in prompt
