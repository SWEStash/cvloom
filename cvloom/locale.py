"""Locale packs: the document-facing defaults cvloom would otherwise hardcode.

A project declares one locale in ``cvloom.yaml``; this module turns that code
into a :class:`LocalePack`. Packs live in ``cvloom/locales/<code>.yaml`` and
govern the **rendered document only** — CLI and terminal output stay in English.

``en`` is an ordinary pack loaded through this same path, with no privileged
branch, so every build exercises the mechanism. It also serves as the fallback:
a key missing from another pack resolves to ``en``'s value and reports a warning;
a key missing from ``en`` is an error, since nothing is left to fall back to.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from cvloom import schema, sections
from cvloom.config import DEFAULT_LOCALE, ConfigError

_LOCALES_DIR = Path(__file__).parent / "locales"


@dataclass(frozen=True)
class Ongoing:
    """The open-ended end date, in both directions.

    ``render`` is written into the document by :func:`cvloom.filters.date_range`;
    ``accepts`` is parsed back out by the chronology lint rule and the JSON Resume
    export. The two are one field, not two: a pack that supplied only the rendered
    form would silently stop chronology ranking and open-ended date export from
    recognising its own output. Both are required by ``schemas/locale.json`` and
    by this class, so a half-populated one cannot be constructed.
    """

    render: str
    accepts: tuple[str, ...]

    def matches(self, value: str) -> bool:
        """Return True if *value* means "still ongoing" in this locale."""
        return value.strip().lower() in {a.lower() for a in self.accepts}


@dataclass(frozen=True)
class Duration:
    """How this locale writes a tenure: "2 years 3 months", "2 años 3 meses".

    Four words and two pieces of punctuation, because that is all `en` and `es`
    need — both pluralise regularly, and both put the span in parentheses after
    the date range. A locale with real plural *categories* (Polish, Arabic) does
    not fit this shape and would need the field to grow; nothing is lost by
    waiting until such a pack exists, and a four-key block is one a translator can
    fill in without reading any code.

    ``join`` and ``format`` are separate from the words so a locale can reshape
    the punctuation — ``"2 años y 3 meses"``, or brackets instead of parentheses —
    without the rendering logic knowing which locale it is serving.
    """

    year: str
    years: str
    month: str
    months: str
    join: str
    format: str

    def render(self, total_months: int) -> str:
        """Write *total_months* out, or ``""`` if there is nothing to say.

        A zero or negative total means the caller could not compute a span; it
        renders as nothing rather than as "0 months", so a template can test the
        result for truthiness instead of for a sentinel.
        """
        if total_months <= 0:
            return ""
        years, months = divmod(total_months, 12)
        parts = []
        if years:
            parts.append(f"{years} {self.year if years == 1 else self.years}")
        if months:
            parts.append(f"{months} {self.month if months == 1 else self.months}")
        return self.format.format(value=self.join.join(parts))


@dataclass(frozen=True)
class LocalePack:
    """Resolved locale pack. Carried on ``ResolvedProfile`` so renderer, linter,
    export and match all read the same values from one place."""

    code: str
    html_lang: str
    section_titles: Mapping[str, str]
    ongoing: Ongoing
    duration: Duration
    placeholder_contact: Mapping[str, str]
    cover_letter: Mapping[str, str]
    months: tuple[str, ...]
    date_format: str

    def format_date(self, value: date) -> str:
        """Render *value* the way this locale writes a date in a letter.

        A pure function of the pack: no host locale, no new dependency.
        ``strftime("%B")`` reads the C locale, so it is English whatever the
        project's ``locale:`` says.
        """
        return self.date_format.format(
            day=value.day, month=self.months[value.month - 1], year=value.year
        )


# Keys a pack file supplies, derived from LocalePack rather than restated. `code`
# is the filename, not file content, so it is not among them.
PACK_KEYS: tuple[str, ...] = tuple(f.name for f in fields(LocalePack) if f.name != "code")


def available_locales() -> list[str]:
    """Return the locale codes that ship with cvloom, sorted."""
    return sorted(p.stem for p in _LOCALES_DIR.glob("*.yaml"))


def _read_pack_file(code: str) -> dict[str, Any]:
    """Read and schema-validate one pack file. Raises ConfigError."""
    path = _LOCALES_DIR / f"{code}.yaml"
    if not path.exists():
        raise ConfigError(
            [
                f"Unknown locale '{code}'. "
                f"Available locales: {', '.join(available_locales()) or 'none'}"
            ]
        )

    try:
        with path.open() as f:
            raw: Any = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError([f"locales/{code}.yaml: not valid YAML: {exc}"]) from None

    if not isinstance(raw, dict):
        raise ConfigError([f"locales/{code}.yaml: expected a mapping of locale keys"])

    # Validated at load, so a malformed pack fails here with its path rather than
    # at render time with a confusing template error.
    errors = schema.validate("locale", raw, source_path=f"locales/{code}.yaml")
    if errors:
        raise ConfigError(errors)

    return raw


def _build_pack(code: str, raw: dict[str, Any]) -> LocalePack:
    """Freeze a validated pack mapping into a LocalePack.

    The mappings are wrapped read-only because ``load_pack`` is cached: every
    build shares one instance, so a caller mutating ``section_titles`` in place
    would change it for every later build in the process.
    """
    ongoing = raw["ongoing"]
    return LocalePack(
        code=code,
        html_lang=raw["html_lang"],
        section_titles=MappingProxyType(dict(raw["section_titles"])),
        ongoing=Ongoing(render=ongoing["render"], accepts=tuple(ongoing["accepts"])),
        duration=Duration(**raw["duration"]),
        placeholder_contact=MappingProxyType(dict(raw["placeholder_contact"])),
        cover_letter=MappingProxyType(dict(raw["cover_letter"])),
        months=tuple(raw["months"]),
        date_format=raw["date_format"],
    )


@cache
def load_pack(code: str) -> tuple[LocalePack, tuple[str, ...]]:
    """Load the pack for *code*, filling gaps from ``en``.

    Returns the pack and any warnings. Warnings are returned rather than printed
    so they reach the user through ``ResolvedProfile.warnings`` like every other
    advisory in the pipeline; this module does no terminal I/O.

    Raises :class:`~cvloom.config.ConfigError` for an unknown code, a malformed
    pack, or a key absent from both *code* and ``en``.
    """
    raw = _read_pack_file(code)
    warnings: list[str] = []

    if code != DEFAULT_LOCALE:
        base = _read_pack_file(DEFAULT_LOCALE)
        for key in PACK_KEYS:
            if key not in raw and key in base:
                raw[key] = base[key]
                warnings.append(
                    f"Locale '{code}' does not define '{key}'; using the {DEFAULT_LOCALE} value."
                )

    missing = [key for key in PACK_KEYS if key not in raw]
    if missing:
        raise ConfigError(
            [
                f"locales/{DEFAULT_LOCALE}.yaml is missing required key(s): "
                f"{', '.join(missing)}. "
                f"Every key the code looks up must have an {DEFAULT_LOCALE} default."
            ]
        )

    return _build_pack(code, raw), tuple(warnings)


def default_pack() -> LocalePack:
    """Return the ``en`` pack — the default for a project with no ``cvloom.yaml``."""
    return load_pack(DEFAULT_LOCALE)[0]


@dataclass(frozen=True)
class PackCoverage:
    """How much of the document surface a pack supplies in its own words.

    Both gaps are silent at render time, which is why they are reported: an
    inherited top-level key puts English into an otherwise translated document,
    and a missing title makes :func:`cvloom.filters.section_title` fall through
    to the raw key, heading a section ``work``.
    """

    code: str
    inherited_keys: tuple[str, ...]
    missing_titles: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.inherited_keys and not self.missing_titles


def pack_coverage(code: str) -> PackCoverage:
    """Report what *code*'s pack file defines itself and what it leaves to ``en``.

    Read from the pack file rather than from a loaded :class:`LocalePack`, which
    has already had the gaps filled in. ``load_pack`` reports the same top-level
    gaps as warnings, but those are prose meant for a user; this is the structured
    form ``list-locales`` tabulates. Nested title gaps have no warning at all —
    the fallback in ``load_pack`` is per top-level key.

    Raises :class:`~cvloom.config.ConfigError` for an unknown or malformed code.
    """
    raw = _read_pack_file(code)
    inherited = () if code == DEFAULT_LOCALE else tuple(k for k in PACK_KEYS if k not in raw)
    titles = raw.get("section_titles") or {}
    return PackCoverage(
        code=code,
        inherited_keys=inherited,
        missing_titles=tuple(k for k in sections.TITLE_KEYS if k not in titles),
    )
