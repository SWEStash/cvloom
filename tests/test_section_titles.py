"""Tests for profile-level section heading overrides."""

from __future__ import annotations

import pytest

from cvloom import renderer, sections
from cvloom.filters import cert_groups
from tests.test_renderer import _FULL_CONTEXT

_CV_TEMPLATES = [
    "cv/ats-clean",
    "cv/academic",
    "cv/modern-single",
    "cv/executive-dark",
    "cv/timeline-clean",
    "cv/sidebar-compact",
]


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_headings_default_to_the_templates_own_wording(template: str) -> None:
    """An empty override map must not flatten the templates into one voice."""
    html = renderer.render_template(template, {**_FULL_CONTEXT, "section_titles": {}})
    assert "Education" in html


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_profile_overrides_a_heading(template: str) -> None:
    ctx = {**_FULL_CONTEXT, "section_titles": {"work": "Professional Experience"}}
    html = renderer.render_template(template, ctx)
    assert "Professional Experience" in html


@pytest.mark.parametrize("template", _CV_TEMPLATES)
def test_missing_section_titles_key_still_renders(template: str) -> None:
    """`render_template` is public API; callers that never heard of headings must work.

    The lookup is a Jinja global reading the context, not a callable injected into
    it, precisely so a context without `section_titles` is not an UndefinedError
    under StrictUndefined.
    """
    ctx = dict(_FULL_CONTEXT)
    ctx.pop("section_titles", None)
    assert "Education" in renderer.render_template(template, ctx)


def test_executive_dark_keeps_its_own_skills_wording() -> None:
    """The design's vocabulary is a default, not something the feature overwrites."""
    html = renderer.render_template("cv/executive-dark", {**_FULL_CONTEXT, "section_titles": {}})
    assert "Core Competencies" in html
    assert ">Skills<" not in html


def test_cert_groups_yields_a_stable_key_per_group() -> None:
    """Reverse-mapping the visible heading would break once it is overridden."""
    groups = cert_groups(
        [
            {"name": "CKA", "issuer": "CNCF", "type": "certification"},
            {"name": "FP in Scala", "issuer": "Coursera", "type": "course"},
        ]
    )
    assert [(key, heading) for key, heading, _ in groups] == [
        ("certifications", sections.CREDENTIAL_HEADING),
        ("professional_development", sections.COURSEWORK_HEADING),
    ]


def test_every_title_key_is_accepted_by_the_profile_schema() -> None:
    """A key the templates use but the schema rejects is a silent dead end."""
    import json
    from pathlib import Path

    doc = json.loads((Path("cvloom/schemas/profile.json")).read_text())
    allowed = doc["properties"]["section_titles"]["propertyNames"]["enum"]
    assert set(allowed) == set(sections.TITLE_KEYS)
