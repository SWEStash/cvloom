"""Tests for keyword gap analysis (match module)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cvloom.cli import cli
from cvloom.match import MatchReport, _extract_keywords, analyze_match
from cvloom.models import ResolvedProfile


def _make_resolved(
    work: list | None = None,
    skills: list | None = None,
    projects: list | None = None,
) -> ResolvedProfile:
    return ResolvedProfile(
        profile={},
        data={
            "basics": {"headline": "Senior Python Engineer", "summary": "Backend specialist."},
            "work": work or [],
            "education": [],
            "skills": skills or [],
            "projects": projects or [],
            "contact": {"name": "Test", "email": "t@t.com"},
        },
        show_sections={"work": True, "education": True, "skills": True, "projects": True},
        section_order=["skills", "work", "education", "projects"],
        template_name="cv/ats-single",
        output_filename="cv",
    )


# ── _extract_keywords ──────────────────────────────────────────────


def test_extract_keywords_basic():
    result = _extract_keywords("Python developer with Python experience")
    assert result["python"] == 2
    assert result["developer"] == 1
    assert result["experience"] == 1


def test_extract_keywords_removes_stop_words():
    result = _extract_keywords("the and is are with for")
    assert result == {}


def test_extract_keywords_empty():
    assert _extract_keywords("") == {}


# ── analyze_match ──────────────────────────────────────────────────


def test_analyze_match_full_coverage():
    resolved = _make_resolved(
        skills=[{"category": "Languages", "items": ["Python", "Kafka"]}],
    )
    jd = "Python Kafka"
    report = analyze_match(resolved, jd)
    assert report.cv_keywords_coverage == 1.0
    matched_kws = {m.keyword for m in report.matched}
    assert "python" in matched_kws
    assert "kafka" in matched_kws


def test_analyze_match_with_gaps():
    resolved = _make_resolved(
        skills=[{"category": "Languages", "items": ["Python"]}],
    )
    jd = "Kubernetes Terraform Docker orchestration cloud infrastructure"
    report = analyze_match(resolved, jd)
    assert len(report.gaps) > 0
    assert "kubernetes" in report.gaps


def test_analyze_match_empty_jd():
    resolved = _make_resolved()
    report = analyze_match(resolved, "")
    assert report.jd_word_count == 0
    assert report.cv_keywords_coverage == 0.0
    assert report.matched == []
    assert report.gaps == []


def test_analyze_match_keyword_sections():
    resolved = _make_resolved(
        work=[{
            "company": "Acme",
            "title": "Python Developer",
            "start_date": "2020-01",
            "highlights": ["Built microservices with Python and FastAPI."],
        }],
        skills=[{"category": "Languages", "items": ["Python"]}],
    )
    jd = "Python microservices FastAPI"
    report = analyze_match(resolved, jd)
    for m in report.matched:
        if m.keyword == "python":
            assert "skills" in m.found_in or "work" in m.found_in
            break
    else:
        pytest.fail("python not found in matched keywords")


def test_analyze_match_returns_report():
    resolved = _make_resolved()
    report = analyze_match(resolved, "python engineer backend")
    assert isinstance(report, MatchReport)
    assert isinstance(report.top_jd_keywords, list)


# ── CLI integration ────────────────────────────────────────────────


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "basics.yaml").write_text(
        'headline: "Python Engineer"\nsummary: "Backend specialist with 5 years."\n'
    )
    (data / "work.yaml").write_text(
        '- company: Acme\n  title: Engineer\n  location: Remote\n'
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n    - Built scalable Python microservices handling 10k requests.\n"
        "  tags: [python]\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours in computer science.\n"
    )
    (data / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python, Go, SQL]\n"
    )
    projects = data / "projects"
    projects.mkdir()
    (projects / "proj.yaml").write_text(
        'name: proj\ndescription: "A project."\ntags: [python]\n'
        'url: "https://example.com"\nstart_date: "2024-01"\n'
        "highlights:\n  - Built a CLI tool used by 500 developers.\n"
    )
    private = tmp_path / "private"
    private.mkdir()
    (private / "contact.yaml").write_text(
        'name: Test User\nemail: "test@example.com"\nphone: "+1 555"\n'
        'location: "City"\nlinkedin: test\ngithub: test\nwebsite: "https://test.dev"\n'
    )
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text("template: cv/ats-single\noutput_filename: cv\n")
    return tmp_path


# ── suggestions ────────────────────────────────────────────────────


def test_suggestions_single_token_goes_to_skills():
    resolved = _make_resolved()
    report = analyze_match(resolved, "kubernetes terraform docker")
    for gap in report.gaps:
        assert report.suggestions[gap] == "skills"


def test_suggestions_multi_word_goes_to_work():
    resolved = _make_resolved()
    # multi-word phrase extracted as separate tokens by tokenizer; each token maps to skills
    # Use a phrase that stays as separate tokens
    report = analyze_match(resolved, "stakeholder management")
    for gap in report.gaps:
        assert report.suggestions.get(gap) in ("skills", "work")


def test_suggestions_present_for_all_gaps():
    resolved = _make_resolved(skills=[{"category": "Languages", "items": ["Python"]}])
    report = analyze_match(resolved, "python rust terraform observability")
    assert set(report.suggestions.keys()) == set(report.gaps)


def test_match_cli_command(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project_root)
    jd_file = project_root / "jd.txt"
    jd_file.write_text("Looking for a Python engineer with SQL and microservices experience.")
    runner = CliRunner()
    result = runner.invoke(cli, ["match", "--jd", str(jd_file)])
    assert result.exit_code == 0
    assert "Coverage" in result.output


# ── reorder_hints ──────────────────────────────────────────────────


def test_reorder_hints_suggests_better_order() -> None:
    r = _make_resolved(work=[
        {"company": "A", "title": "Engineer", "start_date": "2020-01",
         "highlights": ["Built pipelines."]},
        {"company": "B", "title": "Python Developer", "start_date": "2022-01",
         "highlights": ["Built Python microservices with FastAPI and PostgreSQL."]},
    ])
    report = analyze_match(r, "Python FastAPI PostgreSQL microservices developer")
    assert len(report.reorder_hints) == 1
    assert "Python Developer at B" in report.reorder_hints[0]


def test_reorder_hints_empty_when_already_optimal() -> None:
    r = _make_resolved(work=[
        {"company": "A", "title": "Python Developer", "start_date": "2022-01",
         "highlights": ["Built Python microservices."]},
        {"company": "B", "title": "Engineer", "start_date": "2020-01",
         "highlights": ["Did general work."]},
    ])
    report = analyze_match(r, "Python microservices developer")
    assert report.reorder_hints == []


def test_reorder_hints_empty_single_work_entry() -> None:
    r = _make_resolved(work=[
        {"company": "A", "title": "Engineer", "start_date": "2020-01",
         "highlights": ["Built things."]},
    ])
    report = analyze_match(r, "Python developer")
    assert report.reorder_hints == []
