"""Tests for builder utilities added in Phase 1."""

from __future__ import annotations

from cvloom.builder import _estimate_pages, _section_summary


def test_estimate_pages_single():
    html = "<p>" + " ".join(["word"] * 200) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 200
    assert pages == 1


def test_estimate_pages_two():
    html = "<p>" + " ".join(["word"] * 700) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 700
    assert pages == 2


def test_section_summary_all():
    data = {
        "work": [{}] * 3,
        "education": [{}] * 1,
        "skills": [{}] * 4,
        "projects": [{}] * 2,
    }
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert "work×3" in result
    assert "edu×1" in result
    assert "skills×4" in result
    assert "projects×2" in result


def test_section_summary_hidden():
    data = {
        "work": [{}] * 2,
        "education": [{}] * 1,
        "skills": [{}] * 3,
        "projects": [{}] * 5,
    }
    show = {"work": True, "education": False, "skills": True, "projects": False}
    result = _section_summary(data, show)
    assert "work×2" in result
    assert "edu" not in result
    assert "skills×3" in result
    assert "projects" not in result


def test_section_summary_empty_data():
    data: dict = {}
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert result == ""
