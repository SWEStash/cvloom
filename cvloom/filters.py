"""Custom Jinja2 filters for CV templates."""

from __future__ import annotations

import jinja2
from markdown_it import MarkdownIt

_md = MarkdownIt()


def md_to_html(text: str) -> str:
    """Render a Markdown string to HTML (inline for single paragraphs)."""
    if not text:
        return ""
    rendered: str = str(_md.render(text)).strip()
    # Unwrap single <p> tags for inline use
    if rendered.startswith("<p>") and rendered.endswith("</p>") and rendered.count("<p>") == 1:
        return rendered[3:-4]
    return rendered


def date_range(start: str, end: str | None) -> str:
    """Format a date range, substituting 'Present' for a missing end date."""
    end_str = end if end else "Present"
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
