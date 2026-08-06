"""Writing lint — deterministic, rule-based checks for CV writing quality.

Each rule carries a *category* that maps to one of the three honest axes of
"ATS-readiness" (see ``docs/reference/ats-readiness.md``):

- ``writing`` — writing-quality heuristics (voice, verbs, quantification, …).
- ``structure`` — document structure and completeness (bullet/skill counts, …).
- ``ats-parse`` — things that specifically affect ATS parsing / keyword pickup.

There is no single "ATS score"; see the reference doc.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from cvloom import sections
from cvloom.links import network_of, normalize_url
from cvloom.models import ResolvedProfile

# Rule categories — the three honest axes of writing/ATS readiness.
CATEGORY_WRITING = "writing"
CATEGORY_STRUCTURE = "structure"
CATEGORY_ATS_PARSE = "ats-parse"

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
    category: str = ""


@dataclass
class LintRule:
    """A registered lint rule."""

    rule_id: str
    name: str
    description: str
    category: str
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
    "present",
    "recent",
    "absent",
    "current",
    "different",
    "important",
    "efficient",
    "excellent",
    "sufficient",
    "consistent",
    "persistent",
    "resilient",
    "intelligent",
    "confident",
    "competent",
    "relevant",
    "elegant",
    "frequent",
    "urgent",
    "ancient",
    "silent",
    "content",
    "evident",
    "dependent",
    "independent",
    "spent",
    "sent",
    "went",
    "bent",
    "lent",
    "meant",
    "dealt",
    "felt",
    "built",
    "knelt",
    "prevalent",
    "prominent",
    "transparent",
    "coherent",
    "concurrent",
    "existent",
    "inherent",
    "latent",
    "potent",
    "reluctant",
    "apparent",
    "brilliant",
    "compliant",
    "diligent",
    "proficient",
    "sufficient",
    "emergent",
    "equivalent",
    "fluent",
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

# "I" is case-sensitive here: lowercase "i" is never the pronoun, and matching
# it case-insensitively turned every stray initial into a finding.
_FIRST_PERSON_RE = re.compile(r"\b(?:my|me|mine|myself)\b", re.IGNORECASE)
_PRONOUN_I_RE = re.compile(r"\bI\b")

# Present-tense verbs whose -ed ending makes the past-tense heuristic misfire.
_PRESENT_TENSE_ED = frozenset(
    {
        "embed",
        "exceed",
        "proceed",
        "succeed",
        "precede",
        "concede",
        "recede",
        "feed",
        "need",
        "breed",
        "speed",
        "seed",
        "heed",
        "bleed",
        "plead",
        "spread",
        "shed",
    }
)

_VAGUE_BUZZWORDS_RE = re.compile(
    r"\b(?:"
    r"motivated|detail-oriented|team player|hardworking|"
    r"passionate|dynamic|results-driven|go-getter|"
    r"synergy|proactive|self-starter|innovative"
    r")\b",
    re.IGNORECASE,
)

_MIN_BULLETS = 3
_MAX_BULLETS = 8
_MIN_SKILLS = 8
_MAX_SKILLS = 25
# Past this, an education section is almost always a degree list plus a tail of
# short courses/certs, which reads better as a separate certifications section.
_MAX_EDUCATION_ENTRIES = 6
_WORDS_PER_PAGE = 500

from cvloom.trim import MAX_PAGES as _MAX_PAGES  # noqa: E402  (one ceiling, one place)

_DATE_YYYY_MM_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_YYYY_RE = re.compile(r"^\d{4}$")

# Scaffold placeholders such as "[Company Name]" or "[X]%". The negative
# lookahead spares Markdown links, whose "[label](url)" is not a placeholder.
_PLACEHOLDER_RE = re.compile(r"\[[^\][]{1,40}\](?!\()")

_IRREGULAR_PAST = frozenset(
    {
        "led",
        "built",
        "ran",
        "wrote",
        "grew",
        "drove",
        "won",
        "taught",
        "brought",
        "became",
        "came",
        "cut",
        "drew",
        "went",
        "had",
        "held",
        "kept",
        "lost",
        "made",
        "met",
        "paid",
        "put",
        "read",
        "said",
        "sat",
        "sold",
        "took",
        "told",
        "thought",
        "set",
        "got",
        "left",
        "sent",
        "spent",
        "began",
        "broke",
        "chose",
        "found",
        "gave",
        "knew",
        "saw",
        "spoke",
        "stood",
        "wore",
    }
)

_PRESENT_TENSE_VERBS = frozenset(
    {
        "design",
        "develop",
        "build",
        "lead",
        "manage",
        "implement",
        "create",
        "write",
        "run",
        "analyze",
        "architect",
        "deploy",
        "maintain",
        "optimize",
        "own",
        "deliver",
        "drive",
        "grow",
        "scale",
        "migrate",
        "integrate",
        "coordinate",
        "mentor",
        "review",
        "define",
        "establish",
        "improve",
        "reduce",
        "increase",
        "support",
        "enable",
        "handle",
        "oversee",
        "operate",
        "automate",
        "monitor",
        "evaluate",
        "collaborate",
    }
)

_RESULT_FRAMING_RE = re.compile(
    r"\b(?:enabling|resulting|achieving|allowing|saving|delivering|"
    r"generating|helping|driving|growing|scaling|improving|"
    r"reducing|increasing|thereby|which|through|via)\b",
    re.IGNORECASE,
)

_METRIC_RE = re.compile(
    r"\d+\s*%|\d+\s*x\b|\$\s*[\d,]+|\d+\s*[kmb]\b",
    re.IGNORECASE,
)

_MIN_SUMMARY_WORDS = 20
_MAX_SUMMARY_WORDS = 80

_VOWEL_RE = re.compile(r"[aeiouy]+")
_WORD_ALPHA_RE = re.compile(r"\b[a-zA-Z]+\b")
_FK_MIN_GRADE = 6
_FK_MAX_GRADE = 12


def _count_syllables(word: str) -> int:
    w = word.lower()
    if len(w) > 2 and w.endswith("e") and w[-2] not in "aeiouy":
        w = w[:-1]
    return max(1, len(_VOWEL_RE.findall(w)))


def _fk_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level for a single-sentence highlight."""
    words = _WORD_ALPHA_RE.findall(text)
    if not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    return 0.39 * len(words) + 11.8 * (syllables / len(words)) - 15.59


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
            text = sections.highlight_text(hl)
            finding = test(text, i)
            if finding:
                finding.section = section
                finding.entry = sections.entry_label(section, entry)
                finding.bullet_index = i
                finding.bullet_text = text
                findings.append(finding)
    return findings


def _check_passive_voice(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-001: Flag passive voice constructions in highlights."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        match = _PASSIVE_RE.search(text)
        if match and match.group(1).lower() not in _PASSIVE_FALSE_POSITIVES:
            return LintFinding(
                rule_id="wl-001",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f'Passive voice detected: "{match.group()}"',
                fix_hint="Rewrite using an active verb (e.g. 'Designed', 'Built', 'Led').",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-001", test))
    return findings


def _check_missing_quantification(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-002: Flag entries whose highlights carry no numbers at all.

    Reported per entry rather than per bullet.
    """
    findings: list[LintFinding] = []
    for section in ("work", "projects"):
        if not resolved.show_sections.get(section):
            continue
        for entry in resolved.data.get(section, []):
            highlights = [sections.highlight_text(h) for h in entry.get("highlights", [])]
            if not highlights or any(re.search(r"\d+", text) for text in highlights):
                continue
            findings.append(
                LintFinding(
                    rule_id="wl-002",
                    severity="warning",
                    section=section,
                    entry=sections.entry_label(section, entry),
                    bullet_index=None,
                    bullet_text=None,
                    message="No quantified outcome in this entry.",
                    fix_hint=(
                        "Add a metric to at least one bullet: percentages, counts, "
                        "dollar amounts, or time saved. Not every bullet needs one."
                    ),
                )
            )
    return findings


def _check_noise_skills(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-003: Flag low-value 'noise' skills."""
    findings: list[LintFinding] = []
    if not resolved.show_sections.get("skills"):
        return findings

    for group in resolved.data.get("skills", []):
        category = group.get("category", "?")
        for item in group.get("items", []):
            name = sections.skill_name(item)
            if name.lower() in _NOISE_SKILLS:
                findings.append(
                    LintFinding(
                        rule_id="wl-003",
                        severity="warning",
                        section="skills",
                        entry=category,
                        bullet_index=None,
                        bullet_text=None,
                        message=f'"{name}" is considered a noise skill by most ATS reviewers.',
                        fix_hint="Remove it or replace with a more specific/valuable skill.",
                    )
                )
    return findings


def _check_weak_action_verbs(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-004: Flag highlights starting with weak action verbs."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        lower = text.lower().lstrip("- ").strip()
        for weak in _WEAK_OPENERS:
            if lower.startswith(weak):
                return LintFinding(
                    rule_id="wl-004",
                    severity="warning",
                    section="",
                    entry="",
                    bullet_index=idx,
                    bullet_text=text,
                    message=f'Weak opener: "{weak}".',
                    fix_hint="Start with a strong action verb: 'Designed', 'Implemented', "
                    "'Reduced', 'Delivered', 'Architected'.",
                )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-004", test))
    return findings


def _check_highlight_length(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-005: Flag highlights that are too short or too long."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        word_count = len(text.split())
        if word_count < _MIN_HIGHLIGHT_WORDS:
            return LintFinding(
                rule_id="wl-005",
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
                rule_id="wl-005",
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
        findings.extend(_check_highlights(resolved, section, "wl-005", test))
    return findings


def _check_date_format_consistency(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-012: Flag mixed date formats (YYYY-MM vs YYYY) within each section."""
    findings: list[LintFinding] = []

    for section in ("work", "education"):
        if not resolved.show_sections.get(section):
            continue
        formats: set[str] = set()
        for entry in resolved.data.get(section, []):
            for field in ("start_date", "end_date"):
                val = str(entry.get(field, "")).strip()
                if not val or val.lower() == "present":
                    continue
                if _DATE_YYYY_MM_RE.match(val):
                    formats.add("YYYY-MM")
                elif _DATE_YYYY_RE.match(val):
                    formats.add("YYYY")
                else:
                    formats.add("other")
        if len(formats) > 1:
            findings.append(
                LintFinding(
                    rule_id="wl-012",
                    severity="warning",
                    section=section,
                    entry="dates",
                    bullet_index=None,
                    bullet_text=None,
                    message=f"Mixed date formats in {section}: {', '.join(sorted(formats))}.",
                    fix_hint="Use a single date format throughout (YYYY-MM recommended).",
                )
            )

    return findings


def _check_tense_consistency(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-013: Present tense for current roles, past tense for previous."""
    findings: list[LintFinding] = []

    if not resolved.show_sections.get("work"):
        return findings

    for entry in resolved.data.get("work", []):
        end_date = str(entry.get("end_date", "")).strip().lower()
        is_current = not end_date or end_date == "present"
        company = str(entry.get("company", "?"))

        for i, hl in enumerate(entry.get("highlights", [])):
            text = sections.highlight_text(hl)
            if not text:
                continue
            first_word = text.lstrip("- ").split()[0].lower() if text.split() else ""
            is_past = (
                first_word.endswith("ed") and first_word not in _PRESENT_TENSE_ED
            ) or first_word in _IRREGULAR_PAST

            if is_current and is_past:
                findings.append(
                    LintFinding(
                        rule_id="wl-013",
                        severity="warning",
                        section="work",
                        entry=company,
                        bullet_index=i,
                        bullet_text=text,
                        message=f'Past-tense opener "{first_word}" in current role.',
                        fix_hint="Use present tense for current roles (e.g. 'Design', 'Lead').",
                    )
                )
            elif not is_current and first_word in _PRESENT_TENSE_VERBS:
                findings.append(
                    LintFinding(
                        rule_id="wl-013",
                        severity="warning",
                        section="work",
                        entry=company,
                        bullet_index=i,
                        bullet_text=text,
                        message=f'Present-tense opener "{first_word}" in past role.',
                        fix_hint="Use past tense for past roles (e.g. 'Designed', 'Led').",
                    )
                )

    return findings


def _check_summary_length(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-014: Warn if summary is too short or too long."""
    summary = resolved.data.get("basics", {}).get("summary", "")
    if not summary:
        return []
    word_count = len(summary.split())
    if word_count < _MIN_SUMMARY_WORDS:
        return [
            LintFinding(
                rule_id="wl-014",
                severity="warning",
                section="basics",
                entry="summary",
                bullet_index=None,
                bullet_text=None,
                message=f"Summary too short ({word_count} words, minimum {_MIN_SUMMARY_WORDS}).",
                fix_hint="Expand to 20–80 words to give context and grab recruiter attention.",
            )
        ]
    if word_count > _MAX_SUMMARY_WORDS:
        return [
            LintFinding(
                rule_id="wl-014",
                severity="warning",
                section="basics",
                entry="summary",
                bullet_index=None,
                bullet_text=None,
                message=f"Summary too long ({word_count} words, maximum {_MAX_SUMMARY_WORDS}).",
                fix_hint="Tighten to 80 words or fewer; recruiters skim the summary.",
            )
        ]
    return []


def _check_action_result(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-015: Flag highlights with a quantified metric but no result framing."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        if _METRIC_RE.search(text) and not _RESULT_FRAMING_RE.search(text):
            return LintFinding(
                rule_id="wl-015",
                severity="suggestion",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message="Metric found but no result framing (impact/outcome) detected.",
                fix_hint="Add the business impact: '…enabling X', '…resulting in Y', etc.",
            )
        return None

    for section in ("work", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-015", test))

    return findings


def _check_bullet_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-006: Warn if a work entry has too few or too many highlights."""
    findings: list[LintFinding] = []
    if not resolved.show_sections.get("work"):
        return findings
    for entry in resolved.data.get("work", []):
        count = len(entry.get("highlights", []))
        company = str(entry.get("company", "?"))
        if count < _MIN_BULLETS:
            findings.append(
                LintFinding(
                    rule_id="wl-006",
                    severity="warning",
                    section="work",
                    entry=company,
                    bullet_index=None,
                    bullet_text=None,
                    message=f"{count} highlight(s) (minimum {_MIN_BULLETS}).",
                    fix_hint="Add more highlights to better showcase your impact in this role.",
                )
            )
        elif count > _MAX_BULLETS:
            findings.append(
                LintFinding(
                    rule_id="wl-006",
                    severity="warning",
                    section="work",
                    entry=company,
                    bullet_index=None,
                    bullet_text=None,
                    message=f"{count} highlights (maximum {_MAX_BULLETS}).",
                    fix_hint="Trim to the most impactful bullets.",
                )
            )
    return findings


def _has_first_person(text: str) -> bool:
    """True when *text* actually uses a first-person pronoun.

    A bare "I" is only a pronoun when it is not a roman numeral. "Algorithms I"
    and "Phase II" are a course level and a project stage, and both follow a
    capitalised noun — whereas the pronoun opens a clause or follows a
    lowercase word.
    """
    if _FIRST_PERSON_RE.search(text):
        return True
    for match in _PRONOUN_I_RE.finditer(text):
        preceding = text[: match.start()].rstrip()
        if not preceding:
            return True
        if not preceding.split()[-1][:1].isupper():
            return True
    return False


def _check_first_person(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-007: Flag first-person pronouns in highlights and summary."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        if _has_first_person(text):
            return LintFinding(
                rule_id="wl-007",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message="First-person pronoun detected.",
                fix_hint="Remove first-person pronouns; use implied subject.",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-007", test))

    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary and _has_first_person(summary):
        findings.append(
            LintFinding(
                rule_id="wl-007",
                severity="warning",
                section="basics",
                entry="summary",
                bullet_index=None,
                bullet_text=None,
                message="First-person pronoun detected in summary.",
                fix_hint="Remove first-person pronouns; use implied subject.",
            )
        )

    return findings


def _check_vague_buzzwords(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-008: Flag vague buzzwords in highlights and summary."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        m = _VAGUE_BUZZWORDS_RE.search(text)
        if m:
            return LintFinding(
                rule_id="wl-008",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f'Vague buzzword detected: "{m.group().lower()}".',
                fix_hint="Replace with specific accomplishment or concrete skill.",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-008", test))

    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary:
        m = _VAGUE_BUZZWORDS_RE.search(summary)
        if m:
            findings.append(
                LintFinding(
                    rule_id="wl-008",
                    severity="warning",
                    section="basics",
                    entry="summary",
                    bullet_index=None,
                    bullet_text=None,
                    message=f'Vague buzzword detected: "{m.group().lower()}".',
                    fix_hint="Replace with specific accomplishment or concrete skill.",
                )
            )

    return findings


def _check_skill_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-009: Warn if total skills are below minimum or above maximum."""
    if not resolved.show_sections.get("skills"):
        return []
    total = sum(len(group.get("items", [])) for group in resolved.data.get("skills", []))
    if total < _MIN_SKILLS:
        return [
            LintFinding(
                rule_id="wl-009",
                severity="warning",
                section="skills",
                entry="total",
                bullet_index=None,
                bullet_text=None,
                message=f"Only {total} skill(s) listed (minimum {_MIN_SKILLS}).",
                fix_hint="Add more skills to reach at least 8.",
            )
        ]
    if total > _MAX_SKILLS:
        return [
            LintFinding(
                rule_id="wl-009",
                severity="warning",
                section="skills",
                entry="total",
                bullet_index=None,
                bullet_text=None,
                message=f"{total} skills listed (maximum {_MAX_SKILLS}).",
                fix_hint="Trim to the most relevant 25 skills.",
            )
        ]
    return []


def _check_education_size(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-018: Warn if the education section has grown into a course list."""
    if not resolved.show_sections.get("education"):
        return []
    entries = resolved.data.get("education", [])
    if len(entries) <= _MAX_EDUCATION_ENTRIES:
        return []
    return [
        LintFinding(
            rule_id="wl-018",
            severity="warning",
            section="education",
            entry="total",
            bullet_index=None,
            bullet_text=None,
            message=(
                f"{len(entries)} education entries (over {_MAX_EDUCATION_ENTRIES}). "
                "Degrees and short courses are rendering with equal weight."
            ),
            fix_hint=(
                "Move certifications and short courses to data/certifications.yaml, "
                "which renders compactly as its own section. Alternatively tag the "
                "tail (e.g. tags: [certification]) and filter it out per profile."
            ),
        )
    ]


def _parse_date(value: str, *, as_end: bool = False) -> tuple[int, int] | None:
    """Parse ``YYYY`` / ``YYYY-MM`` into a comparable ``(year, month)``.

    ``Present`` (and anything unparseable) returns ``None``; callers decide what
    an open-ended date means. A bare year resolves to December when it closes a
    range and January when it opens one, so ``2020`` – ``2020-05`` is not read
    as ending before it starts.
    """
    text = str(value).strip()
    if _DATE_YYYY_MM_RE.match(text):
        year, month = text.split("-")
        return int(year), int(month)
    if _DATE_YYYY_RE.match(text):
        return int(text), 12 if as_end else 1
    return None


def _entry_rank(section: sections.Section, entry: dict[str, Any]) -> tuple[int, int] | None:
    """Chronological rank of *entry* — the first present ``sort_date_keys`` field.

    An explicit ``Present`` outranks every real date, since the role is ongoing.
    """
    for key in section.sort_date_keys:
        raw = str(entry.get(key, "")).strip()
        if not raw:
            continue
        if raw.lower() == "present":
            return (9999, 12)
        parsed = _parse_date(raw, as_end=key.startswith("end"))
        if parsed:
            return parsed
    return None


def _check_chronological_order(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-019: Flag sections not ordered newest-first."""
    findings: list[LintFinding] = []
    for section in sections.SECTIONS:
        if not section.sort_date_keys or not resolved.show_sections.get(section.name):
            continue
        entries = resolved.data.get(section.name, [])
        # Order only means something within a rendered block; certifications
        # render as two, and their chronologies are independent.
        for run in sections.ordered_runs(section.name, entries):
            findings.extend(_out_of_order(section, run))
    return findings


def _out_of_order(section: sections.Section, entries: list[dict[str, Any]]) -> list[LintFinding]:
    """The first entry in *entries* that is newer than the one above it."""
    findings: list[LintFinding] = []
    ranked = [(e, _entry_rank(section, e)) for e in entries]
    dated = [(e, r) for e, r in ranked if r is not None]
    if len(dated) >= 2:
        for (_, earlier), (entry, later) in zip(dated, dated[1:], strict=False):
            if later > earlier:
                findings.append(
                    LintFinding(
                        rule_id="wl-019",
                        severity="warning",
                        section=section.name,
                        entry=sections.entry_label(section.name, entry),
                        bullet_index=None,
                        bullet_text=None,
                        message=(
                            f"'{sections.entry_label(section.name, entry)}' is newer than the "
                            "entry above it — this section is not in reverse-chronological order."
                        ),
                        fix_hint=(
                            "Rename the files so the newest sorts first — "
                            f"data/{section.name}/ loads in filename order."
                            if section.from_directory
                            else "Reorder the entries newest-first; cvloom renders "
                            "them in the order they appear in the file."
                        ),
                    )
                )
                break
    return findings


def _check_date_sanity(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-020: Flag impossible dates and expired credentials."""
    findings: list[LintFinding] = []
    today = date.today()
    now = (today.year, today.month)

    def finding(section: str, entry: dict[str, Any], message: str, fix_hint: str) -> LintFinding:
        return LintFinding(
            rule_id="wl-020",
            severity="warning",
            section=section,
            entry=sections.entry_label(section, entry),
            bullet_index=None,
            bullet_text=None,
            message=message,
            fix_hint=fix_hint,
        )

    for section in sections.SECTIONS:
        if not resolved.show_sections.get(section.name):
            continue
        for entry in resolved.data.get(section.name, []):
            if section.range_keys:
                start_key, end_key = section.range_keys
                start = _parse_date(str(entry.get(start_key, "")))
                end = _parse_date(str(entry.get(end_key, "")), as_end=True)
                if start and end and end < start:
                    findings.append(
                        finding(
                            section.name,
                            entry,
                            f"Entry ends before it starts ({entry[start_key]} → {entry[end_key]}).",
                            "Correct the dates. Parsers reading a negative tenure may "
                            "drop the entry or mis-assign its dates.",
                        )
                    )

            for key in (*section.sort_date_keys, *(section.range_keys or ())):
                raw = str(entry.get(key, "")).strip()
                parsed = _parse_date(raw) if raw else None
                if parsed and parsed > now:
                    findings.append(
                        finding(
                            section.name,
                            entry,
                            f"'{key}' is in the future ({raw}).",
                            "Use a date that has already happened, or 'Present' "
                            "for an ongoing entry.",
                        )
                    )
                    break

            if section.expiry_key:
                expiry_raw = str(entry.get(section.expiry_key, "")).strip()
                expiry = _parse_date(expiry_raw, as_end=True) if expiry_raw else None
                if expiry and expiry < now:
                    findings.append(
                        finding(
                            section.name,
                            entry,
                            f"Credential expired ({expiry_raw}).",
                            "Renew it, remove it, or label it as lapsed. Listing an "
                            "expired credential as current is a credibility risk.",
                        )
                    )
    return findings


def _check_unfilled_placeholders(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-021: Flag scaffold placeholders left in the content."""
    findings: list[LintFinding] = []

    def scan(section: str, entry_label: str, text: str) -> None:
        match = _PLACEHOLDER_RE.search(text)
        if match:
            findings.append(
                LintFinding(
                    rule_id="wl-021",
                    severity="warning",
                    section=section,
                    entry=entry_label,
                    bullet_index=None,
                    bullet_text=None,
                    message=f"Unfilled placeholder: {match.group()}",
                    fix_hint=(
                        "Replace it with real content, or delete the clause. "
                        "This renders verbatim into the PDF you send out."
                    ),
                )
            )

    basics = resolved.data.get("basics", {})
    for key in ("headline", "summary"):
        scan("basics", key, str(basics.get(key, "")))
    for link in basics.get("links", []):
        scan("basics", f"link: {link.get('label', '')}", str(link.get("url", "")))

    for section in sections.SECTIONS:
        if not resolved.show_sections.get(section.name):
            continue
        for entry in resolved.data.get(section.name, []):
            label = sections.entry_label(section.name, entry)
            for text in sections.iter_entry_text(entry):
                scan(section.name, label, text)

    return findings


def _check_profile_links(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-010: Warn if no LinkedIn or GitHub link is present."""
    links = resolved.data.get("basics", {}).get("links", [])
    if any(network_of(str(link.get("url", ""))) for link in links):
        return []
    return [
        LintFinding(
            rule_id="wl-010",
            severity="warning",
            section="basics",
            entry="profile links",
            bullet_index=None,
            bullet_text=None,
            message="No LinkedIn or GitHub profile link found.",
            fix_hint="Add a LinkedIn or GitHub entry to `links` in data/basics.yaml.",
        )
    ]


def _check_duplicate_links(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-022: Warn if two `links` entries point at the same place.

    Compared after normalisation, so ``https://www.github.com/me/`` and
    ``github.com/me`` are caught as the duplicate they are.
    """
    findings: list[LintFinding] = []
    seen: dict[str, str] = {}
    for link in resolved.data.get("basics", {}).get("links", []):
        url = str(link.get("url", ""))
        if not url:
            continue
        key = normalize_url(url)
        if key in seen:
            findings.append(
                LintFinding(
                    rule_id="wl-022",
                    severity="warning",
                    section="basics",
                    entry="profile links",
                    bullet_index=None,
                    bullet_text=None,
                    message=f"Duplicate link: {url} repeats {seen[key]}.",
                    fix_hint="Remove one of the two entries from `links` in data/basics.yaml.",
                )
            )
        else:
            seen[key] = url
    return findings


def _check_page_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-011: Warn if estimated page count exceeds 2 (skipped for academic templates)."""
    if "academic" in resolved.template_name:
        return []

    texts: list[str] = []
    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary:
        texts.append(summary)
    for section in ("work", "education", "projects"):
        for entry in resolved.data.get(section, []):
            for hl in entry.get("highlights", []):
                text = sections.highlight_text(hl)
                if text:
                    texts.append(text)
    for group in resolved.data.get("skills", []):
        for item in group.get("items", []):
            name = sections.skill_name(item)
            if name:
                texts.append(name)

    total_words = sum(len(t.split()) for t in texts)
    estimated_pages = max(1, round(total_words / _WORDS_PER_PAGE))

    if estimated_pages > _MAX_PAGES:
        return [
            LintFinding(
                rule_id="wl-011",
                severity="warning",
                section="basics",
                entry="page estimate",
                bullet_index=None,
                bullet_text=None,
                message=f"Estimated ~{estimated_pages} pages; target 1–{_MAX_PAGES} pages.",
                fix_hint="Reduce highlights or shorten descriptions.",
            )
        ]
    return []


def _check_readability(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-016: Flag highlights with Flesch-Kincaid grade level outside 6–12."""

    def test(text: str, idx: int) -> LintFinding | None:
        grade = _fk_grade(text)
        if grade > _FK_MAX_GRADE:
            return LintFinding(
                rule_id="wl-016",
                severity="suggestion",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=(
                    f"Readability grade {grade:.1f} exceeds target (≤{_FK_MAX_GRADE});"
                    " simplify sentence structure."
                ),
                fix_hint=(
                    "Break into shorter phrases or replace multi-syllable words"
                    " with simpler alternatives."
                ),
            )
        if grade < _FK_MIN_GRADE:
            return LintFinding(
                rule_id="wl-016",
                severity="suggestion",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=(
                    f"Readability grade {grade:.1f} is below target (≥{_FK_MIN_GRADE});"
                    " add context or detail."
                ),
                fix_hint=(
                    "Expand the highlight with a result, metric, or scope to increase substance."
                ),
            )
        return None

    findings: list[LintFinding] = []
    for section in ("work", "projects"):
        findings.extend(_check_highlights(resolved, section, "wl-016", test))
    return findings


def _check_tech_mentions_in_work(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-017: Flag work entries whose highlights mention no skill item."""
    skill_names: set[str] = set()
    for group in resolved.data.get("skills", []):
        for item in group.get("items", []):
            name = sections.skill_name(item)
            if name:
                skill_names.add(name.lower())

    if not skill_names:
        return []

    findings: list[LintFinding] = []
    for entry in resolved.data.get("work", []):
        highlights = entry.get("highlights", [])
        if not highlights:
            continue
        hl_text = " ".join(sections.highlight_text(h) for h in highlights).lower()
        if not any(skill in hl_text for skill in skill_names):
            findings.append(
                LintFinding(
                    rule_id="wl-017",
                    severity="suggestion",
                    section="work",
                    entry=entry.get("company", ""),
                    bullet_index=None,
                    bullet_text=None,
                    message="No skill items mentioned in this role's highlights.",
                    fix_hint=(
                        "Reference at least one tool, language, or framework "
                        "from your skills section."
                    ),
                )
            )
    return findings


# ── Rule registry ───────────────────────────────────────────────────

_NON_ASCII_DASHES = {"\u2013": "en dash", "\u2014": "em dash", "\u2212": "minus sign"}


def _check_non_ascii_dashes(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-023: Flag en/em dashes in content.

    cvloom renders every range and separator it controls as an ASCII hyphen, so a
    remaining en/em dash comes from the content. See docs/reference/ats-linter-rules.md.
    """
    findings: list[LintFinding] = []
    for section in (sec.name for sec in sections.SECTIONS):
        if not resolved.show_sections.get(section):
            continue
        for entry in resolved.data.get(section, []) or []:
            for text in sections.iter_entry_text(entry):
                found = sorted({d for d in _NON_ASCII_DASHES if d in text})
                if not found:
                    continue
                names = ", ".join(_NON_ASCII_DASHES[d] for d in found)
                findings.append(
                    LintFinding(
                        rule_id="wl-023",
                        severity="info",
                        section=section,
                        entry=sections.entry_label(section, entry),
                        bullet_index=None,
                        bullet_text=text,
                        message=f"Contains {names} rather than an ASCII hyphen.",
                        fix_hint="Replace with '-' so every dash in the document matches.",
                    )
                )
                break
    return findings


def _check_fused_connector(resolved: ResolvedProfile) -> list[LintFinding]:
    """wl-024: Flag an education connector that would fuse degree and field.

    The connector is written verbatim, so it carries its own spacing. Unquoted
    YAML strips it — ``connector: in`` renders ``BScinComputer Science``. Only a
    connector padded on neither side fuses both words: ``", "`` and ``" in "``
    are both fine.
    """
    if not resolved.show_sections.get("education"):
        return []
    findings: list[LintFinding] = []
    for entry in resolved.data.get("education", []) or []:
        connector = str(entry.get("connector") or "")
        if not connector or not entry.get("degree") or not entry.get("field"):
            continue
        if connector[0].isspace() or connector[-1].isspace():
            continue
        findings.append(
            LintFinding(
                rule_id="wl-024",
                severity="warning",
                section="education",
                entry=sections.entry_label("education", entry),
                bullet_index=None,
                bullet_text=sections.degree_line(entry),
                message=(
                    f"Connector '{connector}' has no surrounding space, so degree and "
                    "field render fused."
                ),
                fix_hint=(
                    f'Quote it with the spacing you want: connector: " {connector} ". '
                    'Punctuation connectors such as ", " need only the trailing space.'
                ),
            )
        )
    return findings


RULES: list[LintRule] = [
    LintRule(
        "wl-001",
        "passive-voice",
        "Flag passive voice in highlights",
        CATEGORY_WRITING,
        _check_passive_voice,
    ),
    LintRule(
        "wl-002",
        "missing-quantification",
        "Flag highlights without numbers",
        CATEGORY_WRITING,
        _check_missing_quantification,
    ),
    LintRule(
        "wl-003",
        "noise-skills",
        "Flag low-value skills",
        CATEGORY_WRITING,
        _check_noise_skills,
    ),
    LintRule(
        "wl-004",
        "weak-action-verbs",
        "Flag weak opening verbs",
        CATEGORY_WRITING,
        _check_weak_action_verbs,
    ),
    LintRule(
        "wl-005",
        "highlight-length",
        "Flag too-short or too-long highlights",
        CATEGORY_WRITING,
        _check_highlight_length,
    ),
    LintRule(
        "wl-012",
        "date-format-consistency",
        "Flag mixed date formats within work or education sections",
        CATEGORY_ATS_PARSE,
        _check_date_format_consistency,
    ),
    LintRule(
        "wl-013",
        "tense-consistency",
        "Present tense for current roles, past tense for previous",
        CATEGORY_WRITING,
        _check_tense_consistency,
    ),
    LintRule(
        "wl-014",
        "summary-length",
        "Warn if summary is too short or too long",
        CATEGORY_STRUCTURE,
        _check_summary_length,
    ),
    LintRule(
        "wl-015",
        "action-result",
        "Flag highlights with a metric but no result framing",
        CATEGORY_WRITING,
        _check_action_result,
    ),
    LintRule(
        "wl-006",
        "bullet-count",
        "Warn if a work entry has too few or too many highlights",
        CATEGORY_STRUCTURE,
        _check_bullet_count,
    ),
    LintRule(
        "wl-007",
        "first-person",
        "Flag first-person pronouns in highlights and summary",
        CATEGORY_WRITING,
        _check_first_person,
    ),
    LintRule(
        "wl-008",
        "vague-buzzwords",
        "Flag vague buzzwords in highlights and summary",
        CATEGORY_WRITING,
        _check_vague_buzzwords,
    ),
    LintRule(
        "wl-009",
        "skill-count",
        "Warn if total skills are below minimum or above maximum",
        CATEGORY_STRUCTURE,
        _check_skill_count,
    ),
    LintRule(
        "wl-010",
        "profile-links",
        "Warn if no LinkedIn or GitHub link is present",
        CATEGORY_STRUCTURE,
        _check_profile_links,
    ),
    LintRule(
        "wl-011",
        "page-count",
        "Warn if estimated page count exceeds 2",
        CATEGORY_STRUCTURE,
        _check_page_count,
    ),
    LintRule(
        "wl-016",
        "readability",
        "Flesch-Kincaid grade level per highlight (target 6–12)",
        CATEGORY_WRITING,
        _check_readability,
    ),
    LintRule(
        "wl-017",
        "tech-mentions-in-work",
        "Flag work entries with no skill items mentioned in highlights",
        CATEGORY_ATS_PARSE,
        _check_tech_mentions_in_work,
    ),
    LintRule(
        "wl-018",
        "education-size",
        f"Flag an education section with more than {_MAX_EDUCATION_ENTRIES} entries",
        CATEGORY_STRUCTURE,
        _check_education_size,
    ),
    LintRule(
        "wl-019",
        "chronological-order",
        "Flag sections not ordered newest-first",
        CATEGORY_STRUCTURE,
        _check_chronological_order,
    ),
    LintRule(
        "wl-020",
        "date-sanity",
        "Flag impossible dates and expired credentials",
        CATEGORY_ATS_PARSE,
        _check_date_sanity,
    ),
    LintRule(
        "wl-021",
        "unfilled-placeholders",
        "Flag scaffold placeholders left in the content",
        CATEGORY_STRUCTURE,
        _check_unfilled_placeholders,
    ),
    LintRule(
        "wl-022",
        "duplicate-links",
        "Flag two `links` entries pointing at the same place",
        CATEGORY_STRUCTURE,
        _check_duplicate_links,
    ),
    LintRule(
        "wl-023",
        "non-ascii-dashes",
        "Flag en/em dashes in content, which cvloom renders as ASCII elsewhere",
        CATEGORY_ATS_PARSE,
        _check_non_ascii_dashes,
    ),
    LintRule(
        "wl-024",
        "fused-connector",
        "Flag an education connector that renders degree and field fused together",
        CATEGORY_STRUCTURE,
        _check_fused_connector,
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
        rule_findings = rule.check(resolved)
        for finding in rule_findings:
            finding.category = rule.category
        findings.extend(rule_findings)
    return findings


def category_counts(findings: list[LintFinding]) -> dict[str, int]:
    """Count findings per category, in the canonical axis order."""
    counts = {
        CATEGORY_WRITING: 0,
        CATEGORY_STRUCTURE: 0,
        CATEGORY_ATS_PARSE: 0,
    }
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return counts
