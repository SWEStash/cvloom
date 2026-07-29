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


def test_every_section_accepts_tags() -> None:
    """Selection is uniform across sections, so every schema must allow `tags`."""
    for section in sections.SECTIONS:
        schema = json.loads((_SCHEMAS_DIR / f"{section.schema}.json").read_text())
        entry = schema["items"] if schema.get("type") == "array" else schema
        assert "tags" in entry["properties"], section.name


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


# ── certification type grouping ──────────────────────────────────────


def test_group_certifications_credentials_only() -> None:
    groups = sections.group_certifications(
        [{"name": "CKA", "type": "certification"}, {"name": "Licence", "type": "license"}]
    )
    assert [heading for heading, _ in groups] == ["Certifications"]
    assert len(groups[0][1]) == 2


def test_group_certifications_coursework_only() -> None:
    groups = sections.group_certifications(
        [
            {"name": "GenAI with LLMs", "type": "course"},
            {"name": "Nano", "type": "micro-credential"},
        ]
    )
    assert [heading for heading, _ in groups] == ["Professional Development"]


def test_group_certifications_mixed_puts_credentials_first() -> None:
    groups = sections.group_certifications(
        [
            {"name": "Course", "type": "course"},
            {"name": "Cert", "type": "certification"},
        ]
    )
    assert [heading for heading, _ in groups] == ["Certifications", "Professional Development"]
    assert groups[0][1][0]["name"] == "Cert"
    assert groups[1][1][0]["name"] == "Course"


def test_group_certifications_defaults_missing_type_to_credential() -> None:
    """Existing data has no `type`; it must keep rendering as a certification."""
    groups = sections.group_certifications([{"name": "Legacy cert"}])
    assert [heading for heading, _ in groups] == ["Certifications"]


def test_group_certifications_empty() -> None:
    assert sections.group_certifications([]) == []
