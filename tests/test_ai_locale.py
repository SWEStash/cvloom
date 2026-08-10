"""Every AI prompt names the language the answer must be written in.

The prompt-side analogue of ``test_locale_qa.py``, which brackets a pseudo-locale
through the templates and so covers the rendered document only. Nothing there can
notice that a project declaring ``locale: es`` gets English feedback and an English
cover letter — the AI layer has no template to render.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from cvloom.ai.align import _build_align_prompt
from cvloom.ai.analyzer import _build_review_prompt
from cvloom.ai.cover import _build_cover_prompt
from cvloom.ai.prompts import locale_context_block
from cvloom.ai.suggest import _build_suggest_prompt
from cvloom.locale import LocalePack, load_pack
from cvloom.match import KeywordMatch, MatchReport

_CV = "Jane Doe | Senior Engineer"
_JD = "We need a Python developer."

_LOCALES = ["en", "es"]


def _pack(code: str) -> LocalePack:
    pack, _ = load_pack(code)
    return pack


def _match_report() -> MatchReport:
    return MatchReport(
        matched=[KeywordMatch(keyword="python", found_in=["skills"], frequency_jd=3)],
        gaps=["kubernetes"],
        jd_word_count=300,
        cv_keywords_coverage=0.65,
    )


def _prompts(pack: LocalePack) -> dict[str, str]:
    return {
        "review": _build_review_prompt(_CV, ["work"], pack),
        "suggest": _build_suggest_prompt(_CV, ["work"], "Senior Backend Engineer", pack),
        "align": _build_align_prompt(_CV, _JD, _match_report(), pack),
        "cover": _build_cover_prompt(_CV, _JD, {"company": "Acme"}, pack),
    }


@pytest.mark.parametrize("code", _LOCALES)
@pytest.mark.parametrize("command", ["review", "suggest", "align", "cover"])
def test_every_command_states_the_language_to_answer_in(command: str, code: str) -> None:
    prompt = _prompts(_pack(code))[command]
    assert "<locale>" in prompt
    assert f"({code})" in prompt


def test_the_language_is_named_not_only_coded() -> None:
    """A code alone is a weaker instruction than a name a model has seen in training."""
    assert "English" in locale_context_block(_pack("en"))
    assert "Spanish" in locale_context_block(_pack("es"))


def test_an_unknown_locale_degrades_to_naming_its_code() -> None:
    """A user-supplied pack still gets a usable instruction, not a blank one."""
    block = locale_context_block(replace(_pack("en"), code="de"))
    assert "the language with code 'de'" in block


@pytest.mark.parametrize("code", _LOCALES)
@pytest.mark.parametrize("command", ["review", "suggest", "align", "cover"])
def test_machine_read_strings_are_exempted_from_translation(command: str, code: str) -> None:
    """Without this clause a Spanish run returns ``"type": "viñeta"`` and the CLI's
    colour map falls through on every suggestion — a locale instruction that breaks
    the terminal output it was meant to improve."""
    prompt = _prompts(_pack(code))[command]
    assert "JSON keys, section names and enum values stay in English" in prompt


@pytest.mark.parametrize("code", _LOCALES)
def test_the_cover_letter_uses_the_packs_own_furniture(code: str) -> None:
    """The template builds its salutation and sign-off from these same three strings,
    so an AI letter that invents its own cannot be pasted alongside a rendered one."""
    pack = _pack(code)
    prompt = _prompts(pack)["cover"]
    assert pack.cover_letter["greeting"] in prompt
    assert pack.cover_letter["closing"] in prompt
    assert pack.cover_letter["fallback_salutee"] in prompt


def test_a_named_hiring_manager_replaces_the_fallback_salutee() -> None:
    pack = _pack("es")
    prompt = _build_cover_prompt(_CV, _JD, {"hiring_manager": "Ana Ruiz"}, pack)
    assert f"{pack.cover_letter['greeting']} Ana Ruiz," in prompt
    assert pack.cover_letter["fallback_salutee"] not in prompt


def test_a_profile_can_override_the_greeting_as_the_template_allows() -> None:
    """``job_context.greeting`` exists because Spanish agrees with the recipient;
    the AI path must honour the same override the template does."""
    prompt = _build_cover_prompt(
        _CV, _JD, {"greeting": "Estimada", "closing": "Un saludo,"}, _pack("es")
    )
    assert "Estimada" in prompt
    assert "Un saludo," in prompt
