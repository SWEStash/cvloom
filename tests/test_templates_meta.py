"""Tests for the template parse-risk registry."""

from __future__ import annotations

import pytest

from cvloom import renderer, templates_meta


def test_every_packaged_cv_template_is_rated() -> None:
    """An unrated CV template is the failure this registry exists to prevent.

    A template that ships without an entry falls through `info_for` as None and
    is reported "unrated", which reads to a user as "probably fine" — exactly the
    silent pass that a two-column layout must not get.
    """
    unrated = [
        name
        for name in renderer.list_templates()
        if name.startswith("cv/") and templates_meta.info_for(name) is None
    ]
    assert not unrated, f"CV templates missing a templates_meta entry: {unrated}"


def test_ratings_are_known_values() -> None:
    valid = {templates_meta.ATS_SAFE, templates_meta.ATS_CAUTION, templates_meta.ATS_UNSAFE}
    for name, meta in templates_meta.TEMPLATES.items():
        assert meta.ats in valid, f"{name} has rating {meta.ats!r}"


@pytest.mark.parametrize("name", ["cv/ats-clean", "cv/academic"])
def test_conservative_templates_are_safe_and_offline(name: str) -> None:
    meta = templates_meta.info_for(name)
    assert meta is not None
    assert meta.ats == templates_meta.ATS_SAFE
    assert meta.columns == 1
    assert meta.fonts == "system"


def test_multi_column_templates_are_never_rated_safe() -> None:
    """Two columns interleave under at least one extractor; styling cannot fix that.

    Whether *every* extractor is fooled decides `caution` versus `unsafe`, and that
    is measured in `tests/test_ats_ratings.py`. What is asserted here is only that a
    multi-column layout never claims to be safe.
    """
    for name, meta in templates_meta.TEMPLATES.items():
        if meta.columns > 1:
            assert meta.ats != templates_meta.ATS_SAFE, name


def test_non_safe_templates_explain_themselves() -> None:
    """A warning with no caveat text tells the user nothing actionable."""
    for name, meta in templates_meta.TEMPLATES.items():
        if meta.ats != templates_meta.ATS_SAFE:
            assert meta.caveat.strip(), f"{name} is rated {meta.ats} with no caveat"


def test_info_for_tolerates_the_j2_suffix() -> None:
    assert templates_meta.info_for("cv/ats-clean.html.j2") is templates_meta.info_for(
        "cv/ats-clean"
    )


def test_info_for_unknown_template_is_none() -> None:
    """A project's own template is unrated, not assumed safe."""
    assert templates_meta.info_for("cv/my-own-thing") is None
