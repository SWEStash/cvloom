"""Tests for JSON Resume export."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from cvloom.export import (
    export_docx,
    export_linkedin,
    export_markdown,
    to_json_resume,
    to_linkedin,
    to_markdown,
)
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
    result = to_json_resume(
        _make_resolved(
            contact={
                "name": "Min",
                "email": "min@example.com",
            }
        )
    )
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


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------


def test_markdown_contains_name() -> None:
    md = to_markdown(_make_resolved())
    assert "# Jane Doe" in md


def test_markdown_section_headings() -> None:
    md = to_markdown(_make_resolved())
    assert "## Work Experience" in md
    assert "## Education" in md
    assert "## Skills" in md


def test_markdown_entry_content() -> None:
    md = to_markdown(_make_resolved())
    assert "Senior Engineer at Acme Corp" in md
    assert "- Built scalable systems." in md
    assert "**Languages:**" in md
    assert "Python" in md
    assert "Go" in md


def test_markdown_hidden_section_omitted() -> None:
    r = dataclasses.replace(
        _make_resolved(),
        show_sections={"work": False, "education": True, "skills": True, "projects": True},
    )
    md = to_markdown(r)
    assert "## Work Experience" not in md
    assert "## Education" in md


def test_markdown_section_order() -> None:
    r = dataclasses.replace(
        _make_resolved(),
        section_order=["education", "skills", "work", "projects"],
    )
    md = to_markdown(r)
    assert md.index("## Education") < md.index("## Skills") < md.index("## Work Experience")


def test_export_markdown_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "cv.md"
    export_markdown(_make_resolved(), out)
    assert out.exists()
    assert "# Jane Doe" in out.read_text()


# ---------------------------------------------------------------------------
# LinkedIn export
# ---------------------------------------------------------------------------


def test_linkedin_contains_sections() -> None:
    txt = to_linkedin(_make_resolved())
    assert "ABOUT" in txt
    assert "EXPERIENCE" in txt
    assert "SKILLS" in txt


def test_linkedin_entry_content() -> None:
    txt = to_linkedin(_make_resolved())
    assert "Senior Engineer at Acme Corp" in txt
    assert "· Built scalable systems." in txt
    assert "Python" in txt


def test_linkedin_no_warning_under_limit(tmp_path: Path) -> None:
    warnings = export_linkedin(_make_resolved(), tmp_path / "li.txt")
    assert warnings == []


def test_linkedin_warning_over_limit(tmp_path: Path) -> None:
    long_summary = "x" * 2601
    r = _make_resolved(basics={"headline": "Engineer", "summary": long_summary, "public_links": []})
    warnings = export_linkedin(r, tmp_path / "li.txt")
    assert len(warnings) == 1
    assert "2601" in warnings[0]
    assert "2600" in warnings[0]


def test_export_linkedin_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "li.txt"
    export_linkedin(_make_resolved(), out)
    assert out.exists()
    assert "ABOUT" in out.read_text()


# ---------------------------------------------------------------------------
# DOCX export
# ---------------------------------------------------------------------------


def test_export_docx_writes_file(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    out = tmp_path / "cv.docx"
    export_docx(_make_resolved(), out)
    assert out.exists()
    doc = docx.Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert any("Jane Doe" in t for t in texts)


def test_export_docx_has_section_headings(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    out = tmp_path / "cv.docx"
    export_docx(_make_resolved(), out)
    doc = docx.Document(str(out))
    styles = {p.style.name for p in doc.paragraphs}
    assert "Heading 1" in styles
    assert "List Bullet" in styles


# ── publications ─────────────────────────────────────────────────────

_PUBLICATION = {
    "name": "A model of distributed consensus under churn",
    "publisher": "Journal of Systems Research",
    "release_date": "2018",
    "identifier": "ISBN 978-0-0000-0000-1",
    "url": "https://example.com/paper",
    "summary": "A short summary of the paper.",
}


def _resolved_with_publications():
    resolved = _make_resolved(publications=[dict(_PUBLICATION)])
    resolved.show_sections["publications"] = True
    resolved.section_order.append("publications")
    return resolved


def test_publications_mapping():
    result = to_json_resume(_resolved_with_publications())
    pub = result["publications"][0]
    assert pub["name"] == _PUBLICATION["name"]
    assert pub["publisher"] == "Journal of Systems Research"
    assert pub["releaseDate"] == "2018"
    assert pub["url"] == "https://example.com/paper"


def test_publications_identifier_folded_into_summary():
    """JSON Resume has no ISBN/DOI field — export must not silently drop it."""
    result = to_json_resume(_resolved_with_publications())
    assert result["publications"][0]["summary"] == (
        "A short summary of the paper. ISBN 978-0-0000-0000-1"
    )


def test_publications_omitted_when_empty():
    assert "publications" not in to_json_resume(_make_resolved())


def test_markdown_includes_publications():
    md = to_markdown(_resolved_with_publications())
    assert "## Publications" in md
    assert _PUBLICATION["name"] in md
    assert "Journal of Systems Research · 2018 · ISBN 978-0-0000-0000-1" in md


# ── certifications ───────────────────────────────────────────────────

_CERTIFICATION = {
    "name": "AWS Certified Solutions Architect",
    "issuer": "Amazon Web Services",
    "date": "2023-04",
    "expiry_date": "2026-04",
    "identifier": "AWS-PSA-12345",
    "url": "https://example.com/verify",
}


def _resolved_with_certifications():
    resolved = _make_resolved(certifications=[dict(_CERTIFICATION)])
    resolved.show_sections["certifications"] = True
    resolved.section_order.append("certifications")
    return resolved


def test_certifications_map_to_json_resume_certificates():
    result = to_json_resume(_resolved_with_certifications())
    assert result["certificates"] == [
        {
            "name": "AWS Certified Solutions Architect",
            "issuer": "Amazon Web Services",
            "date": "2023-04",
            "url": "https://example.com/verify",
        }
    ]


def test_certifications_extensions_dropped_on_export():
    """expiry_date and identifier have no JSON Resume home — documented loss."""
    cert = to_json_resume(_resolved_with_certifications())["certificates"][0]
    assert "expiry_date" not in cert
    assert "identifier" not in cert


def test_certificates_omitted_when_empty():
    assert "certificates" not in to_json_resume(_make_resolved())


def test_markdown_keeps_certification_extensions():
    """Markdown is lossless where JSON Resume is not."""
    md = to_markdown(_resolved_with_certifications())
    assert "## Certifications" in md
    assert "2023-04 – 2026-04" in md
    assert "AWS-PSA-12345" in md
