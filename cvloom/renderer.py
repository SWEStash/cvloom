"""Jinja2 template rendering for CV outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from cvloom import locale as locale_mod
from cvloom.filters import register_filters
from cvloom.locale import LocalePack

# Packaged templates live alongside this module in cvloom/templates/.
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _make_env(templates_dir: Path, locale: LocalePack | None = None) -> jinja2.Environment:
    loader = jinja2.FileSystemLoader(str(templates_dir))
    env = jinja2.Environment(
        loader=loader,
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.StrictUndefined,
    )
    # A global rather than a context key: templates and filters read the pack
    # unconditionally, so a caller that passes no locale must still get one
    # instead of an UndefinedError under StrictUndefined.
    env.globals["locale"] = locale if locale is not None else locale_mod.default_pack()
    register_filters(env)
    return env


def template_exists(template_name: str, templates_dir: Path | None = None) -> bool:
    """Return True if *template_name* exists in the templates directory."""
    if templates_dir is None:
        templates_dir = _TEMPLATES_DIR
    if not template_name.endswith(".html.j2"):
        template_name = f"{template_name}.html.j2"
    return (templates_dir / template_name).exists()


def list_templates(templates_dir: Path | None = None) -> list[str]:
    """Return sorted list of available template names (without .html.j2 extension)."""
    if templates_dir is None:
        templates_dir = _TEMPLATES_DIR
    return sorted(
        str(p.relative_to(templates_dir)).removesuffix(".html.j2")
        for p in templates_dir.rglob("*.html.j2")
        if p.name != "base.html.j2"
    )


def render_template(
    template_name: str,
    context: dict[str, Any],
    templates_dir: Path | None = None,
    locale: LocalePack | None = None,
) -> str:
    """Render *template_name* (e.g. ``'cv/ats-clean'``) with *context*.

    The ``.html.j2`` extension is appended automatically if not already present.
    *locale* supplies the document-facing strings the templates no longer
    hardcode — section headings, ``<html lang>``, the open-ended end date. It
    defaults to the ``en`` pack, so a caller that has none still renders.
    """
    if templates_dir is None:
        templates_dir = _TEMPLATES_DIR

    if not template_name.endswith(".html.j2"):
        template_name = f"{template_name}.html.j2"

    env = _make_env(templates_dir, locale)
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound:
        available = sorted(
            str(p.relative_to(templates_dir)) for p in templates_dir.rglob("*.html.j2")
        )
        raise SystemExit(
            f"Template '{template_name}' not found in {templates_dir}.\n"
            f"Available templates: {', '.join(available) or 'none'}"
        )

    return template.render(**context)
