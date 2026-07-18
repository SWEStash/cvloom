"""Tests for Jinja2 custom filters."""

from cvloom.filters import date_range, md_to_html, skill_level_bar


def test_md_to_html_inline():
    assert md_to_html("Hello **world**") == "Hello <strong>world</strong>"


def test_md_to_html_empty():
    assert md_to_html("") == ""


def test_md_to_html_multiline():
    html = md_to_html("Line 1\n\nLine 2")
    assert "<p>" in html


def test_date_range_with_end():
    assert date_range("2020-01", "2022-03") == "2020-01 – 2022-03"


def test_date_range_no_end():
    assert date_range("2020-01", None) == "2020-01 – Present"


def test_skill_level_bar_expert():
    result = skill_level_bar("expert")
    assert "skill-level-4" in result


def test_skill_level_bar_empty():
    result = skill_level_bar("")
    assert "skill-level-0" in result
