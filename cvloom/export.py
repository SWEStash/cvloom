"""Export CV data to external formats (JSON Resume)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cvloom.models import ResolvedProfile


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
