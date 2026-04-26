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

_FIRST_PERSON_RE = re.compile(r"\b(I|my|me|mine|myself)\b", re.IGNORECASE)

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
_WORDS_PER_PAGE = 500

_DATE_YYYY_MM_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_YYYY_RE = re.compile(r"^\d{4}$")

_IRREGULAR_PAST = frozenset({
    "led", "built", "ran", "wrote", "grew", "drove", "won", "taught",
    "brought", "became", "came", "cut", "drew", "went", "had", "held",
    "kept", "lost", "made", "met", "paid", "put", "read", "said", "sat",
    "sold", "took", "told", "thought", "set", "got", "left", "sent", "spent",
    "began", "broke", "chose", "found", "gave", "knew", "saw", "spoke",
    "stood", "wore",
})

_PRESENT_TENSE_VERBS = frozenset({
    "design", "develop", "build", "lead", "manage", "implement", "create",
    "write", "run", "analyze", "architect", "deploy", "maintain", "optimize",
    "own", "deliver", "drive", "grow", "scale", "migrate", "integrate",
    "coordinate", "mentor", "review", "define", "establish", "improve",
    "reduce", "increase", "support", "enable", "handle", "oversee",
    "operate", "automate", "monitor", "evaluate", "collaborate",
})

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


def _check_date_format_consistency(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-012: Flag mixed date formats (YYYY-MM vs YYYY) within each section."""
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
            findings.append(LintFinding(
                rule_id="ats-012",
                severity="warning",
                section=section,
                entry="dates",
                bullet_index=None,
                bullet_text=None,
                message=f"Mixed date formats in {section}: {', '.join(sorted(formats))}.",
                fix_hint="Use a single date format throughout (YYYY-MM recommended).",
            ))

    return findings


def _check_tense_consistency(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-013: Present tense for current roles, past tense for previous."""
    findings: list[LintFinding] = []

    if not resolved.show_sections.get("work"):
        return findings

    for entry in resolved.data.get("work", []):
        end_date = str(entry.get("end_date", "")).strip().lower()
        is_current = not end_date or end_date == "present"
        company = str(entry.get("company", "?"))

        for i, hl in enumerate(entry.get("highlights", [])):
            text = hl if isinstance(hl, str) else hl.get("text", "")
            if not text:
                continue
            first_word = text.lstrip("- ").split()[0].lower() if text.split() else ""
            is_past = first_word.endswith("ed") or first_word in _IRREGULAR_PAST

            if is_current and is_past:
                findings.append(LintFinding(
                    rule_id="ats-013",
                    severity="warning",
                    section="work",
                    entry=company,
                    bullet_index=i,
                    bullet_text=text,
                    message=f"Past-tense opener \"{first_word}\" in current role.",
                    fix_hint="Use present tense for current roles (e.g. 'Design', 'Lead').",
                ))
            elif not is_current and first_word in _PRESENT_TENSE_VERBS:
                findings.append(LintFinding(
                    rule_id="ats-013",
                    severity="warning",
                    section="work",
                    entry=company,
                    bullet_index=i,
                    bullet_text=text,
                    message=f"Present-tense opener \"{first_word}\" in past role.",
                    fix_hint="Use past tense for past roles (e.g. 'Designed', 'Led').",
                ))

    return findings


def _check_summary_length(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-014: Warn if summary is too short or too long."""
    summary = resolved.data.get("basics", {}).get("summary", "")
    if not summary:
        return []
    word_count = len(summary.split())
    if word_count < _MIN_SUMMARY_WORDS:
        return [LintFinding(
            rule_id="ats-014",
            severity="warning",
            section="basics",
            entry="summary",
            bullet_index=None,
            bullet_text=None,
            message=f"Summary too short ({word_count} words, minimum {_MIN_SUMMARY_WORDS}).",
            fix_hint="Expand to 20–80 words to give context and grab recruiter attention.",
        )]
    if word_count > _MAX_SUMMARY_WORDS:
        return [LintFinding(
            rule_id="ats-014",
            severity="warning",
            section="basics",
            entry="summary",
            bullet_index=None,
            bullet_text=None,
            message=f"Summary too long ({word_count} words, maximum {_MAX_SUMMARY_WORDS}).",
            fix_hint="Tighten to 80 words or fewer; recruiters skim the summary.",
        )]
    return []


def _check_action_result(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-015: Flag highlights with a quantified metric but no result framing."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        if _METRIC_RE.search(text) and not _RESULT_FRAMING_RE.search(text):
            return LintFinding(
                rule_id="ats-015",
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
        findings.extend(_check_highlights(resolved, section, "ats-015", test))

    return findings


def _check_bullet_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-006: Warn if a work entry has too few or too many highlights."""
    findings: list[LintFinding] = []
    if not resolved.show_sections.get("work"):
        return findings
    for entry in resolved.data.get("work", []):
        count = len(entry.get("highlights", []))
        company = str(entry.get("company", "?"))
        if count < _MIN_BULLETS:
            findings.append(LintFinding(
                rule_id="ats-006",
                severity="warning",
                section="work",
                entry=company,
                bullet_index=None,
                bullet_text=None,
                message=f"{count} highlight(s) (minimum {_MIN_BULLETS}).",
                fix_hint="Add more highlights to better showcase your impact in this role.",
            ))
        elif count > _MAX_BULLETS:
            findings.append(LintFinding(
                rule_id="ats-006",
                severity="warning",
                section="work",
                entry=company,
                bullet_index=None,
                bullet_text=None,
                message=f"{count} highlights (maximum {_MAX_BULLETS}).",
                fix_hint="Trim to the most impactful bullets.",
            ))
    return findings


def _check_first_person(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-007: Flag first-person pronouns in highlights and summary."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        if _FIRST_PERSON_RE.search(text):
            return LintFinding(
                rule_id="ats-007",
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
        findings.extend(_check_highlights(resolved, section, "ats-007", test))

    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary and _FIRST_PERSON_RE.search(summary):
        findings.append(LintFinding(
            rule_id="ats-007",
            severity="warning",
            section="basics",
            entry="summary",
            bullet_index=None,
            bullet_text=None,
            message="First-person pronoun detected in summary.",
            fix_hint="Remove first-person pronouns; use implied subject.",
        ))

    return findings


def _check_vague_buzzwords(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-008: Flag vague buzzwords in highlights and summary."""
    findings: list[LintFinding] = []

    def test(text: str, idx: int) -> LintFinding | None:
        m = _VAGUE_BUZZWORDS_RE.search(text)
        if m:
            return LintFinding(
                rule_id="ats-008",
                severity="warning",
                section="",
                entry="",
                bullet_index=idx,
                bullet_text=text,
                message=f"Vague buzzword detected: \"{m.group().lower()}\".",
                fix_hint="Replace with specific accomplishment or concrete skill.",
            )
        return None

    for section in ("work", "education", "projects"):
        findings.extend(_check_highlights(resolved, section, "ats-008", test))

    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary:
        m = _VAGUE_BUZZWORDS_RE.search(summary)
        if m:
            findings.append(LintFinding(
                rule_id="ats-008",
                severity="warning",
                section="basics",
                entry="summary",
                bullet_index=None,
                bullet_text=None,
                message=f"Vague buzzword detected: \"{m.group().lower()}\".",
                fix_hint="Replace with specific accomplishment or concrete skill.",
            ))

    return findings


def _check_skill_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-009: Warn if total skills are below minimum or above maximum."""
    if not resolved.show_sections.get("skills"):
        return []
    total = sum(len(group.get("items", [])) for group in resolved.data.get("skills", []))
    if total < _MIN_SKILLS:
        return [LintFinding(
            rule_id="ats-009",
            severity="warning",
            section="skills",
            entry="total",
            bullet_index=None,
            bullet_text=None,
            message=f"Only {total} skill(s) listed (minimum {_MIN_SKILLS}).",
            fix_hint="Add more skills to reach at least 8.",
        )]
    if total > _MAX_SKILLS:
        return [LintFinding(
            rule_id="ats-009",
            severity="warning",
            section="skills",
            entry="total",
            bullet_index=None,
            bullet_text=None,
            message=f"{total} skills listed (maximum {_MAX_SKILLS}).",
            fix_hint="Trim to the most relevant 25 skills.",
        )]
    return []


def _check_profile_links(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-010: Warn if no LinkedIn or GitHub link is present."""
    contact = resolved.data.get("contact", {})
    if contact.get("linkedin") or contact.get("github"):
        return []
    for link in resolved.data.get("basics", {}).get("public_links", []):
        url = str(link.get("url", ""))
        if "linkedin.com" in url or "github.com" in url:
            return []
    return [LintFinding(
        rule_id="ats-010",
        severity="warning",
        section="contact",
        entry="profile links",
        bullet_index=None,
        bullet_text=None,
        message="No LinkedIn or GitHub profile link found.",
        fix_hint="Add linkedin or github to contact.yaml, or add a public_links entry in basics.",
    )]


def _check_page_count(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-011: Warn if estimated page count exceeds 2 (skipped for academic templates)."""
    if "academic" in resolved.template_name:
        return []

    texts: list[str] = []
    summary = resolved.data.get("basics", {}).get("summary", "")
    if summary:
        texts.append(summary)
    for section in ("work", "education", "projects"):
        for entry in resolved.data.get(section, []):
            for hl in entry.get("highlights", []):
                text = hl if isinstance(hl, str) else hl.get("text", "")
                if text:
                    texts.append(text)
    for group in resolved.data.get("skills", []):
        for item in group.get("items", []):
            name = item if isinstance(item, str) else item.get("name", "")
            if name:
                texts.append(name)

    total_words = sum(len(t.split()) for t in texts)
    estimated_pages = max(1, round(total_words / _WORDS_PER_PAGE))

    if estimated_pages > 2:
        return [LintFinding(
            rule_id="ats-011",
            severity="warning",
            section="basics",
            entry="page estimate",
            bullet_index=None,
            bullet_text=None,
            message=f"Estimated ~{estimated_pages} pages; target 1–2 pages.",
            fix_hint="Reduce highlights or shorten descriptions.",
        )]
    return []


def _check_readability(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-016: Flag highlights with Flesch-Kincaid grade level outside 6–12."""

    def test(text: str, idx: int) -> LintFinding | None:
        grade = _fk_grade(text)
        if grade > _FK_MAX_GRADE:
            return LintFinding(
                rule_id="ats-016", severity="suggestion",
                section="", entry="", bullet_index=idx, bullet_text=text,
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
                rule_id="ats-016", severity="suggestion",
                section="", entry="", bullet_index=idx, bullet_text=text,
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
        findings.extend(_check_highlights(resolved, section, "ats-016", test))
    return findings


def _check_tech_mentions_in_work(resolved: ResolvedProfile) -> list[LintFinding]:
    """ats-017: Flag work entries whose highlights mention no skill item."""
    skill_names: set[str] = set()
    for group in resolved.data.get("skills", []):
        for item in group.get("items", []):
            name = item if isinstance(item, str) else item.get("name", "")
            if name:
                skill_names.add(name.lower())

    if not skill_names:
        return []

    findings: list[LintFinding] = []
    for entry in resolved.data.get("work", []):
        highlights = entry.get("highlights", [])
        if not highlights:
            continue
        hl_text = " ".join(
            h if isinstance(h, str) else h.get("text", "")
            for h in highlights
        ).lower()
        if not any(skill in hl_text for skill in skill_names):
            findings.append(LintFinding(
                rule_id="ats-017", severity="suggestion",
                section="work", entry=entry.get("company", ""),
                bullet_index=None, bullet_text=None,
                message="No skill items mentioned in this role's highlights.",
                fix_hint=(
                    "Reference at least one tool, language, or framework from your skills section."
                ),
            ))
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
    LintRule(
        "ats-012", "date-format-consistency",
        "Flag mixed date formats within work or education sections", _check_date_format_consistency,
    ),
    LintRule(
        "ats-013", "tense-consistency",
        "Present tense for current roles, past tense for previous", _check_tense_consistency,
    ),
    LintRule(
        "ats-014", "summary-length",
        "Warn if summary is too short or too long", _check_summary_length,
    ),
    LintRule(
        "ats-015", "action-result",
        "Flag highlights with a metric but no result framing", _check_action_result,
    ),
    LintRule(
        "ats-006", "bullet-count",
        "Warn if a work entry has too few or too many highlights", _check_bullet_count,
    ),
    LintRule(
        "ats-007", "first-person",
        "Flag first-person pronouns in highlights and summary", _check_first_person,
    ),
    LintRule(
        "ats-008", "vague-buzzwords",
        "Flag vague buzzwords in highlights and summary", _check_vague_buzzwords,
    ),
    LintRule(
        "ats-009", "skill-count",
        "Warn if total skills are below minimum or above maximum", _check_skill_count,
    ),
    LintRule(
        "ats-010", "profile-links",
        "Warn if no LinkedIn or GitHub link is present", _check_profile_links,
    ),
    LintRule(
        "ats-011", "page-count",
        "Warn if estimated page count exceeds 2", _check_page_count,
    ),
    LintRule(
        "ats-016", "readability",
        "Flesch-Kincaid grade level per highlight (target 6–12)", _check_readability,
    ),
    LintRule(
        "ats-017", "tech-mentions-in-work",
        "Flag work entries with no skill items mentioned in highlights",
        _check_tech_mentions_in_work,
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
