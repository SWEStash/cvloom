"""Tests for profile-level section heading overrides."""

from __future__ import annotations

import pytest

from cvloom import renderer, sections, templates_meta
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
def test_headings_default_to_the_locale_pack(template: str) -> None:
    """With no override, every template heads a section with the pack's wording."""
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


def test_executive_darks_own_wording_is_now_a_suggestion() -> None:
    """The pack's flat default wins; the design's vocabulary is opt-in.

    Two mechanisms competing for the same heading is what F7's amendment
    removed. `templates_meta.suggested_titles` carries "Core Competencies" now,
    and a profile applies it — see `test_templates_meta.py`.
    """
    html = renderer.render_template("cv/executive-dark", {**_FULL_CONTEXT, "section_titles": {}})
    assert "Core Competencies" not in html
    assert ">Skills<" in html

    suggested = templates_meta.TEMPLATES["cv/executive-dark"].suggested_titles
    ctx = {**_FULL_CONTEXT, "section_titles": dict(suggested)}
    assert "Core Competencies" in renderer.render_template("cv/executive-dark", ctx)


def test_cert_groups_yields_a_stable_key_per_group() -> None:
    """The visible heading belongs to the pack and the profile, not to the filter."""
    groups = cert_groups(
        [
            {"name": "CKA", "issuer": "CNCF", "type": "certification"},
            {"name": "FP in Scala", "issuer": "Coursera", "type": "course"},
        ]
    )
    assert [key for key, _ in groups] == ["certifications", "professional_development"]


def test_every_title_key_is_accepted_by_the_profile_schema() -> None:
    """A key the templates use but the schema rejects is a silent dead end."""
    import json
    from pathlib import Path

    doc = json.loads((Path("cvloom/schemas/profile.json")).read_text())
    allowed = doc["properties"]["section_titles"]["propertyNames"]["enum"]
    assert set(allowed) == set(sections.TITLE_KEYS)
