"""Result dataclasses for AI-powered analysis features."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SectionScore:
    section: str
    score: float
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    overall_score: float
    sections: list[SectionScore] = field(default_factory=list)
    top_priorities: list[str] = field(default_factory=list)


@dataclass
class CoverResult:
    letter: str
    word_count: int
    key_alignments: list[str] = field(default_factory=list)


@dataclass
class Suggestion:
    section: str
    entry: str | None
    type: str
    current: str | None
    suggested: str
    rationale: str


@dataclass
class SuggestResult:
    suggestions: list[Suggestion] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    summary: str = ""
