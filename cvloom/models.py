"""Shared data structures for the build pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ResolvedProfile:
    """Result of loading a profile and resolving all data through the pipeline."""

    profile: dict[str, Any]
    data: dict[str, Any]
    show_sections: dict[str, bool]
    section_order: list[str]
    template_name: str
    output_filename: str


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
