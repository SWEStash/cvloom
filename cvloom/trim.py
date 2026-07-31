"""Page trim report — per-section word breakdown and cut recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field

from cvloom import sections
from cvloom.models import ResolvedProfile

_WORDS_PER_PAGE = 350

# Default page target, shared by the CLI's `--target-pages`, its post-build warning,
# the `wl-011` lint rule, and the `trim_report` MCP tool — they disagreed once and the
# tool told users two different things about the same CV.
MAX_PAGES = 3


# ── Data structures ─────────────────────────────────────────────────


@dataclass
class EntryWordCount:
    """Word count for a single entry (job, project, etc.)."""

    label: str
    total_words: int
    highlight_count: int
    longest_highlight_words: int


@dataclass
class SectionWordCount:
    """Word count breakdown for a CV section."""

    section: str
    total_words: int
    entries: list[EntryWordCount] = field(default_factory=list)


@dataclass
class TrimReport:
    """Complete trim analysis for a resolved profile."""

    total_words: int
    estimated_pages: int
    target_pages: int
    words_to_cut: int
    sections: list[SectionWordCount] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Helpers ─────────────────────────────────────────────────────────


def _count_words(text: str) -> int:
    return len(text.split())


def _analyze_array_section(
    section: str,
    entries: list[dict],  # type: ignore[type-arg]
) -> SectionWordCount:
    """Count words for an array section (work, education, projects)."""
    total = 0
    entry_counts: list[EntryWordCount] = []

    for entry in entries:
        words = sum(_count_words(text) for text in sections.iter_entry_text(entry))

        highlights = entry.get("highlights", [])
        longest_hl = max(
            (_count_words(sections.highlight_text(hl)) for hl in highlights),
            default=0,
        )

        entry_counts.append(
            EntryWordCount(
                label=sections.entry_label(section, entry),
                total_words=words,
                highlight_count=len(highlights),
                longest_highlight_words=longest_hl,
            )
        )
        total += words

    return SectionWordCount(section=section, total_words=total, entries=entry_counts)


def _analyze_skills(skills: list[dict]) -> SectionWordCount:  # type: ignore[type-arg]
    """Count words in the skills section."""
    total = 0
    for group in skills:
        total += _count_words(group.get("category", ""))
        for item in group.get("items", []):
            total += _count_words(sections.skill_name(item))
    return SectionWordCount(section="skills", total_words=total)


# ── Recommendations ─────────────────────────────────────────────────


def _generate_recommendations(
    sections: list[SectionWordCount],
    words_to_cut: int,
) -> list[str]:
    """Generate actionable trim recommendations."""
    if words_to_cut <= 0:
        return ["Your CV fits within the target page count."]

    recs: list[str] = []
    recs.append(f"Cut ~{words_to_cut} words to fit within target.")

    # Collect all entries across sections, sorted by word count desc
    all_entries: list[tuple[str, EntryWordCount]] = []
    for sec in sections:
        for entry in sec.entries:
            all_entries.append((sec.section, entry))
    all_entries.sort(key=lambda x: x[1].total_words, reverse=True)

    if all_entries:
        sec_name, top = all_entries[0]
        recs.append(
            f"Largest entry: {top.label} ({sec_name}) — {top.total_words} words, "
            f"{top.highlight_count} bullet(s). Consider trimming or removing."
        )

    # Flag entries with high word-per-bullet ratio
    for sec_name, entry in all_entries:
        if entry.highlight_count > 0 and entry.total_words / entry.highlight_count > 20:
            recs.append(
                f"{entry.label} ({sec_name}): ~{entry.total_words // entry.highlight_count} "
                f"words/bullet — consider tightening."
            )
            if len(recs) >= 5:
                break

    # Skills suggestion
    for sec in sections:
        if sec.section == "skills" and sec.total_words > 50:
            recs.append(
                f"Skills section: {sec.total_words} words. "
                "Consider removing categories or items that are less relevant."
            )

    return recs


# ── Public API ──────────────────────────────────────────────────────


def analyze(resolved: ResolvedProfile, target_pages: int = MAX_PAGES) -> TrimReport:
    """Analyze word counts and generate trim recommendations."""
    section_counts: list[SectionWordCount] = []

    for section in sections.ARRAY_SECTIONS:
        if resolved.show_sections.get(section):
            entries = resolved.data.get(section, [])
            section_counts.append(_analyze_array_section(section, entries))

    if resolved.show_sections.get("skills"):
        section_counts.append(_analyze_skills(resolved.data.get("skills", [])))

    total_words = sum(s.total_words for s in section_counts)
    # Add basics words
    basics = resolved.data.get("basics", {})
    for key in ("headline", "summary"):
        val = basics.get(key)
        if isinstance(val, str):
            total_words += _count_words(val)

    estimated_pages = max(1, round(total_words / _WORDS_PER_PAGE))
    target_words = target_pages * _WORDS_PER_PAGE
    words_to_cut = max(0, total_words - target_words)

    recommendations = _generate_recommendations(section_counts, words_to_cut)

    return TrimReport(
        total_words=total_words,
        estimated_pages=estimated_pages,
        target_pages=target_pages,
        words_to_cut=words_to_cut,
        sections=section_counts,
        recommendations=recommendations,
    )
