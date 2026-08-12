"""Tests for keyword gap analysis (match module)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cvloom.cli import cli
from cvloom.linter_locales import pack_for
from cvloom.match import (
    MatchReport,
    _extract_keywords,
    _suggest_section,
    analyze_match,
    looks_like_a_job_posting,
)
from cvloom.models import ResolvedProfile
from tests.conftest import make_resolved


def _make_resolved(
    work: list | None = None,
    skills: list | None = None,
    projects: list | None = None,
) -> ResolvedProfile:
    return make_resolved(
        basics={"headline": "Senior Python Engineer", "summary": "Backend specialist."},
        work=work,
        skills=skills,
        projects=projects,
    )


# ── _extract_keywords ──────────────────────────────────────────────


def test_extract_keywords_basic():
    result = _extract_keywords("Python developer with Python experience", pack_for("en"))
    assert result["python"] == 2
    assert result["developer"] == 1
    assert result["experience"] == 1


def test_extract_keywords_removes_stop_words():
    result = _extract_keywords("the and is are with for", pack_for("en"))
    assert result == {}


def test_extract_keywords_empty():
    assert _extract_keywords("", pack_for("en")) == {}


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
        work=[
            {
                "company": "Acme",
                "title": "Python Developer",
                "start_date": "2020-01",
                "highlights": ["Built microservices with Python and FastAPI."],
            }
        ],
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
        "- company: Acme\n  title: Engineer\n  location: Remote\n"
        '  start_date: "2020-01"\n  end_date: Present\n'
        "  highlights:\n    - Built scalable Python microservices handling 10k requests.\n"
        "  tags: [python]\n"
    )
    (data / "education.yaml").write_text(
        '- institution: Uni\n  degree: BSc\n  field: CS\n  location: "City"\n'
        '  start_date: "2016"\n  end_date: "2020"\n'
        "  highlights:\n    - Graduated with honours in computer science.\n"
    )
    (data / "skills.yaml").write_text("- category: Languages\n  items: [Python, Go, SQL]\n")
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
        'name: Test User\nemail: "test@example.com"\nphone: "+1 555"\nlocation: "City"\n'
    )
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "general.yaml").write_text("template: cv/ats-clean\noutput_filename: cv\n")
    return tmp_path


# ── suggestions ────────────────────────────────────────────────────


def test_suggestions_single_token_goes_to_skills():
    resolved = _make_resolved()
    report = analyze_match(resolved, "kubernetes terraform docker")
    for gap in report.gaps:
        assert report.suggestions[gap] == "skills"


def test_suggest_section_multi_word_goes_to_work():
    # A multi-word phrase is not a single token, so it belongs in work highlights.
    assert _suggest_section("stakeholder relationship management") == "work"


def test_suggest_section_long_token_goes_to_work():
    # A single token longer than 20 chars is treated as prose, not a skill.
    assert _suggest_section("hyperconvergedinfrastructure") == "work"


def test_suggest_section_short_token_goes_to_skills():
    assert _suggest_section("kubernetes") == "skills"


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
    r = _make_resolved(
        work=[
            {
                "company": "A",
                "title": "Engineer",
                "start_date": "2020-01",
                "highlights": ["Built pipelines."],
            },
            {
                "company": "B",
                "title": "Python Developer",
                "start_date": "2022-01",
                "highlights": ["Built Python microservices with FastAPI and PostgreSQL."],
            },
        ]
    )
    report = analyze_match(r, "Python FastAPI PostgreSQL microservices developer")
    assert len(report.reorder_hints) == 1
    assert "Python Developer — B" in report.reorder_hints[0]


def test_reorder_hints_empty_when_already_optimal() -> None:
    r = _make_resolved(
        work=[
            {
                "company": "A",
                "title": "Python Developer",
                "start_date": "2022-01",
                "highlights": ["Built Python microservices."],
            },
            {
                "company": "B",
                "title": "Engineer",
                "start_date": "2020-01",
                "highlights": ["Did general work."],
            },
        ]
    )
    report = analyze_match(r, "Python microservices developer")
    assert report.reorder_hints == []


def test_reorder_hints_empty_single_work_entry() -> None:
    r = _make_resolved(
        work=[
            {
                "company": "A",
                "title": "Engineer",
                "start_date": "2020-01",
                "highlights": ["Built things."],
            },
        ]
    )
    report = analyze_match(r, "Python developer")
    assert report.reorder_hints == []


# ── keyword coverage across all entry-list sections ──────────────────


def test_certification_issuer_counts_toward_coverage() -> None:
    """A JD asking for Kubernetes must not report a gap when the CV holds a
    Kubernetes certification — keyword extraction covers every entry section."""
    resolved = make_resolved(
        certifications=[{"name": "Certified Kubernetes Administrator", "issuer": "CNCF"}]
    )
    report = analyze_match(resolved, "We need Kubernetes experience.")
    assert "kubernetes" in {m.keyword for m in report.matched}
    assert "kubernetes" not in set(report.gaps)


def test_language_counts_toward_coverage() -> None:
    resolved = make_resolved(languages=[{"language": "Spanish", "fluency": "C1"}])
    report = analyze_match(resolved, "Spanish speaker preferred.")
    assert "spanish" in {m.keyword for m in report.matched}


def test_publication_publisher_counts_toward_coverage() -> None:
    resolved = make_resolved(
        publications=[{"name": "Scaling Kafka consumers", "publisher": "IEEE"}]
    )
    report = analyze_match(resolved, "Experience with Kafka required.")
    assert "kafka" in {m.keyword for m in report.matched}


def test_hidden_section_does_not_count() -> None:
    """A section switched off for the profile isn't on the CV, so it can't match."""
    resolved = make_resolved(
        certifications=[{"name": "Certified Kubernetes Administrator"}],
        show={"certifications": False},
    )
    report = analyze_match(resolved, "We need Kubernetes experience.")
    assert "kubernetes" in set(report.gaps)


# ── Is this even a job posting? ─────────────────────────────────────


def test_a_real_posting_is_recognised() -> None:
    jd = Path(__file__).parent.parent / "examples" / "stripe-infra-jd.txt"
    assert looks_like_a_job_posting(jd.read_text(encoding="utf-8"), "en")


def test_a_privacy_policy_is_not() -> None:
    """The document a "save page as" produces instead of the posting."""
    policy = (
        "Privacy Policy — last updated March 2024\n"
        "We collect information you provide directly to us, including when you\n"
        "create an account. We use cookies and similar tracking technologies.\n"
    )
    assert not looks_like_a_job_posting(policy, "en")


def test_a_cv_pasted_by_mistake_is_not_a_posting() -> None:
    cv = "Jane Doe | Senior Engineer\nReduced p99 latency by 40%.\nPython, Go, SQL.\n"
    assert not looks_like_a_job_posting(cv, "en")


def test_one_marker_is_enough() -> None:
    """A lenient bar on purpose: the check catches a wrong file, not a badly
    written posting, so a false negative costs a warning and a false positive
    costs nothing."""
    assert looks_like_a_job_posting("Backend engineer.\n\nRequirements:\n- Python\n", "en")


def test_the_spanish_markers_are_native_not_translated() -> None:
    posting = (
        "Ingeniero de Backend\n\nSe requiere experiencia en Python.\n"
        "Se ofrece contrato indefinido.\n"
    )
    assert looks_like_a_job_posting(posting, "es")
    assert not looks_like_a_job_posting(posting, "en"), "the en list must not match Spanish"


def test_an_unknown_locale_falls_back_rather_than_crashing() -> None:
    assert looks_like_a_job_posting("Responsibilities:\n- ship things\n", "fr")


def test_match_warns_on_a_file_that_is_not_a_posting(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warned, not blocked: the check is a word list, and the user can see the
    file. Stopping them would be cvloom overruling a judgement it cannot make."""
    policy = project_root / "policy.txt"
    policy.write_text("Privacy Policy\n\nWe collect information you provide to us.\n")
    monkeypatch.chdir(project_root)
    result = CliRunner().invoke(cli, ["match", "--jd", str(policy)])
    assert result.exit_code == 0
    # Whitespace-normalised: rich wraps the warning around the tmp path in it.
    flat = " ".join(result.output.split())
    assert "does not read like a job posting" in flat
    assert "Coverage:" in flat, "the command still ran"
