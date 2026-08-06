"""Orchestrate: load → validate → render → write HTML + PDF."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from cvloom import config, loader, overlays, renderer, schema, sections, select
from cvloom import locale as locale_mod
from cvloom.locale import LocalePack
from cvloom.models import BuildResult, ResolvedProfile


class ResolveError(Exception):
    """A profile could not be resolved (profile/data validation, missing template).

    Carries the individual error messages so each frontend can present them.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "resolve failed")


def _estimate_pages(html: str) -> tuple[int, int]:
    """Strip HTML tags, count words, estimate pages at 350 words/page."""
    # Strip <style> blocks before removing tags so CSS tokens aren't counted.
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    words = len(text.split())
    pages = max(1, round(words / 350))
    return words, pages


def resolve(
    data_dir: Path,
    private_dir: Path,
    profiles_dir: Path,
    profile_name: str = "general",
    template_override: str | None = None,
    public: bool = False,
    locale: LocalePack | None = None,
    locale_warnings: list[str] | None = None,
) -> ResolvedProfile:
    """Run the pipeline up to rendering: load, filter, overlay, validate.

    Returns a :class:`ResolvedProfile` with fully resolved data.

    *locale* defaults to the ``en`` pack. This function takes three directories
    rather than a project root, so it cannot read ``cvloom.yaml`` itself —
    :func:`resolve_project` resolves the pack and passes it (with any fallback
    warnings) down, which keeps this function pure.
    """
    pack = locale if locale is not None else locale_mod.default_pack()

    # Load profile
    profile_path = profiles_dir / f"{profile_name}.yaml"
    profile = loader.load_profile(profile_path)

    # Validate profile against schema
    profile_errors = schema.validate(
        "profile", profile, source_path=f"profiles/{profile_name}.yaml"
    )
    if profile_errors:
        raise ResolveError(profile_errors)

    template_name = template_override or profile.get("template", "cv/ats-clean")

    if not renderer.template_exists(template_name):
        available = renderer.list_templates()
        raise ResolveError(
            [
                f"Template '{template_name}' not found. "
                f"Available templates: {', '.join(available) or 'none'}"
            ]
        )

    output_filename = profile.get("output_filename") or profile_name
    sections_cfg: dict[str, bool] = profile.get("sections", {}) or {}

    # Load data
    data = loader.load_data(data_dir=data_dir, private_dir=private_dir, public=public, locale=pack)

    # Narrow each section the profile names. Selection runs before anything
    # normalizes or patches the data, so overlays only ever see what survives.
    select_warnings = select.apply_selection(data, profile.get("select", {}) or {})

    # Fill schema-optional keys, then normalize highlights to {id, text} for
    # overlay processing.
    for section in sections.ARRAY_SECTIONS:
        entries = data.get(section, [])
        if entries:
            loader.normalize_optional_fields(section, entries)
            loader.normalize_highlights(entries)

    # Validate overlays before applying — warnings are returned to the caller,
    # not printed here (resolve() stays free of terminal I/O).
    overlay_warnings = overlays.validate_overlays(data, profile)

    # Apply overlays
    overlays.apply_overlays(data, profile)

    # Flatten highlights back to plain strings for templates
    for section in sections.ARRAY_SECTIONS:
        entries = data.get(section, [])
        if entries:
            loader.flatten_highlights(entries)

    # Apply section visibility
    show_sections = {
        **dict.fromkeys(sections.DEFAULT_SECTION_ORDER, True),
        **sections_cfg,
    }

    # Section ordering
    section_order = profile.get("section_order", list(sections.DEFAULT_SECTION_ORDER))

    # Heading text overrides. Schema restricts the keys, so anything here is known.
    section_titles: dict[str, str] = dict(profile.get("section_titles") or {})

    # Validate data
    data_errors = schema.validate_all(data, private_path=str(private_dir / "contact.yaml"))
    if data_errors:
        raise ResolveError(data_errors)

    return ResolvedProfile(
        profile=profile,
        data=data,
        show_sections=show_sections,
        section_order=section_order,
        section_titles=section_titles,
        template_name=template_name,
        output_filename=output_filename,
        warnings=(locale_warnings or []) + select_warnings + overlay_warnings,
        profile_name=profile_name,
        locale=pack,
    )


def resolve_project(
    root: Path,
    profile_name: str = "general",
    *,
    template_override: str | None = None,
    public: bool = False,
) -> ResolvedProfile:
    """Resolve a profile using the conventional ``data/``, ``private/``,
    ``profiles/`` layout under a project *root*.

    Thin wrapper over :func:`resolve` that fixes the directory convention and
    resolves the project's locale — the one place ``cvloom.yaml`` is read, so
    every frontend gets the same answer without asking for it.
    """
    pack, locale_warnings = project_locale(root)
    return resolve(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        profile_name=profile_name,
        template_override=template_override,
        public=public,
        locale=pack,
        locale_warnings=locale_warnings,
    )


def project_locale(root: Path) -> tuple[LocalePack, list[str]]:
    """Read ``cvloom.yaml`` and load the pack it names.

    Public because three entry points need it: :func:`resolve_project` and
    :func:`build_project` reach ``resolve`` by different routes, and
    ``mcp_server.validate_data`` validates a project without resolving one.

    Config problems surface as :class:`ResolveError` so callers keep catching one
    pipeline error type; ``config`` and ``locale`` stay free of it.
    """
    try:
        cfg = config.load_project_config(root)
        pack, warnings = locale_mod.load_pack(cfg.locale)
    except config.ConfigError as exc:
        raise ResolveError(exc.errors) from None
    return pack, list(warnings)


def build_project(
    root: Path,
    *,
    output_dir: Path | None = None,
    profile_name: str = "general",
    template_override: str | None = None,
    public: bool = False,
    templates_dir: Path | None = None,
    skip_pdf: bool = False,
) -> BuildResult:
    """Build a profile using the conventional project layout under *root*.

    Thin wrapper over :func:`build`; *output_dir* defaults to ``root/"dist"``.
    Resolves the project's locale for the same reason :func:`resolve_project`
    does — this is the other entry point that knows the root, and a build that
    skipped it would render with the wrong locale while ``check`` used the right
    one.
    """
    pack, locale_warnings = project_locale(root)
    return build(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        output_dir=output_dir if output_dir is not None else root / "dist",
        profile_name=profile_name,
        template_override=template_override,
        public=public,
        templates_dir=templates_dir,
        skip_pdf=skip_pdf,
        locale=pack,
        locale_warnings=locale_warnings,
    )


def _pdf_filename(resolved: ResolvedProfile) -> str:
    """Derive the PDF output stem from profile format string or contact name.

    The default carries a ``_<profile>`` suffix so building several profiles does
    not overwrite a single contact-derived stem.
    """
    name = resolved.data.get("contact", {}).get("name", "")
    parts = name.split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    profile = resolved.profile_name

    fmt = resolved.profile.get("pdf_filename_format")
    if fmt:
        return str(
            fmt.format(
                first=first,
                last=last,
                name=name.replace(" ", "_"),
                profile=profile,
            )
        )

    if name:
        stem = f"{first}_{last}_Resume" if last else f"{first}_Resume"
        return f"{stem}_{profile}" if profile else stem

    # No contact name: output_filename is already unique per profile.
    return resolved.output_filename


def build(
    data_dir: Path,
    private_dir: Path,
    profiles_dir: Path,
    output_dir: Path,
    profile_name: str = "general",
    template_override: str | None = None,
    public: bool = False,
    templates_dir: Path | None = None,
    skip_pdf: bool = False,
    locale: LocalePack | None = None,
    locale_warnings: list[str] | None = None,
) -> BuildResult:
    """Full build pipeline for one profile. Returns structured result."""
    resolved = resolve(
        data_dir=data_dir,
        private_dir=private_dir,
        profiles_dir=profiles_dir,
        profile_name=profile_name,
        template_override=template_override,
        public=public,
        locale=locale,
        locale_warnings=locale_warnings,
    )

    # Same StrictUndefined contract as the data sections: cover-letter
    # templates test job_context keys for truthiness, so they must all exist.
    job_context: dict[str, Any] = {
        **schema.entry_defaults("profile", "job_context"),
        **(resolved.profile.get("job_context") or {}),
    }

    # Build render context
    context: dict[str, Any] = {
        **resolved.data,
        "profile": resolved.profile,
        "show": resolved.show_sections,
        "section_order": resolved.section_order,
        # Read by the `section_title` Jinja global. Templates keep owning the
        # wording that suits their design; a profile overrides it without forking.
        "section_titles": resolved.section_titles,
        "job_context": job_context,
        "public": public,
        # Formatted from the pack, not `strftime("%B")`, which reads the C locale
        # and so dates a Spanish letter in English.
        "today": resolved.locale.format_date(date.today()),
    }

    # Render HTML
    html = renderer.render_template(
        resolved.template_name, context, templates_dir=templates_dir, locale=resolved.locale
    )

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{resolved.output_filename}.html"
    html_path.write_text(html, encoding="utf-8")

    pdf_path: Path | None = None
    if not skip_pdf:
        pdf_path = output_dir / f"{_pdf_filename(resolved)}.pdf"
        _render_pdf(html, pdf_path)

    words, pages = _estimate_pages(html)
    section_word_counts = sections.count_words(resolved)

    return BuildResult(
        resolved=resolved,
        html=html,
        html_path=html_path,
        pdf_path=pdf_path,
        words=words,
        pages=pages,
        section_word_counts=section_word_counts,
    )


def _render_pdf(html: str, output_path: Path) -> None:
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError:
        raise SystemExit("WeasyPrint is not installed. Install it with: uv pip install weasyprint")
    # Tagged output carries the logical reading order in a structure tree.
    HTML(string=html).write_pdf(str(output_path), pdf_tags=True)
