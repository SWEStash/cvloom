"""Tests for Jinja2 custom filters."""

import jinja2
import pytest

from cvloom.filters import date_range, link_anchor, md_to_html, register_filters, skill_level_bar


def _render(source: str, **ctx: object) -> str:
    """Render *source* through an environment configured like the renderer's."""
    env = jinja2.Environment(autoescape=jinja2.select_autoescape(["html", "j2"]))
    register_filters(env)
    return env.from_string(source).render(**ctx)


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("Cut costs by **40%**.", "<strong>40%</strong>"),
        ("Maintainer of [cvloom](https://example.com).", '<a href="https://example.com">'),
        ("Shipped *faster* releases.", "<em>faster</em>"),
        ("First para.\n\nSecond para.", "<p>First para.</p>"),
    ],
)
def test_md_survives_autoescape(markdown, expected):
    """Markdown must reach the page as HTML, not as escaped literal tags.

    Regression: md_to_html returned a plain str, so Jinja's autoescape turned
    every generated tag into &lt;strong&gt; etc. Plain-text bullets hid it
    because the single-<p> unwrap left nothing to escape.
    """
    out = _render("{{ v | md }}", v=markdown)
    assert expected in out
    assert "&lt;" not in out


def test_md_still_escapes_raw_html_in_source():
    """Markdown rendering must not become an HTML injection hole."""
    out = _render("{{ v | md }}", v="Plain <script>alert(1)</script> text")
    assert "<script>" not in out


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


def test_date_range_collapses_identical_dates():
    """A degree known only by its completion year must not render "2017 – 2017"."""
    assert date_range("2017", "2017") == "2017"


def test_date_range_keeps_distinct_dates():
    assert date_range("2019", "2022") == "2019 – 2022"


# ── link_anchor ──────────────────────────────────────────────────────


def test_link_anchor_uses_the_url_as_its_visible_text():
    """ATS parsers that read visible text must get a URL, not a bare label."""
    html = link_anchor({"label": "GitHub", "url": "https://github.com/jane"})
    assert html == '<a href="https://github.com/jane">github.com/jane</a>'


def test_link_anchor_trims_www_and_trailing_slash_from_the_text_only():
    html = link_anchor({"label": "Site", "url": "https://www.jane.dev/"})
    assert 'href="https://www.jane.dev/"' in html
    assert ">jane.dev<" in html


def test_link_anchor_escapes_the_url():
    html = link_anchor({"label": "X", "url": 'https://x.com/"onmouseover='})
    assert '"onmouseover=' not in str(html)


def test_link_anchor_of_a_urlless_link_is_empty():
    assert link_anchor({"label": "Broken"}) == ""


def test_date_range_accepts_an_ascii_separator():
    """ASCII-first templates pass sep="-" so the whole line stays ASCII."""
    assert date_range("2020-01", "2022-03", sep="-") == "2020-01 - 2022-03"


def test_date_range_ascii_separator_still_collapses_identical_dates():
    assert date_range("2017", "2017", sep="-") == "2017"


def test_date_range_ascii_separator_handles_present():
    assert date_range("2020-01", None, sep="-") == "2020-01 - Present"
