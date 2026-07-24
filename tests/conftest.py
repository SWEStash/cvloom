"""Shared test factories.

Two builders that were previously copy-pasted across the suite:

- :func:`make_resolved` — a :class:`ResolvedProfile` for the analysis modules
  (diff / linter / match / trim / ai). Per-module test files keep their own thin
  ``_make_resolved`` wrapper (their historic signature) that delegates here, so
  the ResolvedProfile shape lives in exactly one place.
- :func:`make_project` — an on-disk ``data/`` + ``private/`` + ``profiles/``
  project tree in ``tmp_path`` for the CLI / MCP / loader integration tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cvloom.models import ResolvedProfile

_DEFAULT_BASICS: dict[str, Any] = {"headline": "Engineer", "summary": "A summary."}
_DEFAULT_CONTACT: dict[str, Any] = {"name": "Test", "email": "t@t.com"}
_DEFAULT_SHOW: dict[str, bool] = {"work": True, "education": True, "skills": True, "projects": True}
_DEFAULT_ORDER = ["skills", "work", "education", "projects"]


def make_resolved(
    *,
    profile: dict[str, Any] | None = None,
    basics: dict[str, Any] | None = None,
    contact: dict[str, Any] | None = None,
    work: list[Any] | None = None,
    education: list[Any] | None = None,
    skills: list[Any] | None = None,
    projects: list[Any] | None = None,
    show: dict[str, bool] | None = None,
    section_order: list[str] | None = None,
    template_name: str = "cv/ats-single",
    output_filename: str = "cv",
    warnings: list[str] | None = None,
) -> ResolvedProfile:
    """Build a ResolvedProfile with sensible defaults; override any part."""
    return ResolvedProfile(
        profile=profile if profile is not None else {},
        data={
            "basics": basics if basics is not None else dict(_DEFAULT_BASICS),
            "contact": contact if contact is not None else dict(_DEFAULT_CONTACT),
            "work": work or [],
            "education": education or [],
            "skills": skills or [],
            "projects": projects or [],
        },
        show_sections=show if show is not None else dict(_DEFAULT_SHOW),
        section_order=section_order if section_order is not None else list(_DEFAULT_ORDER),
        template_name=template_name,
        output_filename=output_filename,
        warnings=warnings or [],
    )


# Default file contents for a scaffolded project. Overridable per file via
# make_project(..., files={"data/work.yaml": "...", ...}).
_PROJECT_FILES: dict[str, str] = {
    "data/basics.yaml": 'headline: "Test Engineer"\nsummary: "A test summary."\n',
    "data/work.yaml": (
        "- company: Acme\n  title: Engineer\n  location: Remote\n"
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n    - Designed and built a distributed system handling 10k requests.\n"
        "  tags: [python]\n"
    ),
    "data/education.yaml": (
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours in computer science program.\n"
    ),
    "data/skills.yaml": "- category: Languages\n  items: [Python]\n",
    "data/projects/alpha.yaml": (
        'name: alpha\ndescription: "A project."\ntags: [python]\n'
        'url: "https://example.com/alpha"\nstart_date: "2023-01"\n'
        "highlights:\n  - Built a CLI tool used by 500 developers daily.\n"
    ),
    "private/contact.yaml": (
        'name: Test\nemail: "test@example.com"\nphone: "+1 (555) 000-0000"\n'
        'location: "Test City"\nlinkedin: testuser\ngithub: testuser\n'
        'website: "https://example.com"\n'
    ),
    "profiles/general.yaml": "template: cv/ats-single\noutput_filename: cv\n",
}

# A project where every entry carries *only* its schema-required fields — the
# shape a user gets by following the docs and omitting what they don't need.
# Templates run under StrictUndefined, so this is the case that regresses.
SPARSE_PROJECT_FILES: dict[str, str] = {
    "data/basics.yaml": 'headline: "Test Engineer"\nsummary: "A test summary."\n',
    "data/work.yaml": '- company: Acme\n  title: Engineer\n  start_date: "2020-01"\n',
    "data/education.yaml": '- institution: Uni\n  degree: BSc\n  start_date: "2016"\n',
    "data/skills.yaml": "- category: Languages\n  items: [Python]\n",
    "data/projects/alpha.yaml": 'name: alpha\ndescription: "A project."\ntags: [python]\n',
    "private/contact.yaml": "name: Test\n",
    "profiles/general.yaml": "template: cv/ats-single\noutput_filename: cv\n",
}


def make_project(
    tmp_path: Path,
    *,
    files: dict[str, str] | None = None,
    extra: dict[str, str] | None = None,
) -> Path:
    """Write a project tree under *tmp_path* and return it.

    *files* replaces the default file set entirely; *extra* adds/overrides
    individual files on top of the defaults (e.g. an extra profile).
    """
    contents = dict(files if files is not None else _PROJECT_FILES)
    if extra:
        contents.update(extra)
    for rel, text in contents.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path
