"""Tests for cvloom.ai.cover — parsing and prompt logic only."""

from __future__ import annotations

import json

import pytest

from cvloom.ai.cover import _build_cover_prompt, _parse_cover_result
from cvloom.locale import default_pack

# ---------------------------------------------------------------------------
# _parse_cover_result
# ---------------------------------------------------------------------------


def test_parse_valid_json() -> None:
    raw = json.dumps(
        {
            "letter": "Dear Hiring Manager,\n\nI am writing to apply...",
            "word_count": 120,
            "key_alignments": ["5 years Python", "distributed systems experience"],
        }
    )
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
    prompt = _build_cover_prompt(
        "Jane Doe | Senior Engineer", "We need a backend engineer.", {}, default_pack()
    )
    assert "Jane Doe | Senior Engineer" in prompt


def test_prompt_contains_jd_text() -> None:
    prompt = _build_cover_prompt("cv text", "We need a backend engineer.", {}, default_pack())
    assert "We need a backend engineer." in prompt


def test_prompt_contains_schema_keys() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {}, default_pack())
    assert "letter" in prompt
    assert "word_count" in prompt
    assert "key_alignments" in prompt


def test_prompt_includes_job_context_when_present() -> None:
    job_context = {"company": "Stripe", "role": "Senior Engineer", "hiring_manager": "Jane Smith"}
    prompt = _build_cover_prompt("cv text", "jd text", job_context, default_pack())
    assert "Stripe" in prompt
    assert "Senior Engineer" in prompt
    assert "Jane Smith" in prompt


def test_prompt_excludes_job_context_block_when_empty() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {}, default_pack())
    assert "<job_context>" not in prompt


def test_prompt_partial_job_context_omits_missing_fields() -> None:
    prompt = _build_cover_prompt("cv text", "jd text", {"company": "Acme"}, default_pack())
    block = prompt[prompt.index("<job_context>") : prompt.index("</job_context>")]
    assert "Acme" in block
    # Scoped to the block on purpose: the pack's fallback salutee names a hiring
    # manager in the salutation instruction, which is not this test's subject.
    assert "Hiring Manager" not in block


# ---------------------------------------------------------------------------
# body_only
# ---------------------------------------------------------------------------


def _instruction(prompt: str) -> str:
    """The instruction half — everything before the first context block."""
    return prompt[: prompt.index("<cv>")]


def test_body_only_drops_the_furniture_instruction() -> None:
    pack = default_pack()
    prompt = _build_cover_prompt("cv", "jd", {}, pack, body_only=True)
    instruction = _instruction(prompt)
    assert pack.cover_letter["greeting"] not in instruction
    assert pack.cover_letter["closing"] not in instruction
    assert pack.cover_letter["fallback_salutee"] not in instruction


def test_body_only_says_the_document_supplies_the_furniture() -> None:
    prompt = _build_cover_prompt("cv", "jd", {}, default_pack(), body_only=True)
    instruction = _instruction(prompt).lower()
    for banned in ("salutation", "closing", "signature", "date"):
        assert f"no {banned}" in instruction


def test_body_only_also_rules_out_a_heading() -> None:
    """A live qwen2.5:3b run opened with `**Cover Letter for the Position of…**`.
    Not a salutation, so the original enumeration let it through — and it renders
    inside the letter's body, below the greeting the template already wrote."""
    prompt = _build_cover_prompt("cv", "jd", {}, default_pack(), body_only=True)
    assert "no title or heading" in _instruction(prompt).lower()


def test_body_only_keeps_the_job_context_block() -> None:
    # The template still builds its greeting from hiring_manager, so dropping the
    # furniture instruction must not drop the facts the letter argues from.
    prompt = _build_cover_prompt(
        "cv",
        "jd",
        {"company": "Acme", "hiring_manager": "Dana Reyes"},
        default_pack(),
        body_only=True,
    )
    block = prompt[prompt.index("<job_context>") : prompt.index("</job_context>")]
    assert "Acme" in block
    assert "Dana Reyes" in block


def test_full_letter_remains_the_default() -> None:
    pack = default_pack()
    prompt = _build_cover_prompt("cv", "jd", {}, pack)
    assert pack.cover_letter["greeting"] in prompt
    assert pack.cover_letter["closing"] in prompt
