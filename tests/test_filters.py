"""Tests for Jinja2 custom filters."""

import jinja2
import pytest

from cvloom.filters import (
    date_range,
    icon,
    link_anchor,
    link_icon,
    md_to_html,
    register_filters,
    skill_level_bar,
)


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
    assert date_range("2020-01", "2022-03") == "2020-01 - 2022-03"


def test_date_range_no_end():
    assert date_range("2020-01", None) == "2020-01 - Present"


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
    assert date_range("2019", "2022") == "2019 - 2022"


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


# ── link_icon ────────────────────────────────────────────────────────


def test_link_icon_renders_the_github_mark_for_a_github_url():
    svg = link_icon({"label": "GitHub", "url": "https://github.com/jane"})
    assert "<svg" in svg
    assert 'class="contact-icon contact-icon-github"' in svg


def test_link_icon_renders_the_linkedin_mark_for_a_linkedin_url():
    svg = link_icon({"label": "LinkedIn", "url": "https://www.linkedin.com/in/jane/"})
    assert 'class="contact-icon contact-icon-linkedin"' in svg


def test_link_icon_falls_back_to_a_globe_for_an_unrecognised_host():
    """A personal site or blog is the common case, not an error case."""
    svg = link_icon({"label": "Blog", "url": "https://jane.dev"})
    assert 'class="contact-icon contact-icon-globe"' in svg


def test_link_icon_puts_no_text_in_the_pdf_layer():
    """The whole reason SVG is the only workable icon technology here.

    An emoji or an icon-font glyph is a character, so an extractor reads it as
    part of the address next to it. A path is geometry and contributes nothing.
    """
    svg = str(link_icon({"label": "GitHub", "url": "https://github.com/jane"}))
    assert "<title" not in svg
    assert "<text" not in svg


def test_link_icon_is_decorative_for_screen_readers():
    """The anchor text already says where the link goes; the icon must not repeat it."""
    svg = str(link_icon({"label": "GitHub", "url": "https://github.com/jane"}))
    assert 'aria-hidden="true"' in svg
    assert 'focusable="false"' in svg


def test_link_icon_of_a_urlless_link_is_empty():
    assert link_icon({"label": "Broken"}) == ""


def test_icon_renders_a_named_mark():
    """Email, phone and location have no URL to derive from, so templates name the mark."""
    assert 'class="contact-icon contact-icon-envelope"' in icon("envelope")
    assert 'class="contact-icon contact-icon-phone"' in icon("phone")
    assert 'class="contact-icon contact-icon-globe-americas"' in icon("globe-americas")


def test_icon_renders_every_path_of_a_multi_path_mark():
    """The handset is a body plus its home button; one <path> renders half a mark."""
    assert str(icon("phone")).count("<path") == 2


def test_icon_rejects_an_unknown_name():
    """A typo in a template must fail the build, not render a silent blank."""
    with pytest.raises(KeyError):
        icon("envlope")


def test_link_icon_survives_autoescape():
    """`skill_level_bar` shipped this bug: a plain str renders as visible source."""
    html = _render("{{ link | link_icon }}", link={"url": "https://github.com/jane"})
    assert html.startswith("<svg")


def test_date_range_accepts_an_ascii_separator():
    """ASCII-first templates pass sep="-" so the whole line stays ASCII."""
    assert date_range("2020-01", "2022-03", sep="-") == "2020-01 - 2022-03"


def test_date_range_ascii_separator_still_collapses_identical_dates():
    assert date_range("2017", "2017", sep="-") == "2017"


def test_date_range_ascii_separator_handles_present():
    assert date_range("2020-01", None, sep="-") == "2020-01 - Present"
