"""Custom Jinja2 filters for CV templates."""

from __future__ import annotations

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from cvloom import sections

# html=False escapes raw HTML in the source instead of passing it through, which
# is what makes the rendered output safe to mark as Markup below. CommonMark
# enables it by default; imported JSON Resume data is not necessarily trusted.
_md = MarkdownIt("commonmark", {"html": False})


def md_to_html(text: str) -> Markup:
    """Render a Markdown string to HTML (inline for single paragraphs).

    Returns :class:`Markup` so the generated tags survive Jinja's autoescape.
    A plain ``str`` here is escaped into literal ``&lt;strong&gt;`` on the page,
    which is invisible for plain-text bullets (the single-``<p>`` unwrap leaves
    nothing to escape) but breaks every bold, link, and multi-paragraph field.
    """
    if not text:
        return Markup("")
    rendered: str = str(_md.render(text)).strip()
    # Unwrap single <p> tags for inline use
    if rendered.startswith("<p>") and rendered.endswith("</p>") and rendered.count("<p>") == 1:
        return Markup(rendered[3:-4])
    return Markup(rendered)


def date_range(start: str, end: str | None) -> str:
    """Format a date range, substituting 'Present' for a missing end date.

    Identical endpoints collapse to a single date: a qualification recorded
    only by the year it was awarded should read "2017", not "2017 – 2017".
    """
    end_str = end if end else "Present"
    if end_str == start:
        return start
    return f"{start} – {end_str}"


def skill_level_bar(level: str) -> str:
    """Return an HTML span encoding skill proficiency as a CSS class."""
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    n = level_map.get(level.lower(), 0) if level else 0
    return f'<span class="skill-level skill-level-{n}" aria-label="{level}"></span>'


def register_filters(env: jinja2.Environment) -> None:
    """Register all custom filters onto *env*."""
    env.filters["md"] = md_to_html
    env.filters["date_range"] = date_range
    env.filters["skill_level_bar"] = skill_level_bar
    env.filters["cert_groups"] = sections.group_certifications
