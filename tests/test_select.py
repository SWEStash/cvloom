"""Tests for per-section content selection."""

from __future__ import annotations

from typing import Any

import pytest

from cvloom.select import apply_selection


def _data() -> dict[str, Any]:
    return {
        "work": [
            {"company": "Cloud Co", "tags": ["cloud", "devops"]},
            {"company": "AI Lab", "tags": ["ai"]},
            {"company": "Untagged Inc"},
            {"company": "Empty Tags", "tags": []},
        ],
        "education": [{"institution": "Uni"}],
        "projects": [{"name": "p1", "tags": ["ai"]}],
        "publications": [],
        "certifications": [],
        "awards": [],
        "languages": [],
        "skills": [
            {"category": "Languages", "items": ["Python"]},
            {"category": "Cloud", "items": ["AWS"]},
            {"category": "Tools", "items": ["Docker"]},
        ],
    }


def _companies(data: dict[str, Any]) -> list[str]:
    return [e["company"] for e in data["work"]]


def _categories(data: dict[str, Any]) -> list[str]:
    return [g["category"] for g in data["skills"]]


# ── entry sections ───────────────────────────────────────────────────


def test_no_selector_leaves_everything() -> None:
    data = _data()
    assert apply_selection(data, {}) == []
    assert len(_companies(data)) == 4


def test_unnamed_section_is_untouched() -> None:
    """Selection is opt-in per section — that is what makes strict safe."""
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert data["education"] == [{"institution": "Uni"}]
    assert data["projects"] == [{"name": "p1", "tags": ["ai"]}]


def test_include_list_keeps_only_matching() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert _companies(data) == ["Cloud Co"]


def test_entry_matches_on_any_of_its_tags() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": ["devops"]}})
    assert _companies(data) == ["Cloud Co"]


def test_multiple_selector_tags_are_a_union() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud", "ai"]}})
    assert _companies(data) == ["Cloud Co", "AI Lab"]


def test_untagged_entries_do_not_match_an_include_list() -> None:
    """An include list is a query; untagged content answers no query."""
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert "Untagged Inc" not in _companies(data)


def test_empty_tag_list_counts_as_untagged() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert "Empty Tags" not in _companies(data)


def test_empty_selector_list_is_no_constraint() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": []}})
    assert len(_companies(data)) == 4


@pytest.mark.parametrize("section", ["work", "education", "projects"])
def test_strict_semantics_are_uniform_across_sections(section: str) -> None:
    """`projects` used to be the only strict section; the exception is gone."""
    data = _data()
    apply_selection(data, {section: {"tags": ["nonexistent"]}})
    assert data[section] == []


# ── warnings ─────────────────────────────────────────────────────────


def test_warns_when_untagged_entries_are_dropped() -> None:
    """The safety net: a new, untagged entry vanishing must not be silent."""
    warnings = apply_selection(_data(), {"work": {"tags": ["cloud"]}})
    assert any("dropped 2 entries that carry no tags" in w for w in warnings)


def test_untagged_warning_is_singular_for_one_entry() -> None:
    data = _data()
    data["work"] = [{"company": "A", "tags": ["cloud"]}, {"company": "B"}]
    warnings = apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert any("dropped 1 entry that carries no tags" in w for w in warnings)


def test_no_untagged_warning_when_everything_is_tagged() -> None:
    data = _data()
    data["work"] = [{"company": "A", "tags": ["cloud"]}, {"company": "B", "tags": ["ai"]}]
    warnings = apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert not any("carry no tags" in w or "carries no tags" in w for w in warnings)


def test_warns_when_a_selector_matches_nothing() -> None:
    warnings = apply_selection(_data(), {"work": {"tags": ["nonexistent"]}})
    assert any("no entry matches" in w for w in warnings)


def test_warns_on_unknown_section() -> None:
    warnings = apply_selection(_data(), {"hobbies": {"tags": ["x"]}})
    assert any("unknown section 'hobbies'" in w for w in warnings)


def test_warns_on_unknown_skill_category() -> None:
    warnings = apply_selection(_data(), {"skills": {"categories": ["Nonexistent"]}})
    assert any("unknown category 'Nonexistent'" in w for w in warnings)


# ── skills ───────────────────────────────────────────────────────────


def test_skills_categories_keeps_only_listed() -> None:
    data = _data()
    apply_selection(data, {"skills": {"categories": ["Languages", "Cloud"]}})
    assert _categories(data) == ["Languages", "Cloud"]


def test_skills_exclude_categories_drops_listed() -> None:
    data = _data()
    apply_selection(data, {"skills": {"exclude_categories": ["Tools"]}})
    assert _categories(data) == ["Languages", "Cloud"]


def test_skills_exclusion_wins_over_inclusion() -> None:
    """Unlike tags, categories are a closed set, so the two compose."""
    data = _data()
    apply_selection(
        data,
        {"skills": {"categories": ["Languages", "Cloud"], "exclude_categories": ["Cloud"]}},
    )
    assert _categories(data) == ["Languages"]


def test_skills_untouched_without_a_selector() -> None:
    data = _data()
    apply_selection(data, {"work": {"tags": ["cloud"]}})
    assert len(_categories(data)) == 3


def test_skills_preserve_declared_order() -> None:
    data = _data()
    apply_selection(data, {"skills": {"categories": ["Tools", "Languages"]}})
    assert _categories(data) == ["Languages", "Tools"]
