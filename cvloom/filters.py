"""Custom Jinja2 filters for CV templates."""

from __future__ import annotations

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from cvloom import icons, links, sections

# html=False escapes raw HTML in the source instead of passing it through, which
# is what makes the rendered output safe to mark as Markup below. CommonMark
# enables it by default; imported JSON Resume data is not necessarily trusted.
_md = MarkdownIt("commonmark", {"html": False})


def md_to_html(text: str) -> Markup:
    """Render a Markdown string to HTML (inline for single paragraphs).

    Returns :class:`Markup` so the generated tags survive Jinja's autoescape.
    """
    if not text:
        return Markup("")
    rendered: str = str(_md.render(text)).strip()
    # Unwrap single <p> tags for inline use
    if rendered.startswith("<p>") and rendered.endswith("</p>") and rendered.count("<p>") == 1:
        return Markup(rendered[3:-4])
    return Markup(rendered)


def date_range(start: str, end: str | None, sep: str = "-") -> str:
    """Format a date range, substituting 'Present' for a missing end date.

    Identical endpoints collapse to a single date: "2017", not "2017 - 2017".
    *sep* is an ASCII hyphen, and every output uses the same character.
    """
    end_str = end if end else "Present"
    if end_str == start:
        return start
    return f"{start} {sep} {end_str}"


def skill_level_bar(level: str) -> Markup:
    """Return an HTML span encoding skill proficiency as a CSS class.

    The level is carried entirely in a CSS class, so the bar puts no text in the
    PDF and no parser can read it; ``aria-label`` covers screen readers.
    """
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    n = level_map.get(level.lower(), 0) if level else 0
    return Markup('<span class="skill-level skill-level-{}" aria-label="{}"></span>').format(
        n, level
    )


def link_anchor(link: dict[str, str]) -> Markup:
    """Render a profile link as an anchor whose visible text is the URL itself.

    The visible text is the URL with the scheme and ``www.`` trimmed; the ``href``
    keeps the full URL, which WeasyPrint turns into a PDF link annotation.
    """
    url = str(link.get("url", ""))
    if not url:
        return Markup("")
    display = url.split("://", 1)[-1].removeprefix("www.").rstrip("/")
    return Markup('<a href="{}">{}</a>').format(url, display)


def icon(name: str, fill: str = "currentColor") -> Markup:
    """Render the decorative SVG mark registered under *name*.

    Raises :class:`KeyError` for an unknown name, so a typo in a template fails the
    build. The mark is ``aria-hidden`` decoration; the text beside it carries the
    address.

    *fill* must be a literal colour for anything that has to survive the PDF.
    WeasyPrint resolves no CSS against an inline SVG — ``currentColor``, a ``color``
    declaration and a ``fill`` declaration are all ignored and the path paints
    black — so a template on a dark ground passes its colour here rather than
    styling ``.contact-icon``.
    """
    paths = Markup("").join(Markup('<path d="{}"/>').format(d) for d in icons.ICON_PATHS[name])
    return Markup(
        '<svg class="contact-icon contact-icon-{}" viewBox="0 0 16 16" fill="{}"'
        ' aria-hidden="true" focusable="false">{}</svg>'
    ).format(name, fill, paths)


def link_icon(link: dict[str, str], fill: str = "currentColor") -> Markup:
    """Render the decorative SVG mark for a profile link.

    Derived from the URL via :func:`cvloom.links.network_of`; an unrecognised host
    gets the globe. *fill* behaves as in :func:`icon`.
    """
    url = str(link.get("url", ""))
    if not url:
        return Markup("")
    network = links.network_of(url)
    name = network.lower() if network else icons.FALLBACK
    return icon(name if name in icons.ICON_PATHS else icons.FALLBACK, fill)


def cert_groups(entries: list[dict[str, str]]) -> list[tuple[str, str, list[dict[str, str]]]]:
    """Yield ``(title_key, default_heading, entries)`` per certification group.

    The key is stable so a template can look up a profile's `section_titles`
    override without reverse-mapping the visible heading text.
    """
    return [
        (sections.CERT_GROUP_KEYS[heading], heading, group)
        for heading, group in sections.group_certifications(entries)
    ]


@jinja2.pass_context
def section_title(ctx: jinja2.runtime.Context, key: str, default: str) -> str:
    """Resolve a section heading: the profile's override, else the template's own.

    Reads `section_titles` off the Jinja context, so a template still renders when
    the caller supplies none. Templates pass their own wording as *default*.
    """
    overrides = ctx.get("section_titles") or {}
    return str(overrides.get(key) or default)


def register_filters(env: jinja2.Environment) -> None:
    """Register all custom filters and globals onto *env*."""
    env.globals["section_title"] = section_title
    env.globals["icon"] = icon
    env.filters["md"] = md_to_html
    env.filters["date_range"] = date_range
    env.filters["skill_level_bar"] = skill_level_bar
    env.filters["cert_groups"] = cert_groups
    env.filters["link_anchor"] = link_anchor
    env.filters["link_icon"] = link_icon
