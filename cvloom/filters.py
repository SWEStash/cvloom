"""Custom Jinja2 filters for CV templates."""

from __future__ import annotations

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from cvloom import dates, icons, links, sections
from cvloom import locale as locale_mod
from cvloom.locale import LocalePack


def _locale_of(ctx: jinja2.runtime.Context) -> LocalePack:
    """The pack a template is rendering under.

    ``renderer`` installs it as a Jinja global, so this only falls back for a
    caller that built its own environment.
    """
    pack = ctx.get("locale")
    return pack if isinstance(pack, LocalePack) else locale_mod.default_pack()


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


@jinja2.pass_context
def date_range(ctx: jinja2.runtime.Context, start: str, end: str | None, sep: str = "-") -> str:
    """Format a date range, substituting the locale's word for a missing end date.

    Identical endpoints collapse to a single date: "2017", not "2017 - 2017".
    *sep* is an ASCII hyphen, and every output uses the same character.

    The open-ended word comes from the pack rather than a literal, and is read off
    the context so a caller that supplied no locale still renders — the renderer
    puts the ``en`` pack there by default.
    """
    end_str = end if end else _locale_of(ctx).ongoing.render
    if end_str == start:
        return start
    return f"{start} {sep} {end_str}"


@jinja2.pass_context
def duration(ctx: jinja2.runtime.Context, start: str, end: str | None) -> str:
    """Format the tenure a date range covers: ``(2 years 3 months)``.

    Both the arithmetic and the wording come from elsewhere — :mod:`cvloom.dates`
    counts the months against the current one, the pack's ``duration`` block
    writes them out — so this filter is only the join between them.

    Returns ``""`` when the span is not computable: dates are free strings by
    schema, so ``summer 2020`` is legal data that no arithmetic can read. A
    template tests the result rather than getting a broken suffix, and
    ``builder.resolve`` separately warns about the entry, since a filter cannot
    reach ``ResolvedProfile.warnings``.
    """
    pack = _locale_of(ctx)
    total = dates.span_months(start, end, pack.ongoing)
    return pack.duration.render(total) if total else ""


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


def cert_groups(entries: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    """Yield ``(title_key, entries)`` per certification group.

    `certifications` renders as two headed groups, so the key is what a template
    passes to `section_title` — the visible heading belongs to the locale pack and
    to a profile's overrides, not to this filter.
    """
    return sections.group_certifications(entries)


@jinja2.pass_context
def section_title(ctx: jinja2.runtime.Context, key: str, default: str | None = None) -> str:
    """Resolve a section heading: profile override, else locale pack, else *default*.

    The packaged templates pass no *default* — the pack owns the wording, and
    per-template wording is a suggestion surfaced by `list-templates` that a user
    applies through `profile.section_titles`. *default* stays available for a
    user's own template using a key the pack does not carry.

    Both `section_titles` and `locale` are read off the Jinja context, so a
    template still renders when the caller supplies neither.
    """
    overrides = ctx.get("section_titles") or {}
    pack_title = _locale_of(ctx).section_titles.get(key)
    return str(overrides.get(key) or pack_title or default or key)


@jinja2.pass_context
def cover_letter_text(ctx: jinja2.runtime.Context, key: str) -> str:
    """Resolve a piece of cover-letter furniture: profile override, else pack.

    The same two-source rule `section_title` uses, minus the template-suggestion
    layer, which has no analogue here. The override lives in `job_context`
    because a greeting is a fact about the application, not about the language:
    `Estimado` / `Estimada` / `Estimados` depend on who is being written to.

    `fallback_salutee` has no override on purpose — it is only reached when
    `job_context.hiring_manager` is unset, and a user who wants other wording
    there sets `hiring_manager` itself.
    """
    override = (ctx.get("job_context") or {}).get(key)
    return str(override or _locale_of(ctx).cover_letter.get(key) or key)


def register_filters(env: jinja2.Environment) -> None:
    """Register all custom filters and globals onto *env*."""
    env.globals["section_title"] = section_title
    env.globals["cover_letter_text"] = cover_letter_text
    env.globals["icon"] = icon
    env.filters["md"] = md_to_html
    env.filters["date_range"] = date_range
    env.filters["duration"] = duration
    env.filters["skill_level_bar"] = skill_level_bar
    env.filters["cert_groups"] = cert_groups
    # Registered straight from `sections` — the exporters need the same join, and
    # nothing about the Jinja side reshapes it.
    env.filters["degree_line"] = sections.degree_line
    env.filters["link_anchor"] = link_anchor
    env.filters["link_icon"] = link_icon
