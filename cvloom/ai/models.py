"""Result dataclasses for AI-powered analysis features.

Two fields recur across these types and are worth explaining once.

``related_findings`` lets an item cite the deterministic lint rule it resolves, so
a suggestion can be traced back to the `cvloom check` output the user has already
seen. Parsers deliberately do **not** filter out unknown rule ids: silently
dropping one hides a model that is making them up, whereas a rendered id absent
from `cvloom check` is a visible symptom the user can report.

``context_notes`` carries what the AI layer had to give up to fit the model's
context — shed lint findings, a coarser analysis block. It is a field rather than
a `ResolvedProfile.warnings` entry because the CLI emits those inside `_resolve`,
before the AI call is made, so anything appended afterwards is never printed.

Both are last and defaulted on every type that has them, which keeps positional
construction working and lets `dataclasses.asdict` carry them to the MCP tools
with no further plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SectionAssessment:
    section: str
    band: str
    """One of `prompts.BANDS`, though an off-rubric label the model returned is
    kept verbatim rather than coerced — same reasoning as `related_findings`."""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    related_findings: list[str] = field(default_factory=list)
    """Section-level, not per-strength: citing each item individually would mean
    turning these plain lists into dataclasses."""


@dataclass
class ReviewResult:
    overall_band: str
    """The worst band across `sections`, computed by cvloom rather than asked of
    the model — a model asked to aggregate its own answer is doing arithmetic it
    has no better view of than the caller does."""

    sections: list[SectionAssessment] = field(default_factory=list)
    top_priorities: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)


@dataclass
class CoverResult:
    letter: str
    word_count: int
    key_alignments: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)
    body_only: bool = False
    """Whether ``letter`` is body paragraphs alone, for a ``cover-letter/*``
    template's ``job_context.notes``, rather than a letter with its own greeting
    and sign-off. A consumer cannot tell the two apart from the prose."""


@dataclass
class Suggestion:
    section: str
    entry: str | None
    type: str
    current: str | None
    suggested: str
    rationale: str
    related_findings: list[str] = field(default_factory=list)


@dataclass
class SuggestResult:
    suggestions: list[Suggestion] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    summary: str = ""
    context_notes: list[str] = field(default_factory=list)


@dataclass
class AlignResult:
    alignment_band: str
    """Asked of the model, unlike `ReviewResult.overall_band`: alignment has no
    per-section members to aggregate, so there is nothing to derive it from."""

    narrative: str
    repositioning: list[str] = field(default_factory=list)
    tone_gaps: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)
