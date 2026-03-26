"""Tests for JSON Resume export."""

from __future__ import annotations

from cvloom.export import to_json_resume
from cvloom.models import ResolvedProfile


def _make_resolved(**overrides: object) -> ResolvedProfile:
    data = {
        "basics": {"headline": "Software Engineer", "summary": "A great engineer."},
        "contact": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+1 555-1234",
            "location": "San Francisco, CA",
            "website": "https://jane.dev",
            "linkedin": "janedoe",
            "github": "janedoe",
        },
        "work": [
            {
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "start_date": "2021-03",
                "end_date": "Present",
                "location": "Remote",
                "highlights": ["Built scalable systems."],
            },
        ],
        "education": [
            {
                "institution": "MIT",
                "degree": "BSc",
                "field": "Computer Science",
                "start_date": "2014",
                "end_date": "2018",
                "grade": "3.9",
                "highlights": ["Dean's list."],
            },
        ],
        "skills": [
            {"category": "Languages", "items": ["Python", {"name": "Go", "level": "advanced"}]},
        ],
        "projects": [
            {
                "name": "cvloom",
                "description": "CLI CV tool.",
                "tags": ["python", "cli"],
                "url": "https://github.com/j/cvloom",
                "start_date": "2026-01",
                "highlights": ["Built it."],
            },
        ],
    }
    data.update(overrides)  # type: ignore[arg-type]
    return ResolvedProfile(
        profile={},
        data=data,
        show_sections={"work": True, "education": True, "skills": True, "projects": True},
        section_order=["skills", "work", "education", "projects"],
        template_name="cv/ats-single",
        output_filename="cv",
    )


def test_basics_mapping():
    result = to_json_resume(_make_resolved())
    assert result["basics"]["name"] == "Jane Doe"
    assert result["basics"]["email"] == "jane@example.com"
    assert result["basics"]["label"] == "Software Engineer"
    assert result["basics"]["summary"] == "A great engineer."
    assert result["basics"]["phone"] == "+1 555-1234"
    assert result["basics"]["url"] == "https://jane.dev"


def test_location_mapping():
    result = to_json_resume(_make_resolved())
    assert result["basics"]["location"]["address"] == "San Francisco, CA"


def test_profiles_mapping():
    result = to_json_resume(_make_resolved())
    profiles = result["basics"]["profiles"]
    networks = {p["network"] for p in profiles}
    assert "LinkedIn" in networks
    assert "GitHub" in networks
    gh = next(p for p in profiles if p["network"] == "GitHub")
    assert gh["username"] == "janedoe"
    assert "github.com" in gh["url"]


def test_work_mapping():
    result = to_json_resume(_make_resolved())
    work = result["work"][0]
    assert work["name"] == "Acme Corp"
    assert work["position"] == "Senior Engineer"
    assert work["startDate"] == "2021-03"
    assert work["endDate"] == "Present"
    assert work["location"] == "Remote"
    assert "Built scalable systems." in work["highlights"]


def test_education_mapping():
    result = to_json_resume(_make_resolved())
    edu = result["education"][0]
    assert edu["institution"] == "MIT"
    assert edu["studyType"] == "BSc"
    assert edu["area"] == "Computer Science"
    assert edu["score"] == "3.9"
    assert "Dean's list." in edu["highlights"]


def test_skills_mapping():
    result = to_json_resume(_make_resolved())
    skill = result["skills"][0]
    assert skill["name"] == "Languages"
    assert "Python" in skill["keywords"]
    assert "Go" in skill["keywords"]


def test_projects_mapping():
    result = to_json_resume(_make_resolved())
    proj = result["projects"][0]
    assert proj["name"] == "cvloom"
    assert proj["description"] == "CLI CV tool."
    assert proj["url"] == "https://github.com/j/cvloom"
    assert proj["keywords"] == ["python", "cli"]
    assert "Built it." in proj["highlights"]


def test_minimal_contact():
    result = to_json_resume(_make_resolved(contact={
        "name": "Min",
        "email": "min@test.com",
    }))
    assert result["basics"]["name"] == "Min"
    assert "phone" not in result["basics"]
    assert "url" not in result["basics"]
    assert "profiles" not in result["basics"]


def test_empty_sections():
    result = to_json_resume(_make_resolved(work=[], education=[], skills=[], projects=[]))
    assert "work" not in result
    assert "education" not in result
    assert "skills" not in result
    assert "projects" not in result
