"""Each prompt's JSON schema, checked against the dataclass that parses it.

All four AI commands build their response schema by concatenating string literals,
so nothing but a reader's attention keeps `cvloom/ai/models.py` and the prompt in
step. The per-command `test_prompt_contains_schema_keys` tests assert hardcoded
substrings against the whole prompt, which is both loose and one-directional: they
pass on a dataclass field the schema never learned about, and they pass on a schema
key nothing reads back.

This compares the two in both directions, deriving each side from its own source —
the keys from the built prompt, the fields from `dataclasses.fields()`. Restating a
key list here would only move the drift one file over.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from typing import Any, get_args, get_type_hints

import pytest

from cvloom.ai.align import _build_align_prompt
from cvloom.ai.analyzer import _build_review_prompt
from cvloom.ai.cover import _build_cover_prompt
from cvloom.ai.models import AlignResult, CoverResult, ReviewResult, SuggestResult
from cvloom.ai.suggest import _build_suggest_prompt
from cvloom.locale import default_pack
from cvloom.match import KeywordMatch, MatchReport

_SCHEMA_MARKER = "matching this schema exactly:\n"

_KEY = re.compile(r'"([a-z_]+)":')

_FILLED_AFTER_PARSING: dict[type, frozenset[str]] = {
    ReviewResult: frozenset({"context_notes", "overall_band"}),
    CoverResult: frozenset({"context_notes", "body_only"}),
    SuggestResult: frozenset({"context_notes"}),
    AlignResult: frozenset({"context_notes"}),
}
"""Fields cvloom sets itself, so they are absent from the prompt by design.

`context_notes` reports what the AI layer had to shed to fit the context, and
`body_only` records which of two shapes the caller asked for — neither is
knowledge the model has. `overall_band` is the worst band across the sections the
model did answer for, so asking would be asking it to aggregate its own reply.

`related_findings` is deliberately *not* here: both `review` and `suggest` ask for
it, and both parsers read it back. Nor is `AlignResult.alignment_band`, which has
no members to aggregate and so must come from the model.
"""


def _schema_block(prompt: str) -> str:
    """Slice the brace-delimited schema out of a built prompt.

    Sliced rather than parsed: the block is not valid JSON, since its values are
    angle-bracket type descriptions (`<float 1.0-10.0>`) and its arrays trail an
    ellipsis. Slicing also keeps surrounding prose out of the key set — `cover`
    goes on to name `word_count` in a sentence about the length cap.
    """
    start = prompt.index(_SCHEMA_MARKER) + len(_SCHEMA_MARKER)
    assert prompt[start] == "{", "the schema no longer opens on the line after the marker"
    depth = 0
    for offset, char in enumerate(prompt[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return prompt[start : offset + 1]
    raise AssertionError("unbalanced braces in the schema block")


def _prompt_keys(prompt: str) -> set[str]:
    keys = {match.group(1) for match in _KEY.finditer(_schema_block(prompt))}
    assert keys, "no keys found — the extractor has stopped matching the schema's shape"
    return keys


def _nested(annotation: Any) -> type | None:
    """The dataclass inside `list[Foo]`, if there is one."""
    for arg in get_args(annotation):
        if is_dataclass(arg):
            return arg  # type: ignore[return-value]
    return None


def _result_keys(cls: type) -> set[str]:
    """Every key the model is asked for, walking into nested result types.

    A nested field contributes its own name too — `sections` is both a
    `ReviewResult` field and a key in the schema. Annotations are resolved with
    `get_type_hints` because `models.py` defers them, so `Field.type` is a string.
    """
    hints = get_type_hints(cls)
    excluded = _FILLED_AFTER_PARSING.get(cls, frozenset())
    names: set[str] = set()
    for spec in fields(cls):
        if spec.name in excluded:
            continue
        names.add(spec.name)
        nested = _nested(hints[spec.name])
        if nested is not None:
            names |= _result_keys(nested)
    return names


def _match_report() -> MatchReport:
    return MatchReport(
        matched=[KeywordMatch(keyword="python", found_in=["skills"], frequency_jd=3)],
        gaps=["kubernetes"],
        jd_word_count=300,
        cv_keywords_coverage=0.65,
        reorder_hints=[],
    )


def _review_prompt() -> str:
    return _build_review_prompt("cv text", ["work"], default_pack())


def _suggest_prompt() -> str:
    return _build_suggest_prompt("cv text", ["work"], "", default_pack())


def _align_prompt() -> str:
    return _build_align_prompt("cv text", "jd text", _match_report(), default_pack())


def _cover_prompt() -> str:
    return _build_cover_prompt("cv text", "jd text", {}, default_pack())


_COMMANDS = [
    pytest.param(_review_prompt, ReviewResult, id="review"),
    pytest.param(_suggest_prompt, SuggestResult, id="suggest"),
    pytest.param(_align_prompt, AlignResult, id="align"),
    pytest.param(_cover_prompt, CoverResult, id="cover"),
]


@pytest.mark.parametrize(("build", "result_type"), _COMMANDS)
def test_every_result_field_is_asked_for(build: Any, result_type: type) -> None:
    missing = _result_keys(result_type) - _prompt_keys(build())
    assert not missing, (
        f"{result_type.__name__} declares {sorted(missing)}, which the prompt never asks "
        "for. Add it to the schema, or to _FILLED_AFTER_PARSING if cvloom sets it."
    )


@pytest.mark.parametrize(("build", "result_type"), _COMMANDS)
def test_every_schema_key_has_a_field(build: Any, result_type: type) -> None:
    unread = _prompt_keys(build()) - _result_keys(result_type)
    assert not unread, (
        f"the prompt asks for {sorted(unread)}, which {result_type.__name__} has no field "
        "for. The model's answer would be parsed and discarded."
    )
