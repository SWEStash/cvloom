"""Tests for template renderer."""

from pathlib import Path

import pytest

from cvloom.renderer import render_template


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    t = tmp_path / "templates"
    (t / "cv").mkdir(parents=True)
    (t / "cv" / "test.html.j2").write_text(
        "<html><body>{{ contact.name }}</body></html>"
    )
    return t


def test_render_basic(templates_dir: Path) -> None:
    html = render_template(
        "cv/test",
        {"contact": {"name": "Jane Smith"}},
        templates_dir=templates_dir,
    )
    assert "Jane Smith" in html


def test_render_appends_extension(templates_dir: Path) -> None:
    html = render_template(
        "cv/test.html.j2",
        {"contact": {"name": "Jane"}},
        templates_dir=templates_dir,
    )
    assert "Jane" in html


def test_render_missing_template(templates_dir: Path) -> None:
    with pytest.raises(SystemExit):
        render_template("cv/nonexistent", {}, templates_dir=templates_dir)
