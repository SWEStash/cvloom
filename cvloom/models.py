"""Shared data structures for the build pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cvloom.locale import LocalePack, default_pack


@dataclass
class ResolvedProfile:
    """Result of loading a profile and resolving all data through the pipeline.

    Invariant: highlights in ``work`` / ``education`` / ``projects`` entries are
    plain strings here (``loader.flatten_highlights`` runs during ``resolve``);
    the pre-flatten ``{id, text}`` form only exists inside loader/overlays.
    """

    profile: dict[str, Any]
    data: dict[str, Any]
    show_sections: dict[str, bool]
    section_order: list[str]
    template_name: str
    output_filename: str
    warnings: list[str] = field(default_factory=list)
    profile_name: str = ""
    """Profile this was resolved from — disambiguates per-profile output filenames."""

    section_titles: dict[str, str] = field(default_factory=dict)
    """Heading text overrides from the profile. Empty means every template default stands."""

    locale: LocalePack = field(default_factory=default_pack)
    """Document-facing locale pack, resolved from the project's ``cvloom.yaml``.

    Defaults to ``en`` so a ResolvedProfile built directly — in tests, or by a
    caller using :func:`~cvloom.builder.resolve` without a project root — behaves
    exactly as it did before locales existed.
    """


@dataclass
class BuildResult:
    """Result of a full build."""

    resolved: ResolvedProfile
    html: str
    html_path: Path | None
    pdf_path: Path | None
    words: int
    pages: int
    section_word_counts: dict[str, int] = field(default_factory=dict)
