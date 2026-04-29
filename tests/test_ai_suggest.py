"""Tests for cvloom.ai.suggest — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.suggest import _build_suggest_prompt, _parse_suggest_result


# ---------------------------------------------------------------------------
# _parse_suggest_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps({
        "suggestions": [
            {
                "section": "work",
                "entry": "Acme Corp",
                "type": "bullet",
                "current": None,
                "suggested": "Reduced API latency by 40% via connection pooling",
                "rationale": "Adds a measurable impact metric to the role",
            }
        ],
        "missing_skills": ["Kubernetes", "Terraform"],
        "summary": "Focus on quantifying achievements and adding cloud skills.",
    })
    result = _parse_suggest_result(raw)
    assert len(result.suggestions) == 1
    s = result.suggestions[0]
    assert s.section == "work"
    assert s.entry == "Acme Corp"
    assert s.type == "bullet"
    assert s.current is None
    assert "latency" in s.suggested
    assert result.missing_skills == ["Kubernetes", "Terraform"]
    assert "quantifying" in result.summary


def test_parse_missing_optional_fields() -> None:
    raw = json.dumps({})
    result = _parse_suggest_result(raw)
    assert result.suggestions == []
    assert result.missing_skills == []
    assert result.summary == ""


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_suggest_result("not valid json")


def test_parse_suggestion_null_entry_and_current() -> None:
    raw = json.dumps({
        "suggestions": [
            {
                "section": "skills",
                "entry": None,
                "type": "skill",
                "current": None,
                "suggested": "Docker",
                "rationale": "Widely required in the target role",
            }
        ]
    })
    result = _parse_suggest_result(raw)
    assert result.suggestions[0].entry is None
    assert result.suggestions[0].current is None


# ---------------------------------------------------------------------------
# _build_suggest_prompt
# ---------------------------------------------------------------------------


def test_prompt_contains_cv_text() -> None:
    prompt = _build_suggest_prompt("Jane Doe | Backend Engineer", ["work", "skills"], "")
    assert "Jane Doe | Backend Engineer" in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_suggest_prompt("cv text", ["work"], "")
    assert "section" in prompt
    assert "suggested" in prompt
    assert "rationale" in prompt
    assert "missing_skills" in prompt


def test_prompt_includes_role_when_provided() -> None:
    prompt = _build_suggest_prompt("cv text", ["work"], "Senior Backend Engineer")
    assert "Senior Backend Engineer" in prompt
    assert "<target_role>" in prompt


def test_prompt_excludes_role_block_when_empty() -> None:
    prompt = _build_suggest_prompt("cv text", ["work"], "")
    assert "<target_role>" not in prompt
