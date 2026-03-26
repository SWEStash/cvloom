"""Tests for profile diff."""

from __future__ import annotations

from cvloom.diff import compare
from cvloom.models import ResolvedProfile


def _make_resolved(
    work: list | None = None,
    projects: list | None = None,
    skills: list | None = None,
    show: dict | None = None,
    template: str = "cv/ats-single",
) -> ResolvedProfile:
    return ResolvedProfile(
        profile={},
        data={
            "basics": {"headline": "Engineer", "summary": "A summary."},
            "work": work or [],
            "education": [],
            "skills": skills or [],
            "projects": projects or [],
            "contact": {"name": "Test", "email": "t@t.com"},
        },
        show_sections=show or {
            "work": True, "education": True, "skills": True, "projects": True,
        },
        section_order=["skills", "work", "education", "projects"],
        template_name=template,
        output_filename="cv",
    )


def test_identical_profiles():
    a = _make_resolved(work=[{"company": "Acme", "highlights": ["Built stuff."]}])
    b = _make_resolved(work=[{"company": "Acme", "highlights": ["Built stuff."]}])
    result = compare(a, b, "a", "b")
    assert result.sections_only_in_a == []
    assert result.sections_only_in_b == []
    assert result.entries_only_in_a == {}
    assert result.entries_only_in_b == {}
    assert result.word_count_a == result.word_count_b


def test_different_sections():
    a = _make_resolved(show={"work": True, "education": True, "skills": False, "projects": True})
    b = _make_resolved(show={"work": True, "education": True, "skills": True, "projects": False})
    result = compare(a, b, "a", "b")
    assert "projects" in result.sections_only_in_a
    assert "skills" in result.sections_only_in_b


def test_different_entries():
    a = _make_resolved(work=[
        {"company": "Acme", "highlights": ["A."]},
        {"company": "Beta", "highlights": ["B."]},
    ])
    b = _make_resolved(work=[
        {"company": "Acme", "highlights": ["A."]},
        {"company": "Gamma", "highlights": ["G."]},
    ])
    result = compare(a, b, "a", "b")
    assert "Beta" in result.entries_only_in_a.get("work", [])
    assert "Gamma" in result.entries_only_in_b.get("work", [])


def test_word_count_delta():
    a = _make_resolved(work=[
        {"company": "Acme", "highlights": ["Short."]},
    ])
    long_text = " ".join(["word"] * 50)
    b = _make_resolved(work=[
        {"company": "Acme", "highlights": [long_text]},
    ])
    result = compare(a, b, "a", "b")
    assert result.word_count_b > result.word_count_a


def test_highlight_count_diff():
    a = _make_resolved(work=[
        {"company": "Acme", "highlights": ["A.", "B.", "C."]},
    ])
    b = _make_resolved(work=[
        {"company": "Acme", "highlights": ["A."]},
    ])
    result = compare(a, b, "a", "b")
    assert result.highlight_count_a == 3
    assert result.highlight_count_b == 1


def test_template_difference():
    a = _make_resolved(template="cv/ats-single")
    b = _make_resolved(template="cv/modern-single")
    result = compare(a, b, "a", "b")
    assert result.template_a == "cv/ats-single"
    assert result.template_b == "cv/modern-single"


def test_project_entries_diff():
    a = _make_resolved(projects=[
        {"name": "alpha", "description": "A", "tags": ["python"]},
    ])
    b = _make_resolved(projects=[
        {"name": "alpha", "description": "A", "tags": ["python"]},
        {"name": "beta", "description": "B", "tags": ["go"]},
    ])
    result = compare(a, b, "a", "b")
    assert "beta" in result.entries_only_in_b.get("projects", [])


def test_hidden_section_not_compared():
    a = _make_resolved(
        work=[{"company": "Acme", "highlights": ["A."]}],
        show={"work": False, "education": True, "skills": True, "projects": True},
    )
    b = _make_resolved(
        work=[{"company": "Beta", "highlights": ["B."]}],
        show={"work": False, "education": True, "skills": True, "projects": True},
    )
    result = compare(a, b, "a", "b")
    assert "work" not in result.entries_only_in_a
    assert "work" not in result.entries_only_in_b
