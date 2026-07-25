"""Import CV data from external formats (JSON Resume) into cvloom's layout.

The inverse of :mod:`cvloom.export`. A JSON Resume document is split into
cvloom's data layout, keeping PII (name, email, phone, location, social
handles) in ``private/contact.yaml`` and everything else under ``data/``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cvloom import schema, sections
from cvloom.export import TAGS_EXTENSION_KEY

# JSON Resume profile networks that map to dedicated contact fields.
_CONTACT_PROFILE_NETWORKS = {"linkedin": "linkedin", "github": "github"}


class ImportProblem(Exception):
    """Raised when a source document cannot be imported."""


@dataclass
class ImportedData:
    """Result of parsing a source document into cvloom's sections."""

    contact: dict[str, Any] = field(default_factory=dict)
    basics: dict[str, Any] | None = None
    work: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    publications: list[dict[str, Any]] = field(default_factory=list)
    certifications: list[dict[str, Any]] = field(default_factory=list)
    awards: list[dict[str, Any]] = field(default_factory=list)
    languages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WritePlan:
    """A single file the importer intends to write."""

    path: Path
    is_private: bool
    exists: bool


def _require(value: Any, kind: str, what: str) -> None:
    """Raise ImportProblem unless *value* is of the expected JSON *kind*."""
    ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }[kind]
    if not ok:
        raise ImportProblem(f"Expected {what} to be a JSON {kind}, got {type(value).__name__}.")


def _highlights(entry: dict[str, Any]) -> list[str]:
    """Extract JSON Resume highlights as a list of plain strings."""
    raw = entry.get("highlights") or []
    _require(raw, "array", "highlights")
    return [str(h) for h in raw]


def _location_string(loc: dict[str, Any]) -> str:
    """Collapse a JSON Resume location object to a single string."""
    if loc.get("address"):
        return str(loc["address"])
    parts = [str(loc[k]) for k in ("city", "region", "countryCode") if loc.get(k)]
    return ", ".join(parts)


def _map_contact(basics: dict[str, Any]) -> dict[str, Any]:
    """Map JSON Resume ``basics`` PII fields to a cvloom contact dict."""
    contact: dict[str, Any] = {"name": str(basics.get("name", "")).strip()}
    if basics.get("email"):
        contact["email"] = str(basics["email"])
    if basics.get("phone"):
        contact["phone"] = str(basics["phone"])
    if basics.get("url"):
        contact["website"] = str(basics["url"])

    loc = basics.get("location") or {}
    _require(loc, "object", "basics.location")
    location = _location_string(loc)
    if location:
        contact["location"] = location

    profiles = basics.get("profiles") or []
    _require(profiles, "array", "basics.profiles")
    for profile in profiles:
        network = str(profile.get("network", "")).lower()
        target = _CONTACT_PROFILE_NETWORKS.get(network)
        if target and profile.get("username"):
            contact[target] = str(profile["username"])
    return contact


def _map_basics(basics: dict[str, Any]) -> dict[str, Any]:
    """Map JSON Resume ``basics`` non-PII fields to a cvloom basics dict."""
    result: dict[str, Any] = {
        "headline": str(basics.get("label", "")),
        "summary": str(basics.get("summary", "")),
    }
    public_links: list[dict[str, str]] = []
    for profile in basics.get("profiles") or []:
        network = str(profile.get("network", "")).lower()
        if network not in _CONTACT_PROFILE_NETWORKS and profile.get("url"):
            public_links.append(
                {"label": str(profile.get("network", "Link")), "url": str(profile["url"])}
            )
    if public_links:
        result["public_links"] = public_links
    return result


def _restore_extensions(item: dict[str, Any], entry: dict[str, Any], *keys: str) -> None:
    """Read back cvloom's namespaced extensions (see ``export.TAGS_EXTENSION_KEY``).

    Fields cvloom carries that JSON Resume has no home for are exported under
    ``x-cvloom-*``. Reading them back is what makes an export → import
    round-trip lossless — without this, a round-trip silently strips the tag
    taxonomy that profile filtering depends on.
    """
    if entry.get(TAGS_EXTENSION_KEY):
        item["tags"] = [str(t) for t in entry[TAGS_EXTENSION_KEY]]
    for key in keys:
        value = entry.get(f"x-cvloom-{key}")
        if value:
            item[key] = str(value)


def _map_work(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", "work entry")
        item: dict[str, Any] = {
            "company": str(entry.get("name") or entry.get("company") or ""),
            "title": str(entry.get("position", "")),
            "start_date": str(entry.get("startDate", "")),
        }
        if entry.get("endDate"):
            item["end_date"] = str(entry["endDate"])
        if entry.get("location"):
            item["location"] = str(entry["location"])
        highlights = _highlights(entry)
        if highlights:
            item["highlights"] = highlights
        _restore_extensions(item, entry)
        result.append(item)
    return result


def _map_education(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", "education entry")
        item: dict[str, Any] = {
            "institution": str(entry.get("institution", "")),
            "degree": str(entry.get("studyType", "")),
            "start_date": str(entry.get("startDate", "")),
        }
        if entry.get("area"):
            item["field"] = str(entry["area"])
        if entry.get("endDate"):
            item["end_date"] = str(entry["endDate"])
        if entry.get("score"):
            item["grade"] = str(entry["score"])
        # Export writes education bullets to `courses` (the spec has no
        # `highlights` here); accept either so third-party documents import too.
        highlights = _highlights(entry) or [str(c) for c in entry.get("courses") or []]
        if highlights:
            item["highlights"] = highlights
        _restore_extensions(item, entry)
        result.append(item)
    return result


def _map_skills(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for group in groups:
        _require(group, "object", "skill group")
        keywords = group.get("keywords") or []
        _require(keywords, "array", "skill keywords")
        result.append(
            {
                "category": str(group.get("name", "")),
                "items": [str(k) for k in keywords],
            }
        )
    return result


def _map_projects(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", "project entry")
        keywords = entry.get("keywords") or []
        _require(keywords, "array", "project keywords")
        item: dict[str, Any] = {
            "name": str(entry.get("name", "")),
            "description": str(entry.get("description", "")),
            "tags": [str(k) for k in keywords],
        }
        if entry.get("url"):
            item["url"] = str(entry["url"])
        if entry.get("startDate"):
            item["start_date"] = str(entry["startDate"])
        if entry.get("endDate"):
            item["end_date"] = str(entry["endDate"])
        highlights = _highlights(entry)
        if highlights:
            item["highlights"] = highlights
        result.append(item)
    return result


def _map_publications(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a JSON Resume publications array to cvloom publication entries.

    JSON Resume has no ISBN/DOI field, so ``identifier`` is never populated on
    import — export folds it into ``summary`` and there is no reliable way to
    split it back out.
    """
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", "publication entry")
        item: dict[str, Any] = {"name": str(entry.get("name", ""))}
        if entry.get("publisher"):
            item["publisher"] = str(entry["publisher"])
        if entry.get("releaseDate"):
            item["release_date"] = str(entry["releaseDate"])
        if entry.get("url"):
            item["url"] = str(entry["url"])
        if entry.get("summary"):
            item["summary"] = str(entry["summary"])
        _restore_extensions(item, entry)
        result.append(item)
    return result


def _map_certifications(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a JSON Resume certificates array to cvloom certification entries.

    JSON Resume has no expiry or credential-ID field, so ``expiry_date`` and
    ``identifier`` are never populated on import.
    """
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", "certificate entry")
        item: dict[str, Any] = {"name": str(entry.get("name", ""))}
        if entry.get("issuer"):
            item["issuer"] = str(entry["issuer"])
        if entry.get("date"):
            item["date"] = str(entry["date"])
        if entry.get("url"):
            item["url"] = str(entry["url"])
        _restore_extensions(item, entry, "expiry_date", "identifier")
        result.append(item)
    return result


def _map_simple(
    entries: list[dict[str, Any]], keys: tuple[tuple[str, str], ...], what: str
) -> list[dict[str, Any]]:
    """Map entries by (JSON Resume key → cvloom key), dropping empty values.

    Enough for sections whose two schemas line up field-for-field; anything
    needing a fold or a rename with logic keeps its own mapper.
    """
    result: list[dict[str, Any]] = []
    for entry in entries:
        _require(entry, "object", what)
        item: dict[str, Any] = {}
        for src, dest in keys:
            if entry.get(src):
                item[dest] = str(entry[src])
        _restore_extensions(item, entry)
        result.append(item)
    return result


_AWARD_KEYS = (
    ("title", "title"),
    ("awarder", "awarder"),
    ("date", "date"),
    ("summary", "summary"),
)
_LANGUAGE_KEYS = (("language", "language"), ("fluency", "fluency"))


def from_json_resume(doc: Any) -> ImportedData:
    """Parse a JSON Resume document into cvloom sections.

    Raises :class:`ImportProblem` if the document is not a JSON Resume object
    or a section has the wrong shape.
    """
    _require(doc, "object", "the JSON Resume document")
    basics = doc.get("basics") or {}
    _require(basics, "object", "basics")

    work = doc.get("work") or []
    education = doc.get("education") or []
    skills = doc.get("skills") or []
    projects = doc.get("projects") or []
    publications = doc.get("publications") or []
    certificates = doc.get("certificates") or []
    awards = doc.get("awards") or []
    languages = doc.get("languages") or []
    _require(work, "array", "work")
    _require(education, "array", "education")
    _require(skills, "array", "skills")
    _require(projects, "array", "projects")
    _require(publications, "array", "publications")
    _require(certificates, "array", "certificates")
    _require(awards, "array", "awards")
    _require(languages, "array", "languages")

    return ImportedData(
        contact=_map_contact(basics),
        basics=_map_basics(basics) if doc.get("basics") is not None else None,
        work=_map_work(work),
        education=_map_education(education),
        skills=_map_skills(skills),
        projects=_map_projects(projects),
        publications=_map_publications(publications),
        certifications=_map_certifications(certificates),
        awards=_map_simple(awards, _AWARD_KEYS, "award entry"),
        languages=_map_simple(languages, _LANGUAGE_KEYS, "language entry"),
    )


def validate_imported(imported: ImportedData) -> list[str]:
    """Validate the imported sections against cvloom's schemas."""
    payload: dict[str, Any] = {"contact": imported.contact}
    if imported.basics is not None:
        payload["basics"] = imported.basics
    if imported.work:
        payload["work"] = imported.work
    if imported.education:
        payload["education"] = imported.education
    if imported.skills:
        payload["skills"] = imported.skills
    if imported.projects:
        payload["projects"] = imported.projects
    if imported.publications:
        payload["publications"] = imported.publications
    if imported.certifications:
        payload["certifications"] = imported.certifications
    if imported.awards:
        payload["awards"] = imported.awards
    if imported.languages:
        payload["languages"] = imported.languages
    return schema.validate_all(payload)


def _project_stems(projects: list[dict[str, Any]]) -> list[str]:
    """Unique, order-stable file stems for project entries."""
    seen: set[str] = set()
    stems: list[str] = []
    for project in projects:
        stem = sections.slugify(str(project.get("name", "")), fallback="project")
        while stem in seen:
            stem += "-1"
        seen.add(stem)
        stems.append(stem)
    return stems


def plan_writes(imported: ImportedData, data_dir: Path, private_dir: Path) -> list[WritePlan]:
    """Compute the files that would be written, in a stable order."""
    plans: list[WritePlan] = []

    def add(path: Path, is_private: bool) -> None:
        plans.append(WritePlan(path=path, is_private=is_private, exists=path.exists()))

    if imported.contact:
        add(private_dir / "contact.yaml", True)
    if imported.basics is not None:
        add(data_dir / "basics.yaml", False)
    if imported.work:
        add(data_dir / "work.yaml", False)
    if imported.education:
        add(data_dir / "education.yaml", False)
    if imported.skills:
        add(data_dir / "skills.yaml", False)
    if imported.publications:
        add(data_dir / "publications.yaml", False)
    if imported.certifications:
        add(data_dir / "certifications.yaml", False)
    if imported.awards:
        add(data_dir / "awards.yaml", False)
    if imported.languages:
        add(data_dir / "languages.yaml", False)
    for stem in _project_stems(imported.projects):
        add(data_dir / "projects" / f"{stem}.yaml", False)
    return plans


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def write_imported(imported: ImportedData, data_dir: Path, private_dir: Path) -> list[Path]:
    """Serialize imported sections to disk. Returns the paths written.

    Callers are responsible for conflict checking (see :func:`plan_writes`).
    PII lands only under *private_dir*; everything else under *data_dir*.
    """
    written: list[Path] = []
    if imported.contact:
        path = private_dir / "contact.yaml"
        _dump(path, imported.contact)
        written.append(path)
    if imported.basics is not None:
        path = data_dir / "basics.yaml"
        _dump(path, imported.basics)
        written.append(path)
    for section, entries in (
        ("work", imported.work),
        ("education", imported.education),
        ("skills", imported.skills),
        ("publications", imported.publications),
        ("certifications", imported.certifications),
        ("awards", imported.awards),
        ("languages", imported.languages),
    ):
        if entries:
            path = data_dir / f"{section}.yaml"
            _dump(path, entries)
            written.append(path)
    for project, stem in zip(imported.projects, _project_stems(imported.projects), strict=True):
        path = data_dir / "projects" / f"{stem}.yaml"
        _dump(path, project)
        written.append(path)
    return written


def load_json_resume(source: Path) -> Any:
    """Read and JSON-parse a source file, raising ImportProblem on bad JSON."""
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ImportProblem(f"{source} is not valid JSON: {exc}") from exc
