"""Tests for builder utilities and resolve()."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from cvloom.builder import (
    ResolveError,
    _estimate_pages,
    _pdf_filename,
    build_project,
    resolve,
)
from cvloom.cli import _section_summary
from cvloom.models import ResolvedProfile
from cvloom.renderer import list_templates, template_exists
from cvloom.sections import count_words
from tests.conftest import SPARSE_PROJECT_FILES, make_project, make_resolved

# ── _estimate_pages ─────────────────────────────────────────────────


def test_estimate_pages_single():
    html = "<p>" + " ".join(["word"] * 200) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 200
    assert pages == 1


def test_estimate_pages_two():
    html = "<p>" + " ".join(["word"] * 700) + "</p>"
    words, pages = _estimate_pages(html)
    assert words == 700
    assert pages == 2


def test_estimate_pages_strips_style_blocks():
    style = "<style>.foo { border-bottom: 1px solid red; color: blue; }</style>"
    body = "<p>" + " ".join(["word"] * 100) + "</p>"
    html = style + body
    words, _ = _estimate_pages(html)
    assert words == 100


# ── _section_summary ────────────────────────────────────────────────


def test_section_summary_all():
    data = {
        "work": [{}] * 3,
        "education": [{}] * 1,
        "skills": [{}] * 4,
        "projects": [{}] * 2,
    }
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert "work×3" in result
    assert "edu×1" in result
    assert "skills×4" in result
    assert "projects×2" in result


def test_section_summary_hidden():
    data = {
        "work": [{}] * 2,
        "education": [{}] * 1,
        "skills": [{}] * 3,
        "projects": [{}] * 5,
    }
    show = {"work": True, "education": False, "skills": True, "projects": False}
    result = _section_summary(data, show)
    assert "work×2" in result
    assert "edu" not in result
    assert "skills×3" in result
    assert "projects" not in result


def test_section_summary_empty_data():
    data: dict = {}
    show = {"work": True, "education": True, "skills": True, "projects": True}
    result = _section_summary(data, show)
    assert result == ""


# ── sections.count_words ────────────────────────────────────────────


def test_word_count_by_section():
    data = {
        "basics": {"headline": "Software Engineer", "summary": "A great engineer."},
        "work": [
            {"company": "Acme", "title": "Engineer", "highlights": ["Built things fast."]},
        ],
        "skills": [
            {"category": "Languages", "items": ["Python", "Go"]},
        ],
        "education": [],
        "projects": [],
    }
    show = {"work": True, "education": True, "skills": True, "projects": True}
    resolved = ResolvedProfile(
        profile={},
        data=data,
        show_sections=show,
        section_order=[],
        template_name="cv/ats-clean",
        output_filename="cv",
    )
    counts = count_words(resolved)
    assert counts["basics"] > 0
    assert counts["work"] > 0
    assert counts["skills"] > 0


# ── _pdf_filename ────────────────────────────────────────────────────


def _make_resolved_for_pdf(
    contact_name: str = "Jane Doe",
    output_filename: str = "cv",
    pdf_filename_format: str | None = None,
    profile_name: str = "general",
) -> ResolvedProfile:
    profile: dict = {}
    if pdf_filename_format:
        profile["pdf_filename_format"] = pdf_filename_format
    return make_resolved(
        profile=profile,
        contact={"name": contact_name},
        show={},
        section_order=[],
        output_filename=output_filename,
        profile_name=profile_name,
    )


def test_pdf_filename_disambiguates_by_profile():
    """Two profiles sharing a contact must not collide on one PDF name.

    Regression: the default was contact-derived only, so building N profiles
    left a single PDF — whichever built last silently overwrote the rest.
    """
    general = _make_resolved_for_pdf(profile_name="general")
    tailored = _make_resolved_for_pdf(profile_name="data-ai")
    assert _pdf_filename(general) != _pdf_filename(tailored)


def test_pdf_filename_profile_token():
    resolved = _make_resolved_for_pdf(
        profile_name="data-ai", pdf_filename_format="{profile}_{last}"
    )
    assert _pdf_filename(resolved) == "data-ai_Doe"


def test_pdf_filename_derives_from_contact_name():
    resolved = _make_resolved_for_pdf(contact_name="Jane Doe", profile_name="general")
    assert _pdf_filename(resolved) == "Jane_Doe_Resume_general"


def test_pdf_filename_single_name():
    resolved = _make_resolved_for_pdf(contact_name="Mononym", profile_name="general")
    assert _pdf_filename(resolved) == "Mononym_Resume_general"


def test_pdf_filename_format_override():
    resolved = _make_resolved_for_pdf(
        contact_name="Jane Doe",
        pdf_filename_format="{first}_{last}_CV_2026",
    )
    assert _pdf_filename(resolved) == "Jane_Doe_CV_2026"


def test_pdf_filename_format_name_placeholder():
    resolved = _make_resolved_for_pdf(
        contact_name="Jane Doe",
        pdf_filename_format="{name}_Resume",
    )
    assert _pdf_filename(resolved) == "Jane_Doe_Resume"


def test_pdf_filename_fallback_on_empty_name():
    resolved = _make_resolved_for_pdf(contact_name="", output_filename="my-cv")
    assert _pdf_filename(resolved) == "my-cv"


# ── resolve() ───────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project structure for resolve() tests."""
    return make_project(tmp_path)


def test_resolve_returns_resolved_profile(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        profile_name="general",
        public=True,
    )
    assert result.template_name == "cv/ats-clean"
    assert result.output_filename == "cv"
    assert "basics" in result.data
    assert "work" in result.data
    assert result.show_sections["work"] is True


def test_resolve_invalid_template_fails_early(project_dir: Path) -> None:
    (project_dir / "profiles" / "bad.yaml").write_text("template: cv/nonexistent\n")
    with pytest.raises(ResolveError) as excinfo:
        resolve(
            data_dir=project_dir / "data",
            private_dir=project_dir / "private",
            profiles_dir=project_dir / "profiles",
            profile_name="bad",
            public=True,
        )
    assert any("not found" in e for e in excinfo.value.errors)


def test_resolve_invalid_data_raises_resolve_error_silently(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Corrupt basics so schema validation fails.
    (project_dir / "data" / "basics.yaml").write_text("headline: 123\n")
    with pytest.raises(ResolveError) as excinfo:
        resolve(
            data_dir=project_dir / "data",
            private_dir=project_dir / "private",
            profiles_dir=project_dir / "profiles",
            profile_name="general",
            public=True,
        )
    assert excinfo.value.errors  # carries the real messages
    # resolve() is pure: it prints nothing.
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_template_exists_true() -> None:
    assert template_exists("cv/ats-clean") is True


def test_template_exists_false() -> None:
    assert template_exists("cv/nonexistent") is False


def test_list_templates_contains_known() -> None:
    templates = list_templates()
    assert "cv/ats-clean" in templates
    assert "cv/modern-single" in templates
    assert "cv/academic" in templates


def test_resolve_public_redacts_sensitive_fields(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert "email" not in result.data["contact"]
    assert "phone" not in result.data["contact"]
    assert result.data["contact"]["name"] == "Test"


# ── Sparse data: schema-optional fields omitted ─────────────────────


@pytest.fixture
def sparse_project_dir(tmp_path: Path) -> Path:
    """Project whose entries carry only their schema-required fields."""
    return make_project(tmp_path, files=SPARSE_PROJECT_FILES)


def test_resolve_fills_schema_optional_fields(sparse_project_dir: Path) -> None:
    result = resolve(
        data_dir=sparse_project_dir / "data",
        private_dir=sparse_project_dir / "private",
        profiles_dir=sparse_project_dir / "profiles",
        public=True,
    )
    assert result.data["work"][0]["location"] == ""
    assert result.data["work"][0]["highlights"] == []
    assert result.data["education"][0]["field"] == ""
    assert result.data["projects"][0]["url"] == ""
    assert result.data["projects"][0]["start_date"] == ""


def test_resolve_leaves_contact_keys_absent(sparse_project_dir: Path) -> None:
    """Contact is deliberately *not* filled — templates use ``is defined`` on it
    so that redacted (public-build) fields stay invisible rather than blank."""
    result = resolve(
        data_dir=sparse_project_dir / "data",
        private_dir=sparse_project_dir / "private",
        profiles_dir=sparse_project_dir / "profiles",
        public=True,
    )
    assert "email" not in result.data["contact"]


def test_build_fills_partial_job_context(sparse_project_dir: Path) -> None:
    (sparse_project_dir / "profiles" / "letter.yaml").write_text(
        "template: cover-letter/standard\njob_context:\n  company: Acme\n"
    )
    result = build_project(sparse_project_dir, profile_name="letter", public=True, skip_pdf=True)
    assert "Acme" in result.html
    assert "Hiring Manager" in result.html  # hiring_manager omitted → fallback


@pytest.mark.parametrize("template", list_templates())
def test_every_template_renders_sparse_data(sparse_project_dir: Path, template: str) -> None:
    result = build_project(
        sparse_project_dir,
        profile_name="general",
        template_override=template,
        public=True,
        skip_pdf=True,
    )
    assert "Test" in result.html


# ── publications section ─────────────────────────────────────────────

_PUBLICATIONS_YAML = (
    "- name: A paper on automata\n  publisher: Journal of Systems Research\n"
    '  release_date: "2016"\n  identifier: "ISBN 978-0-0000-0000-2"\n'
    "  tags: [research]\n"
    "- name: An untagged paper\n"
)


@pytest.fixture
def publications_project_dir(tmp_path: Path) -> Path:
    return make_project(tmp_path, extra={"data/publications.yaml": _PUBLICATIONS_YAML})


def test_resolve_without_publications_file(project_dir: Path) -> None:
    """publications.yaml is optional — absent means an empty section, not a warning."""
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert result.data["publications"] == []
    assert result.show_sections["publications"] is True
    assert "publications" in result.section_order


def test_resolve_loads_publications(publications_project_dir: Path) -> None:
    result = resolve(
        data_dir=publications_project_dir / "data",
        private_dir=publications_project_dir / "private",
        profiles_dir=publications_project_dir / "profiles",
        public=True,
    )
    pubs = result.data["publications"]
    assert [p["name"] for p in pubs] == ["A paper on automata", "An untagged paper"]
    # Optional keys filled from the schema.
    assert pubs[1]["publisher"] == ""
    assert pubs[1]["tags"] == []


def _publications_for(root: Path, profile_body: str) -> list[str]:
    (root / "profiles" / "tagged.yaml").write_text(f"template: cv/academic\n{profile_body}")
    result = resolve(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        profile_name="tagged",
        public=True,
    )
    return [p["name"] for p in result.data["publications"]]


def test_publications_selection_drops_untagged(publications_project_dir: Path) -> None:
    """An include list is a query; untagged content answers no query."""
    body = "select:\n  publications:\n    tags: [research]\n"
    names = _publications_for(publications_project_dir, body)
    assert names == ["A paper on automata"]


def test_publications_selection_excludes_non_matching(publications_project_dir: Path) -> None:
    body = "select:\n  publications:\n    tags: [python]\n"
    assert _publications_for(publications_project_dir, body) == []


def test_publications_untouched_without_a_selector(publications_project_dir: Path) -> None:
    """A section the profile does not name keeps every entry, tagged or not."""
    body = "select:\n  work:\n    tags: [python]\n"
    names = _publications_for(publications_project_dir, body)
    assert names == ["A paper on automata", "An untagged paper"]


def test_publications_section_can_be_hidden(publications_project_dir: Path) -> None:
    (publications_project_dir / "profiles" / "nopubs.yaml").write_text(
        "template: cv/ats-clean\nsections:\n  publications: false\n"
    )
    result = build_project(
        publications_project_dir, profile_name="nopubs", public=True, skip_pdf=True
    )
    assert "A paper on automata" not in result.html


@pytest.mark.parametrize("template", [t for t in list_templates() if t.startswith("cv/")])
def test_every_cv_template_renders_publications(
    publications_project_dir: Path, template: str
) -> None:
    result = build_project(
        publications_project_dir,
        profile_name="general",
        template_override=template,
        public=True,
        skip_pdf=True,
    )
    assert "Publications" in result.html
    assert "A paper on automata" in result.html
    assert "Journal of Systems Research" in result.html
    assert "978-0-0000-0000-2" in result.html


# ── education tags ───────────────────────────────────────────────────

_EDUCATION_TAGGED_YAML = (
    '- institution: Uni\n  degree: BSc\n  start_date: "2016"\n  tags: [degree]\n'
    '- institution: Cloud Academy\n  degree: Cert\n  start_date: "2023"\n'
    "  tags: [certification]\n"
    '- institution: Old School\n  degree: Diploma\n  start_date: "2012"\n'
)


@pytest.fixture
def tagged_education_dir(tmp_path: Path) -> Path:
    return make_project(tmp_path, extra={"data/education.yaml": _EDUCATION_TAGGED_YAML})


def _degrees_only(root: Path) -> list[str]:
    (root / "profiles" / "degrees.yaml").write_text(
        "template: cv/ats-clean\nselect:\n  education:\n    tags: [degree]\n"
    )
    result = resolve(
        data_dir=root / "data",
        private_dir=root / "private",
        profiles_dir=root / "profiles",
        profile_name="degrees",
        public=True,
    )
    return [e["institution"] for e in result.data["education"]]


def test_education_selection_drops_non_matching(tagged_education_dir: Path) -> None:
    assert "Cloud Academy" not in _degrees_only(tagged_education_dir)


def test_education_selection_drops_untagged(tagged_education_dir: Path) -> None:
    """Strict everywhere: `tags: [degree]` selects only entries tagged `degree`."""
    assert _degrees_only(tagged_education_dir) == ["Uni"]


# ── certifications section ───────────────────────────────────────────

_CERTIFICATIONS_YAML = (
    "- name: AWS Certified Solutions Architect\n  issuer: Amazon Web Services\n"
    '  date: "2023-04"\n  expiry_date: "2026-04"\n  identifier: "AWS-PSA-12345"\n'
    "  tags: [cloud]\n"
    "- name: Certified Kubernetes Administrator\n  issuer: CNCF\n"
)


@pytest.fixture
def certifications_project_dir(tmp_path: Path) -> Path:
    return make_project(tmp_path, extra={"data/certifications.yaml": _CERTIFICATIONS_YAML})


def test_resolve_without_certifications_file(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert result.data["certifications"] == []
    assert "certifications" in result.section_order


def test_resolve_loads_certifications(certifications_project_dir: Path) -> None:
    result = resolve(
        data_dir=certifications_project_dir / "data",
        private_dir=certifications_project_dir / "private",
        profiles_dir=certifications_project_dir / "profiles",
        public=True,
    )
    certs = result.data["certifications"]
    assert [c["name"] for c in certs] == [
        "AWS Certified Solutions Architect",
        "Certified Kubernetes Administrator",
    ]
    assert certs[1]["expiry_date"] == ""  # schema-optional key filled


def test_certifications_selection_drops_untagged(certifications_project_dir: Path) -> None:
    (certifications_project_dir / "profiles" / "tagged.yaml").write_text(
        "template: cv/ats-clean\nselect:\n  certifications:\n    tags: [cloud]\n"
    )
    result = resolve(
        data_dir=certifications_project_dir / "data",
        private_dir=certifications_project_dir / "private",
        profiles_dir=certifications_project_dir / "profiles",
        profile_name="tagged",
        public=True,
    )
    # AWS carries `cloud`; the untagged CKA entry does not match and is dropped.
    assert [c["name"] for c in result.data["certifications"]] == [
        "AWS Certified Solutions Architect"
    ]


def test_certifications_section_can_be_hidden(certifications_project_dir: Path) -> None:
    (certifications_project_dir / "profiles" / "nocerts.yaml").write_text(
        "template: cv/ats-clean\nsections:\n  certifications: false\n"
    )
    result = build_project(
        certifications_project_dir, profile_name="nocerts", public=True, skip_pdf=True
    )
    assert "AWS Certified" not in result.html


@pytest.mark.parametrize("template", [t for t in list_templates() if t.startswith("cv/")])
def test_every_cv_template_renders_certifications(
    certifications_project_dir: Path, template: str
) -> None:
    result = build_project(
        certifications_project_dir,
        profile_name="general",
        template_override=template,
        public=True,
        skip_pdf=True,
    )
    assert "Certifications" in result.html
    assert "AWS Certified Solutions Architect" in result.html
    assert "CNCF" in result.html
    assert "AWS-PSA-12345" in result.html


# ── awards and languages ─────────────────────────────────────────────

_AWARDS_YAML = (
    "- title: Best Paper Award\n  awarder: ACM SIGPLAN\n"
    '  date: "2019"\n  summary: For work on incremental type inference.\n'
    "  tags: [research]\n"
)
_LANGUAGES_YAML = (
    "- language: Spanish\n  fluency: Native speaker\n"
    "- language: English\n  fluency: C1\n"
    "- language: Portuguese\n"
)


@pytest.fixture
def extras_project_dir(tmp_path: Path) -> Path:
    return make_project(
        tmp_path,
        extra={"data/awards.yaml": _AWARDS_YAML, "data/languages.yaml": _LANGUAGES_YAML},
    )


def test_resolve_without_awards_or_languages(project_dir: Path) -> None:
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        public=True,
    )
    assert result.data["awards"] == []
    assert result.data["languages"] == []


def test_resolve_loads_awards_and_languages(extras_project_dir: Path) -> None:
    result = resolve(
        data_dir=extras_project_dir / "data",
        private_dir=extras_project_dir / "private",
        profiles_dir=extras_project_dir / "profiles",
        public=True,
    )
    assert result.data["awards"][0]["awarder"] == "ACM SIGPLAN"
    assert [lang["language"] for lang in result.data["languages"]] == [
        "Spanish",
        "English",
        "Portuguese",
    ]
    assert result.data["languages"][2]["fluency"] == ""  # schema-optional key filled


@pytest.mark.parametrize("template", [t for t in list_templates() if t.startswith("cv/")])
def test_every_cv_template_renders_awards_and_languages(
    extras_project_dir: Path, template: str
) -> None:
    result = build_project(
        extras_project_dir,
        profile_name="general",
        template_override=template,
        public=True,
        skip_pdf=True,
    )
    assert "Best Paper Award" in result.html
    assert "ACM SIGPLAN" in result.html
    # Languages render as one inline run, not a stack of entry blocks.
    assert "Spanish (Native speaker)" in result.html
    assert "Portuguese" in result.html


def test_language_without_fluency_renders_bare(extras_project_dir: Path) -> None:
    html = build_project(
        extras_project_dir, profile_name="general", public=True, skip_pdf=True
    ).html
    assert "Portuguese ()" not in html


# ── show_durations ──────────────────────────────────────────────────

_FREE_TEXT_DATES = (
    "- company: Acme\n  title: Engineer\n  location: Remote\n"
    '  start_date: "summer 2020"\n  end_date: "2022-03"\n'
    "  highlights:\n    - Designed and built a distributed system handling 10k requests.\n"
)


def _resolve(project: Path, profile_name: str = "general"):
    return resolve(
        data_dir=project / "data",
        private_dir=project / "private",
        profiles_dir=project / "profiles",
        profile_name=profile_name,
        public=True,
    )


def test_show_durations_defaults_off(project_dir: Path) -> None:
    """The upgrade contract: a profile that says nothing keeps its old document."""
    assert _resolve(project_dir).show_durations is False


def test_show_durations_is_read_off_the_profile(tmp_path: Path) -> None:
    project = make_project(
        tmp_path,
        extra={"profiles/general.yaml": "template: cv/ats-clean\nshow_durations: true\n"},
    )
    assert _resolve(project).show_durations is True


def test_an_unreadable_date_warns_and_still_resolves(tmp_path: Path) -> None:
    """Free-text dates are schema-legal, so this must not fail the build — but
    the entry silently losing its suffix is exactly what needs explaining."""
    project = make_project(
        tmp_path,
        extra={
            "profiles/general.yaml": "template: cv/ats-clean\nshow_durations: true\n",
            "data/work.yaml": _FREE_TEXT_DATES,
        },
    )
    result = _resolve(project)
    duration_warnings = [w for w in result.warnings if "no duration shown" in w]
    assert len(duration_warnings) == 1
    assert "Acme" in duration_warnings[0]
    assert "summer 2020" in duration_warnings[0]


def test_an_inverted_range_warns_about_the_order_not_the_format(tmp_path: Path) -> None:
    project = make_project(
        tmp_path,
        extra={
            "profiles/general.yaml": "template: cv/ats-clean\nshow_durations: true\n",
            "data/work.yaml": (
                "- company: Acme\n  title: Engineer\n"
                '  start_date: "2020-01"\n  end_date: "2019-01"\n'
                "  highlights:\n    - Designed and built a system handling 10k requests.\n"
            ),
        },
    )
    warnings = [w for w in _resolve(project).warnings if "no duration shown" in w]
    assert len(warnings) == 1
    assert "does not end after it begins" in warnings[0]


def test_no_duration_warnings_when_the_flag_is_off(tmp_path: Path) -> None:
    """The same unreadable data warns about nothing until a profile asks for a
    duration — there is no suffix missing if none was requested."""
    project = make_project(tmp_path, extra={"data/work.yaml": _FREE_TEXT_DATES})
    assert not [w for w in _resolve(project).warnings if "no duration shown" in w]


def test_readable_dates_warn_about_nothing(tmp_path: Path) -> None:
    project = make_project(
        tmp_path,
        extra={"profiles/general.yaml": "template: cv/ats-clean\nshow_durations: true\n"},
    )
    assert not [w for w in _resolve(project).warnings if "no duration shown" in w]


def test_a_hidden_work_section_warns_about_nothing(tmp_path: Path) -> None:
    """Nothing is rendered, so nothing is missing."""
    project = make_project(
        tmp_path,
        extra={
            "profiles/general.yaml": (
                "template: cv/ats-clean\nshow_durations: true\nsections:\n  work: false\n"
            ),
            "data/work.yaml": _FREE_TEXT_DATES,
        },
    )
    assert not [w for w in _resolve(project).warnings if "no duration shown" in w]


def test_resolve_reports_missing_section_as_warning_not_stderr(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing data file is the caller's business, not the terminal's.

    Printing it here strands the warning: an MCP client reads the returned
    ResolvedProfile, never resolve()'s stderr.
    """
    (project_dir / "data" / "work.yaml").unlink()
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        profile_name="general",
        public=True,
    )
    assert any("work.yaml" in w for w in result.warnings)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_resolve_reports_missing_contact_as_warning_not_stderr(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.rmtree(project_dir / "private")
    result = resolve(
        data_dir=project_dir / "data",
        private_dir=project_dir / "private",
        profiles_dir=project_dir / "profiles",
        profile_name="general",
        public=False,
    )
    assert any("contact.yaml" in w for w in result.warnings)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
