"""Guards on the section registry.

``sections.SECTIONS`` is the single source of truth for cvloom's entry-list
sections: loader, schema validation, builder, CLI summary and export headings
all derive from it. Two things it *cannot* derive are the JSON files —
``profile.json``'s ``sections`` / ``section_order`` and each section's own
schema — so these tests assert they stay in step. Without them, adding a
section and forgetting the profile schema fails silently at the one place a
user notices: their profile stops validating.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cvloom import sections

_SCHEMAS_DIR = Path(__file__).parent.parent / "cvloom" / "schemas"


@pytest.fixture(scope="module")
def profile_schema() -> dict:
    return json.loads((_SCHEMAS_DIR / "profile.json").read_text())


@pytest.mark.parametrize("section", sections.SECTIONS, ids=lambda s: s.name)
def test_every_section_has_its_entry_schema(section: sections.Section) -> None:
    assert (_SCHEMAS_DIR / f"{section.schema}.json").exists()


def test_profile_sections_match_registry(profile_schema: dict) -> None:
    """A profile must be able to toggle every section that exists."""
    toggles = set(profile_schema["properties"]["sections"]["properties"])
    assert toggles == set(sections.DEFAULT_SECTION_ORDER)


def test_profile_section_order_enum_matches_registry(profile_schema: dict) -> None:
    """...and order every section that exists."""
    enum = set(profile_schema["properties"]["section_order"]["items"]["enum"])
    assert enum == set(sections.DEFAULT_SECTION_ORDER)


def test_registry_names_are_unique() -> None:
    names = [s.name for s in sections.SECTIONS]
    assert len(names) == len(set(names))


def test_only_projects_filters_tags_strictly() -> None:
    """Strict filtering is only safe where `tags` is a required field."""
    strict = {s.name for s in sections.SECTIONS if s.strict_tags}
    assert strict == {"projects"}
    project_schema = json.loads((_SCHEMAS_DIR / "project.json").read_text())
    assert "tags" in project_schema["required"]


def test_lenient_sections_do_not_require_tags() -> None:
    """The converse: an untagged entry is only "always included" where it can exist."""
    for section in sections.SECTIONS:
        if section.strict_tags:
            continue
        schema = json.loads((_SCHEMAS_DIR / f"{section.schema}.json").read_text())
        entry = schema["items"] if schema.get("type") == "array" else schema
        assert "tags" not in entry.get("required", []), section.name


def test_default_order_leads_with_skills() -> None:
    """skills is not in the registry (bespoke shape) but must still be ordered."""
    assert sections.DEFAULT_SECTION_ORDER[0] == "skills"
    assert set(sections.DEFAULT_SECTION_ORDER) - set(sections.ARRAY_SECTIONS) == {"skills"}


def test_section_summary_covers_every_section() -> None:
    """The CLI's post-build summary must not silently omit a new section.

    It previously derived its *labels* from the registry but iterated a
    hardcoded list, so sections added later were counted by nobody.
    """
    from cvloom.cli import _section_summary

    data = {name: [{}] for name in sections.DEFAULT_SECTION_ORDER}
    show = dict.fromkeys(sections.DEFAULT_SECTION_ORDER, True)
    summary = _section_summary(data, show)

    labels = {"skills": "skills", **{s.name: s.summary_label for s in sections.SECTIONS}}
    for name in sections.DEFAULT_SECTION_ORDER:
        assert f"{labels[name]}×1" in summary, f"{name} missing from build summary"


def test_section_summary_respects_visibility() -> None:
    from cvloom.cli import _section_summary

    data = {name: [{}] for name in sections.DEFAULT_SECTION_ORDER}
    show = dict.fromkeys(sections.DEFAULT_SECTION_ORDER, True)
    show["awards"] = False
    assert "awards" not in _section_summary(data, show)
