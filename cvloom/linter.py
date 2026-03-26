"""ATS linter — rule-based checks for CV content quality."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cvloom.models import ResolvedProfile

# ── Data structures ─────────────────────────────────────────────────


@dataclass
class LintFinding:
    """A single linter finding tied to a specific location in the CV."""

    rule_id: str
    severity: str  # "warning" | "error"
    section: str
    entry: str
    bullet_index: int | None
    bullet_text: str | None
    message: str
    fix_hint: str


@dataclass
class LintRule:
    """A registered lint rule."""

    rule_id: str
    name: str
    description: str
    check: Callable[[ResolvedProfile], list[LintFinding]]


# ── Built-in rules ──────────────────────────────────────────────────

# Common passive voice constructions (auxiliary + past participle pattern).
_PASSIVE_RE = re.compile(
    r"\b(?:was|were|been|being|is|are)\s+"
    r"(?:also\s+)?"
    r"([a-z]+(?:ed|en|wn|lt|ht|pt|nt))\b",
    re.IGNORECASE,
)

# Words that match the passive participle pattern but are adjectives/non-participles.
_PASSIVE_FALSE_POSITIVES = {
    "present", "recent", "absent", "current", "different", "important", "efficient",
    "excellent", "sufficient", "consistent", "persistent", "resilient", "intelligent",
    "confident", "competent", "relevant", "elegant", "frequent", "urgent", "ancient",
    "silent", "content", "evident", "dependent", "independent", "spent", "sent", "went",
    "bent", "lent", "meant", "dealt", "felt", "built", "knelt", "prevalent", "prominent",
    "transparent", "coherent", "concurrent", "existent", "inherent", "latent", "potent",
    "reluctant", "apparent", "brilliant", "compliant", "diligent", "proficient",
    "sufficient", "emergent", "equivalent", "fluent",
}

_WEAK_OPENERS = [
    "helped",
    "assisted",
    "worked on",
    "was responsible for",
    "participated in",
    "was involved in",
    "contributed to",
]

_NOISE_SKILLS = {
    "microsoft office",
    "microsoft word",
    "microsoft excel",
    "microsoft powerpoint",
    "google docs",
    "google sheets",
    "google slides",
    "ms office",
    "ms word",
}

_MIN_HIGHLIGHT_WORDS = 8
_MAX_HIGHLIGHT_WORDS = 25


def _entry_label(section: str, entry: dict[str, Any]) -> str:
    """Return a human-readable label for an entry."""
    if section == "work":
        return str(entry.get("company", "?"))
    if section == "education":
        return str(entry.get("institution", "?"))
    if section == "projects":
        return str(entry.get("name", "?"))
    return "?"


def _check_highlights(
    resolved: ResolvedProfile,
    section: str,
    rule_id: str,
    test: Callable[[str, int], LintFinding | None],
) -> list[LintFinding]:
    """Run *test* on every highlight in *section*."""
    findings: list[LintFinding] = []
    if not resolved.show_sections.get(section):
        return findings
    for entry in resolved.data.get(section, []):
        for i, hl in enumerate(entry.get("highlights", [])):
            text = hl if isinstance(hl, str) else hl.get("text", "")
            finding = test(text, i)
            if finding:
                finding.section = section
                finding.entry = _entry_label(section, entry)
                finding.bullet_index = i
                finding.bullet_text = text
                findings.append(finding)
    return findings


def _check_passive_voice(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-001: Flag passive voice constructions in highlights."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        match = _PASSIVE_RE.search(text)
        if match and match.group(1).lower() not in _PASSIVE_FALSE_POSITIVES:
            return LintFinding(
                rule_id="ats-001",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f"Passive voice detected: \"{match.group()}\"",
                fix_hint="Rewrite using an active verb (e.g. 'Designed', 'Built', 'Led').",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "ats-001", test))
    return findings


def _check_missing_quantification(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-002: Flag highlights without any numbers."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        if not re.search(r"\d+", text):
            return LintFinding(
                rule_id="ats-002",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message="No quantification found in this highlight.",
                fix_hint="Add metrics: percentages, counts, dollar amounts, or time saved.",
            )
        return None

    for section in ("work", "projects"):
        findings.extend(_check_highlights(resolved, section, "ats-002", test))
    return findings


def _check_noise_skills(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-003: Flag low-value 'noise' skills."""
    findings: list[LintFinding] = []
    if not resolved.show_sections.get("skills"):
        return findings

    for group in resolved.data.get("skills", []):
        category = group.get("category", "?")
        for item in group.get("items", []):
            name = item if isinstance(item, str) else item.get("name", "")
            if name.lower() in _NOISE_SKILLS:
                findings.append(LintFinding(
                    rule_id="ats-003",
                    severity="warning",
                    section="skills",
                    entry=category,
                    bullet_index=None,
                    bullet_text=None,
                    message=f"\"{name}\" is considered a noise skill by most ATS reviewers.",
                    fix_hint="Remove it or replace with a more specific/valuable skill.",
                ))
    return findings


def _check_weak_action_verbs(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-004: Flag highlights starting with weak action verbs."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        lower = text.lower().lstrip("- ").strip()
        for weak in _WEAK_OPENERS:
            if lower.startswith(weak):
                return LintFinding(
                    rule_id="ats-004",
                    severity="warning",
                    section="",
                    entry="",
                    bullet_index=idx,
                    bullet_text=text,
                    message=f"Weak opener: \"{weak}\".",
                    fix_hint="Start with a strong action verb: 'Designed', 'Implemented', "
                             "'Reduced', 'Delivered', 'Architected'.",
                )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "ats-004", test))
    return findings


def _check_highlight_length(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-005: Flag highlights that are too short or too long."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        word_count = len(text.split())
        if word_count < _MIN_HIGHLIGHT_WORDS:
            return LintFinding(
                rule_id="ats-005",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f"Highlight too short ({word_count} words, min {_MIN_HIGHLIGHT_WORDS}).",
                fix_hint="Add context, impact, or metrics to make this bullet more substantial.",
            )
        if word_count > _MAX_HIGHLIGHT_WORDS:
            return LintFinding(
                rule_id="ats-005",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f"Highlight too long ({word_count} words, maximum {_MAX_HIGHLIGHT_WORDS}).",
                fix_hint="Split into two bullets or tighten the language.",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "ats-005", test))
    return findings


# ── Rule registry ───────────────────────────────────────────────────

RULES: list[LintRule] = [
    LintRule(
        "ats-001", "passive-voice",
        "Flag passive voice in highlights", _check_passive_voice,
    ),
    LintRule(
        "ats-002", "missing-quantification",
        "Flag highlights without numbers", _check_missing_quantification,
    ),
    LintRule(
        "ats-003", "noise-skills",
        "Flag low-value skills", _check_noise_skills,
    ),
    LintRule(
        "ats-004", "weak-action-verbs",
        "Flag weak opening verbs", _check_weak_action_verbs,
    ),
    LintRule(
        "ats-005", "highlight-length",
        "Flag too-short or too-long highlights", _check_highlight_length,
    ),
]


# ── Public API ──────────────────────────────────────────────────────


def lint(
    resolved: ResolvedProfile,
    rule_ids: list[str] | None = None,
) -> list[LintFinding]:
    """Run lint rules against *resolved* profile data.

    If *rule_ids* is given, only those rules are executed.
    """
    findings: list[LintFinding] = []
    for rule in RULES:
        if rule_ids and rule.rule_id not in rule_ids:
            continue
        findings.extend(rule.check(resolved))
    return findings
