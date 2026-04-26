"""Export CV data to external formats (JSON Resume, Markdown, LinkedIn, DOCX)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cvloom.models import ResolvedProfile

_LINKEDIN_ABOUT_LIMIT = 2600

_SECTION_HEADINGS: dict[str, str] = {
    "work": "Work Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
}


def _hl(h: Any) -> str:
    """Extract plain text from a highlight (str or dict with 'text' key)."""
    return h if isinstance(h, str) else h.get("text", "")


def _skill_name(item: Any) -> str:
    return item if isinstance(item, str) else item.get("name", "")


def _map_profiles(contact: dict[str, Any]) -> list[dict[str, str]]:
    """Map contact social links to JSON Resume profiles."""
    profiles: list[dict[str, str]] = []
    if contact.get("linkedin"):
        profiles.append({
            "network": "LinkedIn",
            "username": contact["linkedin"],
            "url": f"https://linkedin.com/in/{contact['linkedin']}",
        })
    if contact.get("github"):
        profiles.append({
            "network": "GitHub",
            "username": contact["github"],
            "url": f"https://github.com/{contact['github']}",
        })
    return profiles


def _map_location(contact: dict[str, Any]) -> dict[str, str]:
    """Map location string to JSON Resume location object."""
    loc = contact.get("location", "")
    return {"address": loc} if loc else {}


def _map_work(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map work entries to JSON Resume work array."""
    result: list[dict[str, Any]] = []
    for entry in entries:
        item: dict[str, Any] = {
            "name": entry.get("company", ""),
            "position": entry.get("title", ""),
            "startDate": entry.get("start_date", ""),
        }
        if entry.get("end_date"):
            item["endDate"] = entry["end_date"]
        if entry.get("location"):
            item["location"] = entry["location"]
        if entry.get("highlights"):
            item["highlights"] = [
                h if isinstance(h, str) else h.get("text", "")
                for h in entry["highlights"]
            ]
        result.append(item)
    return result


def _map_education(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map education entries to JSON Resume education array."""
    result: list[dict[str, Any]] = []
    for entry in entries:
        item: dict[str, Any] = {
            "institution": entry.get("institution", ""),
            "studyType": entry.get("degree", ""),
            "startDate": entry.get("start_date", ""),
        }
        if entry.get("field"):
            item["area"] = entry["field"]
        if entry.get("end_date"):
            item["endDate"] = entry["end_date"]
        if entry.get("grade"):
            item["score"] = entry["grade"]
        if entry.get("highlights"):
            item["highlights"] = [
                h if isinstance(h, str) else h.get("text", "")
                for h in entry["highlights"]
            ]
        result.append(item)
    return result


def _map_skills(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map skill groups to JSON Resume skills array."""
    result: list[dict[str, Any]] = []
    for group in groups:
        keywords: list[str] = []
        for item in group.get("items", []):
            if isinstance(item, str):
                keywords.append(item)
            else:
                keywords.append(item.get("name", ""))
        result.append({
            "name": group.get("category", ""),
            "keywords": keywords,
        })
    return result


def _map_projects(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map project entries to JSON Resume projects array."""
    result: list[dict[str, Any]] = []
    for entry in entries:
        item: dict[str, Any] = {
            "name": entry.get("name", ""),
            "description": entry.get("description", ""),
        }
        if entry.get("url"):
            item["url"] = entry["url"]
        if entry.get("start_date"):
            item["startDate"] = entry["start_date"]
        if entry.get("end_date"):
            item["endDate"] = entry["end_date"]
        if entry.get("tags"):
            item["keywords"] = entry["tags"]
        if entry.get("highlights"):
            item["highlights"] = [
                h if isinstance(h, str) else h.get("text", "")
                for h in entry["highlights"]
            ]
        result.append(item)
    return result


def to_json_resume(resolved: ResolvedProfile) -> dict[str, Any]:
    """Convert resolved cvloom data to JSON Resume schema."""
    data = resolved.data
    contact = data.get("contact", {})
    basics_data = data.get("basics", {})

    result: dict[str, Any] = {
        "basics": {
            "name": contact.get("name", ""),
            "label": basics_data.get("headline", ""),
            "email": contact.get("email", ""),
            "summary": basics_data.get("summary", ""),
        },
    }

    if contact.get("phone"):
        result["basics"]["phone"] = contact["phone"]
    if contact.get("website"):
        result["basics"]["url"] = contact["website"]

    location = _map_location(contact)
    if location:
        result["basics"]["location"] = location

    profiles = _map_profiles(contact)
    if profiles:
        result["basics"]["profiles"] = profiles

    work = data.get("work", [])
    if work:
        result["work"] = _map_work(work)

    education = data.get("education", [])
    if education:
        result["education"] = _map_education(education)

    skills = data.get("skills", [])
    if skills:
        result["skills"] = _map_skills(skills)

    projects = data.get("projects", [])
    if projects:
        result["projects"] = _map_projects(projects)

    return result


def export_json_resume(resolved: ResolvedProfile, output_path: Path) -> None:
    """Write JSON Resume file."""
    resume = to_json_resume(resolved)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(resume, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def to_markdown(resolved: ResolvedProfile) -> str:
    """Return the CV formatted as a Markdown string."""
    data = resolved.data
    contact = data.get("contact", {})
    basics = data.get("basics", {})

    lines: list[str] = [f"# {contact.get('name', '')}", ""]

    parts: list[str] = []
    if basics.get("headline"):
        parts.append(f"**{basics['headline']}**")
    for field in ["email", "phone", "location", "website"]:
        if contact.get(field):
            parts.append(str(contact[field]))
    if contact.get("linkedin"):
        parts.append(f"https://linkedin.com/in/{contact['linkedin']}")
    if contact.get("github"):
        parts.append(f"https://github.com/{contact['github']}")
    if parts:
        lines += [" | ".join(parts), ""]

    if basics.get("summary"):
        lines += ["---", "", "## Summary", "", str(basics["summary"]), ""]

    for section in resolved.section_order:
        if not resolved.show_sections.get(section, False):
            continue
        heading = _SECTION_HEADINGS.get(section)
        if heading is None:
            continue

        lines += ["---", "", f"## {heading}", ""]

        if section == "skills":
            for group in data.get("skills", []):
                cat = group.get("category", "")
                items = [_skill_name(i) for i in group.get("items", [])]
                lines.append(f"**{cat}:** {', '.join(items)}")
            lines.append("")

        elif section == "work":
            for entry in data.get("work", []):
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                location = entry.get("location", "")
                date_str = f"{start} – {end}" if end else start
                meta = f"{date_str} | {location}" if location else date_str
                lines.append(f"### {entry.get('title', '')} at {entry.get('company', '')}")
                lines += [f"*{meta}*", ""]
                for h in entry.get("highlights", []):
                    lines.append(f"- {_hl(h)}")
                lines.append("")

        elif section == "education":
            for entry in data.get("education", []):
                degree = entry.get("degree", "")
                field = entry.get("field", "")
                institution = entry.get("institution", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                location = entry.get("location", "")
                degree_str = f"{degree} in {field}" if field else degree
                date_str = f"{start} – {end}" if end else start
                meta = f"{date_str} | {location}" if location else date_str
                lines.append(f"### {degree_str} — {institution}")
                lines += [f"*{meta}*", ""]
                for h in entry.get("highlights", []):
                    lines.append(f"- {_hl(h)}")
                lines.append("")

        elif section == "projects":
            for entry in data.get("projects", []):
                name = entry.get("name", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                description = entry.get("description", "")
                lines.append(f"### {name}")
                if start:
                    date_str = f"{start} – {end}" if end else start
                    lines += [f"*{date_str}*", ""]
                else:
                    lines.append("")
                if description:
                    lines += [description, ""]
                for h in entry.get("highlights", []):
                    lines.append(f"- {_hl(h)}")
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_markdown(resolved: ResolvedProfile, output_path: Path) -> None:
    """Write Markdown CV to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(to_markdown(resolved), encoding="utf-8")


# ---------------------------------------------------------------------------
# LinkedIn plain text
# ---------------------------------------------------------------------------


def to_linkedin(resolved: ResolvedProfile) -> str:
    """Return the CV as LinkedIn-pasteable plain text."""
    data = resolved.data
    basics = data.get("basics", {})

    sections: list[str] = []

    summary = basics.get("summary", "")
    if summary:
        sections.append(f"ABOUT\n-----\n{summary}")

    for section in resolved.section_order:
        if not resolved.show_sections.get(section, False):
            continue

        if section == "work":
            entries = data.get("work", [])
            if not entries:
                continue
            block: list[str] = ["EXPERIENCE", "----------"]
            for entry in entries:
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                location = entry.get("location", "")
                date_str = f"{start} – {end}" if end else start
                block.append(f"{entry.get('title', '')} at {entry.get('company', '')}")
                block.append(f"{date_str} | {location}" if location else date_str)
                block.append("")
                for h in entry.get("highlights", []):
                    block.append(f"· {_hl(h)}")
                block.append("")
            sections.append("\n".join(block).rstrip())

        elif section == "education":
            entries = data.get("education", [])
            if not entries:
                continue
            block = ["EDUCATION", "---------"]
            for entry in entries:
                degree = entry.get("degree", "")
                field = entry.get("field", "")
                institution = entry.get("institution", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                degree_str = f"{degree} in {field}" if field else degree
                block.append(f"{degree_str}, {institution}")
                if start:
                    block.append(f"{start} – {end}" if end else start)
                block.append("")
            sections.append("\n".join(block).rstrip())

        elif section == "skills":
            groups = data.get("skills", [])
            if not groups:
                continue
            all_skills = [_skill_name(i) for g in groups for i in g.get("items", [])]
            if all_skills:
                sections.append(f"SKILLS\n------\n{' · '.join(all_skills)}")

    return "\n\n\n".join(sections) + "\n"


def export_linkedin(resolved: ResolvedProfile, output_path: Path) -> list[str]:
    """Write LinkedIn plain text to file. Returns list of warning strings."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(to_linkedin(resolved), encoding="utf-8")

    warnings: list[str] = []
    summary = resolved.data.get("basics", {}).get("summary", "")
    if len(summary) > _LINKEDIN_ABOUT_LIMIT:
        warnings.append(
            f"About section is {len(summary)} chars "
            f"(LinkedIn limit: {_LINKEDIN_ABOUT_LIMIT})"
        )
    return warnings


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------


def export_docx(resolved: ResolvedProfile, output_path: Path) -> None:
    """Write a .docx file using python-docx (optional dependency)."""
    try:
        import docx
    except ImportError:
        raise SystemExit(
            "python-docx is not installed. Install it with: uv pip install python-docx"
        )

    data = resolved.data
    contact = data.get("contact", {})
    basics = data.get("basics", {})

    doc = docx.Document()
    doc.add_paragraph(contact.get("name", ""), style="Title")

    parts: list[str] = []
    if basics.get("headline"):
        parts.append(str(basics["headline"]))
    for field in ["email", "phone", "location", "website"]:
        if contact.get(field):
            parts.append(str(contact[field]))
    if contact.get("linkedin"):
        parts.append(f"linkedin.com/in/{contact['linkedin']}")
    if contact.get("github"):
        parts.append(f"github.com/{contact['github']}")
    if parts:
        doc.add_paragraph(" | ".join(parts), style="Subtitle")

    if basics.get("summary"):
        doc.add_heading("Summary", level=1)
        doc.add_paragraph(str(basics["summary"]), style="Body Text")

    for section in resolved.section_order:
        if not resolved.show_sections.get(section, False):
            continue
        heading = _SECTION_HEADINGS.get(section)
        if heading is None:
            continue

        doc.add_heading(heading, level=1)

        if section == "work":
            for entry in data.get("work", []):
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                location = entry.get("location", "")
                date_str = f"{start} – {end}" if end else start
                meta = f"{date_str} | {location}" if location else date_str
                doc.add_heading(f"{entry.get('title', '')} at {entry.get('company', '')}", level=2)
                if meta:
                    p = doc.add_paragraph(meta, style="Body Text")
                    p.runs[0].italic = True
                for h in entry.get("highlights", []):
                    doc.add_paragraph(_hl(h), style="List Bullet")

        elif section == "education":
            for entry in data.get("education", []):
                degree = entry.get("degree", "")
                field = entry.get("field", "")
                institution = entry.get("institution", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                degree_str = f"{degree} in {field}" if field else degree
                doc.add_heading(f"{degree_str} — {institution}", level=2)
                if start:
                    p = doc.add_paragraph(f"{start} – {end}" if end else start, style="Body Text")
                    p.runs[0].italic = True
                for h in entry.get("highlights", []):
                    doc.add_paragraph(_hl(h), style="List Bullet")

        elif section == "skills":
            for group in data.get("skills", []):
                cat = group.get("category", "")
                items = [_skill_name(i) for i in group.get("items", [])]
                doc.add_paragraph(f"{cat}: {', '.join(items)}", style="Body Text")

        elif section == "projects":
            for entry in data.get("projects", []):
                name = entry.get("name", "")
                start = entry.get("start_date", "")
                end = entry.get("end_date", "")
                description = entry.get("description", "")
                doc.add_heading(name, level=2)
                if start:
                    p = doc.add_paragraph(f"{start} – {end}" if end else start, style="Body Text")
                    p.runs[0].italic = True
                if description:
                    doc.add_paragraph(description, style="Body Text")
                for h in entry.get("highlights", []):
                    doc.add_paragraph(_hl(h), style="List Bullet")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
