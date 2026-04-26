"""Keyword gap analysis — compare CV content against a job description."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from cvloom.models import ResolvedProfile

# ── Data structures ────────────────────────────────────────────────


@dataclass
class KeywordMatch:
    """A keyword found in both JD and CV."""

    keyword: str
    found_in: list[str]
    frequency_jd: int
    frequency_cv: int


@dataclass
class MatchReport:
    """Result of comparing CV keywords against a job description."""

    matched: list[KeywordMatch]
    gaps: list[str]
    jd_word_count: int
    cv_keywords_coverage: float
    top_jd_keywords: list[tuple[str, int]] = field(default_factory=list)
    suggestions: dict[str, str] = field(default_factory=dict)
    reorder_hints: list[str] = field(default_factory=list)


# ── Stop words ─────────────────────────────────────────────────────

_STOP_WORDS: set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "has", "have", "having", "he", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "me", "might",
    "more", "most", "must", "my", "myself", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves",
    "out", "over", "own", "s", "same", "shall", "she", "should", "so",
    "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "us", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "would", "you", "your", "yours", "yourself",
    "yourselves",
}

# ── Token extraction ───────────────────────────────────────────────

_TOKEN_RE = re.compile(r"\b[a-z][a-z0-9+#]*\b", re.IGNORECASE)


def _extract_keywords(text: str) -> dict[str, int]:
    """Tokenise *text* and return non-stop-word frequency counts."""
    counts: dict[str, int] = {}
    for token in _TOKEN_RE.findall(text.lower()):
        if token not in _STOP_WORDS and len(token) > 1:
            counts[token] = counts.get(token, 0) + 1
    return counts


def _extract_cv_keywords(
    data: dict[str, Any],
    show_sections: dict[str, bool],
) -> dict[str, set[str]]:
    """Walk visible CV sections and return ``{keyword: {sections...}}``."""
    result: dict[str, set[str]] = {}

    def _ingest(text: str, section: str) -> None:
        for token in _TOKEN_RE.findall(text.lower()):
            if token not in _STOP_WORDS and len(token) > 1:
                result.setdefault(token, set()).add(section)

    # Basics — always present
    basics = data.get("basics", {})
    _ingest(basics.get("headline", ""), "basics")
    _ingest(basics.get("summary", ""), "basics")

    # Array sections
    for section in ("work", "education", "projects"):
        if not show_sections.get(section):
            continue
        for entry in data.get(section, []):
            for key in ("company", "title", "institution", "degree", "field",
                        "name", "description"):
                val = entry.get(key)
                if isinstance(val, str):
                    _ingest(val, section)
            for h in entry.get("highlights", []):
                text = h if isinstance(h, str) else h.get("text", "")
                _ingest(text, section)
            for tag in entry.get("tags", []):
                _ingest(tag, section)

    # Skills
    if show_sections.get("skills"):
        for group in data.get("skills", []):
            _ingest(group.get("category", ""), "skills")
            for item in group.get("items", []):
                name = item if isinstance(item, str) else item.get("name", "")
                _ingest(name, "skills")

    return result


# ── Placement suggestions ──────────────────────────────────────────

_SINGLE_TOKEN_RE = re.compile(r"^[a-z0-9+#.]+$")


def _suggest_section(keyword: str) -> str:
    """Recommend which CV section a gap keyword should be added to.

    Single short tokens that look like tool/tech names go to 'skills';
    everything else goes to 'work' highlights.
    """
    if _SINGLE_TOKEN_RE.match(keyword) and len(keyword) <= 20:
        return "skills"
    return "work"


# ── Reorder hints ─────────────────────────────────────────────────


def _score_entry_jd(entry: dict[str, Any], jd_keywords: set[str]) -> int:
    """Count JD keywords appearing in an entry's title, company, and highlights."""
    parts: list[str] = [entry.get("title", ""), entry.get("company", "")]
    for h in entry.get("highlights", []):
        parts.append(h if isinstance(h, str) else h.get("text", ""))
    text = " ".join(parts).lower()
    return sum(1 for kw in jd_keywords if kw in text)


def _build_reorder_hints(
    work: list[dict[str, Any]],
    jd_keywords: set[str],
) -> list[str]:
    if len(work) < 2:
        return []
    scores = [_score_entry_jd(e, jd_keywords) for e in work]
    best_idx = scores.index(max(scores))
    if best_idx == 0:
        return []
    best = work[best_idx]
    current = work[0]
    best_label = f"{best.get('title', '')} at {best.get('company', '')}"
    current_label = f"{current.get('title', '')} at {current.get('company', '')}"
    return [
        f"Work: move '{best_label}' before '{current_label}' "
        f"({scores[best_idx]} vs {scores[0]} JD keyword matches)"
    ]


# ── Public API ─────────────────────────────────────────────────────


def analyze_match(resolved: ResolvedProfile, jd_text: str) -> MatchReport:
    """Compare JD keywords against resolved CV data.

    Returns a :class:`MatchReport` with matched keywords, gaps, and coverage.
    """
    jd_kw = _extract_keywords(jd_text)
    if not jd_kw:
        return MatchReport(
            matched=[], gaps=[], jd_word_count=0,
            cv_keywords_coverage=0.0, top_jd_keywords=[],
        )

    cv_kw = _extract_cv_keywords(resolved.data, resolved.show_sections)

    matched: list[KeywordMatch] = []
    gaps: list[str] = []

    for keyword, freq in sorted(jd_kw.items(), key=lambda x: -x[1]):
        if keyword in cv_kw:
            cv_freq = sum(
                1 for section in cv_kw[keyword]
                for _ in _TOKEN_RE.findall(keyword)
            )
            matched.append(KeywordMatch(
                keyword=keyword,
                found_in=sorted(cv_kw[keyword]),
                frequency_jd=freq,
                frequency_cv=cv_freq,
            ))
        else:
            gaps.append(keyword)

    total_unique = len(jd_kw)
    coverage = len(matched) / total_unique if total_unique > 0 else 0.0

    top_jd = sorted(jd_kw.items(), key=lambda x: -x[1])[:20]

    suggestions = {gap: _suggest_section(gap) for gap in gaps}

    work = resolved.data.get("work", [])
    if not resolved.show_sections.get("work", True):
        work = []
    all_jd_kw = {kw for kw, _ in top_jd}
    reorder_hints = _build_reorder_hints(work, all_jd_kw)

    return MatchReport(
        matched=matched,
        gaps=gaps,
        jd_word_count=sum(jd_kw.values()),
        cv_keywords_coverage=coverage,
        top_jd_keywords=top_jd,
        suggestions=suggestions,
        reorder_hints=reorder_hints,
    )
