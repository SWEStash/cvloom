"""Binary checks on what a model actually returned.

Each rubric returns ``None`` when the output passes and a short reason when it
does not, so a failing evaluation run names the defect instead of printing
``False``. They are pure functions over a result and its inputs, which is what
lets `tests/test_ai_rubrics.py` cover them offline while the suite that *calls*
them needs a live backend.

Reference-free by construction. There is no labelled corpus of good CV feedback
and building one would be a research project, so every check here asks whether
the output is self-consistent with its own inputs — is it in the right language,
does every number trace to the CV, does it cite a rule that exists. That is a
weaker question than "is this good advice", and it is the one that can be
answered honestly without ground truth.
"""

from __future__ import annotations

import re

from cvloom import sections
from cvloom.models import ResolvedProfile
from tests.test_ai_grounding import ungrounded_numbers

# High-frequency function words. Content words are cognates often enough
# ("implementar"/"implement") that they identify the CV's subject rather than its
# language; function words are what actually differ, and they are frequent enough
# that a paragraph of either language carries several.
_MARKERS = {
    "en": {"the", "and", "of", "to", "is", "with", "for", "your", "that", "this"},
    "es": {"de", "la", "el", "que", "en", "los", "para", "con", "una", "su"},
}

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def language_of(text: str) -> str | None:
    """Which language's function words dominate *text*, or None if neither does.

    Deliberately a word-count heuristic rather than a dependency: the question is
    "did a model told to answer in Spanish answer in English", which is a gross
    difference. A tie or a near-empty string returns None rather than guessing.
    """
    words = [word.lower() for word in _WORD.findall(text)]
    if len(words) < 12:
        return None
    hits = {code: sum(word in markers for word in words) for code, markers in _MARKERS.items()}
    best, runner_up = sorted(hits.values(), reverse=True)[:2]
    if best == 0 or best < runner_up * 2:
        return None
    return max(hits, key=lambda code: hits[code])


def answers_in(text: str, expected: str) -> str | None:
    """The response language matches the project's locale."""
    found = language_of(text)
    if found is None or found == expected:
        # None is not a failure: a short reply has too few function words to judge,
        # and asserting on a guess would make the pass rate noise.
        return None
    return f"answered in {found}, expected {expected}"


def invents_no_numbers(generated: str, *sources: str) -> str | None:
    """Every figure traces back to something the model was actually given.

    The highest-harm failure in the whole layer: the user pastes an invented
    metric into a real CV and is asked about it in an interview.

    *sources* is every block the prompt carried, not only the CV, and getting
    that wrong manufactures failures. `review` and `suggest` are handed the
    analysis block, so "trim this to under 20 words" cites a lint threshold from
    their own context — grading it against the CV alone reports an invented `20`.
    `cover` and `align` additionally hold the job description, whose numbers the
    model is meant to engage with.
    """
    invented = ungrounded_numbers(generated, " ".join(sources))
    return f"invented figures: {sorted(invented)}" if invented else None


def cites_a_real_rule(cited: list[list[str]], analysis: str) -> str | None:
    """At least one item cites a rule id that is actually in the analysis block.

    Proof that the deterministic context was read rather than ignored. Citing
    nothing is allowed per item — the prompt says so — so this asks only that the
    whole response cites something real somewhere.
    """
    flat = [rule for group in cited for rule in group]
    if not flat:
        return "cited no rule ids at all"
    unknown = [rule for rule in flat if rule not in analysis]
    if len(unknown) == len(flat):
        return f"every cited id is absent from <analysis>: {sorted(set(unknown))}"
    return None


def _labels(resolved: ResolvedProfile) -> list[str]:
    found = []
    for section in sections.SECTIONS:
        for entry in resolved.data.get(section.name) or []:
            label = sections.entry_label(section.name, entry)
            if label and label != "?":
                found.append(f"{section.name}/{label}")
    return found


def leaks_no_analysis_labels(generated: str, resolved: ResolvedProfile) -> str | None:
    """No `section/entry` label from the analysis block appears in the prose.

    A live run emitted `[work/Acme Corp]` into a cover letter as though it were a
    placeholder to fill in. Nothing else catches that: the text is grounded, in
    the right language, and structurally valid — it is just addressed to the wrong
    reader.
    """
    squashed = re.sub(r"\s*/\s*", "/", generated)
    leaked = [label for label in _labels(resolved) if label in squashed]
    return f"analysis labels in the output: {sorted(set(leaked))}" if leaked else None


def reports_unusable_input(prose: str, items: list[object]) -> str | None:
    """An empty or wrong input is named as such rather than analysed.

    The prompts ask for exactly this, and it is the instruction a confident model
    is worst at following — inventing an analysis of nothing is the confabulation
    the grounding contract exists to prevent.
    """
    if not prose.strip():
        return "said nothing at all, rather than reporting the input as unusable"
    if items:
        # Deliberately not softened when the prose *does* name the problem. The
        # prompt asks for both halves — say so, and return empty lists — and a
        # model that says "this CV is nearly empty" while still emitting an
        # assessment is half-complying. Telling that apart from silent
        # confabulation needs a reader, which is what the echoed sample is for.
        return f"returned {len(items)} item(s); the prompt asks for empty lists here"
    return None


_RESTATEMENT = re.compile(r"\s+")


def restates_verbatim(generated: list[str], messages: list[str]) -> str | None:
    """Whether the model handed a lint finding's own wording back.

    Measured, never gated. The prompt asks the model not to repeat findings the
    user has already seen from `cvloom check`, and small models ignore that
    reliably enough that a gate here would be red forever — which would say more
    about the model than about the prompt.
    """

    def norm(text: str) -> str:
        return _RESTATEMENT.sub(" ", text).strip().lower().rstrip(".")

    seen = {norm(message) for message in messages}
    repeated = [item for item in generated if norm(item) in seen]
    return f"restated {len(repeated)} finding(s) verbatim" if repeated else None
