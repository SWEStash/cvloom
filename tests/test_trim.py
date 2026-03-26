"""Tests for the page trim report."""

from __future__ import annotations

from cvloom.models import ResolvedProfile
from cvloom.trim import analyze


def _make_resolved(
    work: list | None = None,
    skills: list | None = None,
) -> ResolvedProfile:
    return ResolvedProfile(
        profile={},
        data={
            "basics": {"headline": "Engineer", "summary": "A summary."},
            "work": work or [],
            "education": [],
            "skills": skills or [],
            "projects": [],
            "contact": {"name": "Test", "email": "t@t.com"},
        },
        show_sections={"work": True, "education": True, "skills": True, "projects": True},
        section_order=["skills", "work", "education", "projects"],
        template_name="cv/ats-single",
        output_filename="cv",
    )


def test_analyze_empty():
    resolved = _make_resolved()
    report = analyze(resolved)
    assert report.total_words > 0  # basics still has words
    assert report.estimated_pages == 1


def test_analyze_counts_work_words():
    resolved = _make_resolved(work=[
        {
            "company": "Acme Corp",
            "title": "Engineer",
            "highlights": ["Built a scalable system processing events."],
        },
    ])
    report = analyze(resolved)
    work_sec = next(s for s in report.sections if s.section == "work")
    assert work_sec.total_words > 0
    assert len(work_sec.entries) == 1
    assert work_sec.entries[0].label == "Acme Corp"


def test_analyze_words_to_cut():
    # Create enough content to exceed 1 page (350 words)
    long_hl = " ".join(["word"] * 200)
    resolved = _make_resolved(work=[
        {"company": "A", "highlights": [long_hl]},
        {"company": "B", "highlights": [long_hl]},
        {"company": "C", "highlights": [long_hl]},
    ])
    report = analyze(resolved, target_pages=1)
    assert report.words_to_cut > 0
    assert report.estimated_pages > 1


def test_analyze_fits_target():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Built things."]},
    ])
    report = analyze(resolved, target_pages=2)
    assert report.words_to_cut == 0
    assert "fits within" in report.recommendations[0].lower()


def test_analyze_recommendations_largest_entry():
    long_hl = " ".join(["word"] * 300)
    resolved = _make_resolved(work=[
        {"company": "Big Co", "highlights": [long_hl]},
        {"company": "Small Co", "highlights": [" ".join(["x"] * 100)]},
    ])
    report = analyze(resolved, target_pages=1)
    rec_text = " ".join(report.recommendations)
    assert "Big Co" in rec_text


def test_analyze_skills_counted():
    resolved = _make_resolved(skills=[
        {"category": "Languages", "items": ["Python", "Go", "Rust"]},
        {"category": "Tools", "items": ["Docker", "Kubernetes"]},
    ])
    report = analyze(resolved)
    skills_sec = next(s for s in report.sections if s.section == "skills")
    assert skills_sec.total_words >= 5


def test_analyze_hidden_sections_excluded():
    resolved = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Built things."]},
    ])
    resolved.show_sections["work"] = False
    report = analyze(resolved)
    section_names = [s.section for s in report.sections]
    assert "work" not in section_names


def test_analyze_highlight_word_counts():
    resolved = _make_resolved(work=[
        {
            "company": "Acme",
            "highlights": [
                "One two three four five six seven eight.",
                "A B.",
            ],
        },
    ])
    report = analyze(resolved)
    work_sec = next(s for s in report.sections if s.section == "work")
    assert work_sec.entries[0].highlight_count == 2
    assert work_sec.entries[0].longest_highlight_words == 8
