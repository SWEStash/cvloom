"""Tests for schema validation."""

from cvloom.schema import entry_defaults, validate, validate_all


def test_valid_basics():
    data = {"headline": "Engineer", "summary": "A great engineer."}
    assert validate("basics", data) == []


def test_basics_missing_required():
    errors = validate("basics", {"headline": "Engineer"})
    assert any("summary" in e for e in errors)


def test_valid_work_entry():
    data = [{"company": "Acme", "title": "Dev", "start_date": "2020-01"}]
    assert validate("work", data) == []


def test_work_missing_required():
    errors = validate("work", [{"company": "Acme"}])
    assert any("title" in e or "start_date" in e for e in errors)


def test_valid_contact():
    data = {"name": "Jane", "email": "jane@example.com"}
    assert validate("contact", data) == []


def test_contact_missing_name():
    errors = validate("contact", {"email": "jane@example.com"})
    assert any("name" in e for e in errors)


def test_valid_skills():
    data = [{"category": "Languages", "items": ["Python", "Go"]}]
    assert validate("skills", data) == []


def test_valid_project():
    data = {"name": "myproject", "description": "A project.", "tags": ["python"]}
    assert validate("project", data) == []


def test_project_missing_tags():
    errors = validate("project", {"name": "myproject", "description": "desc"})
    assert any("tags" in e for e in errors)


# ── Education validation ───────────────────────────────────────────


def test_valid_education():
    data = [{"institution": "MIT", "degree": "BSc", "start_date": "2016"}]
    assert validate("education", data) == []


def test_education_missing_institution():
    errors = validate("education", [{"degree": "BSc", "start_date": "2016"}])
    assert any("institution" in e for e in errors)


# ── Type mismatch tests ───────────────────────────────────────────


def test_basics_headline_wrong_type():
    errors = validate("basics", {"headline": 123, "summary": "A summary."})
    assert len(errors) > 0


def test_work_highlights_wrong_type():
    errors = validate(
        "work",
        [
            {
                "company": "Acme",
                "title": "Dev",
                "start_date": "2020-01",
                "highlights": "not a list",
            },
        ],
    )
    assert len(errors) > 0


def test_skills_items_wrong_type():
    errors = validate("skills", [{"category": "Languages", "items": "Python"}])
    assert len(errors) > 0


# ── Profile schema validation ─────────────────────────────────────


def test_valid_profile_minimal():
    data = {"template": "cv/ats-clean"}
    assert validate("profile", data) == []


def test_valid_profile_full():
    data = {
        "template": "cv/ats-clean",
        "output_filename": "my-cv",
        "sections": {"work": True, "education": True, "skills": True, "projects": False},
        "select": {
            "work": {"tags": ["python"]},
            "skills": {"exclude_categories": ["Tools"]},
        },
        "section_order": ["skills", "work", "education", "projects"],
    }
    assert validate("profile", data) == []


def test_removed_profile_keys_are_rejected():
    """The old global filter is gone; an unmigrated profile must fail loudly."""
    for key, value in (("include_tags", ["python"]), ("include_entries", {"work": []})):
        errors = validate("profile", {"template": "cv/ats-clean", key: value})
        assert any(key in e for e in errors), key


def test_profile_missing_template():
    errors = validate("profile", {"output_filename": "cv"})
    assert any("template" in e for e in errors)


def test_profile_unknown_field():
    errors = validate("profile", {"template": "cv/ats-clean", "unknown": True})
    assert len(errors) > 0


# ── validate_all ──────────────────────────────────────────────────


def test_validate_all_valid_data():
    data = {
        "basics": {"headline": "Engineer", "summary": "A summary."},
        "work": [{"company": "Acme", "title": "Dev", "start_date": "2020-01"}],
        "education": [{"institution": "MIT", "degree": "BSc", "start_date": "2016"}],
        "skills": [{"category": "Languages", "items": ["Python"]}],
        "projects": [{"name": "proj", "description": "desc", "tags": ["py"]}],
        "contact": {"name": "Jane", "email": "j@example.com"},
    }
    errors = validate_all(data, private_path="dummy")
    assert errors == []


def test_validate_all_returns_errors_no_raise():
    data = {
        "basics": {"headline": 123},  # wrong type, missing summary
        "work": [],
        "education": [],
        "skills": [],
        "projects": [],
        "contact": {"name": "Jane", "email": "j@example.com"},
    }
    errors = validate_all(data, private_path="dummy")
    assert len(errors) > 0


# ── entry_defaults ───────────────────────────────────────────────────


def test_entry_defaults_array_schema():
    defaults = entry_defaults("work")
    # Optional properties, typed by the schema.
    assert defaults["location"] == ""
    assert defaults["end_date"] == ""
    assert defaults["highlights"] == []
    assert defaults["tags"] == []
    # Required properties are never defaulted.
    assert "company" not in defaults
    assert "title" not in defaults
    assert "start_date" not in defaults


def test_entry_defaults_object_schema():
    defaults = entry_defaults("project")
    assert defaults["url"] == ""
    assert defaults["start_date"] == ""
    assert defaults["highlights"] == []
    assert "name" not in defaults
    assert "tags" not in defaults  # required on projects


def test_entry_defaults_returns_fresh_containers():
    """Callers mutate these in place — they must not share state."""
    first = entry_defaults("work")
    first["highlights"].append("leaked")
    assert entry_defaults("work")["highlights"] == []


# ── publications schema ──────────────────────────────────────────────


def test_validate_publications_minimal():
    assert validate("publications", [{"name": "A paper"}]) == []


def test_validate_publications_full():
    entry = {
        "name": "A model of distributed consensus under churn",
        "publisher": "Journal of Systems Research",
        "release_date": "2018",
        "identifier": "ISBN 978-0-0000-0000-1",
        "url": "https://example.com/paper",
        "summary": "A short summary of the paper.",
        "tags": ["research"],
    }
    assert validate("publications", [entry]) == []


def test_validate_publications_requires_name():
    errors = validate("publications", [{"publisher": "IEEE"}])
    assert len(errors) == 1
    assert "name" in errors[0]


def test_validate_publications_rejects_unknown_field():
    errors = validate("publications", [{"name": "A paper", "isbn": "123"}])
    assert len(errors) == 1


def test_entry_defaults_publications():
    defaults = entry_defaults("publications")
    assert defaults["publisher"] == ""
    assert defaults["identifier"] == ""
    assert defaults["tags"] == []
    assert "name" not in defaults


# ── awards / languages schemas ───────────────────────────────────────


def test_validate_awards_minimal():
    assert validate("awards", [{"title": "Best Paper"}]) == []


def test_validate_awards_requires_title():
    assert len(validate("awards", [{"awarder": "ACM"}])) == 1


def test_validate_languages_minimal():
    assert validate("languages", [{"language": "Spanish"}]) == []


def test_validate_languages_requires_language():
    assert len(validate("languages", [{"fluency": "C1"}])) == 1


def test_validate_languages_rejects_unknown_field():
    assert len(validate("languages", [{"language": "Spanish", "level": "C1"}])) == 1


def test_entry_defaults_honours_schema_default() -> None:
    """A constrained field must default to a *valid* value, not the empty string.

    normalize_optional_fields() fills every optional key so templates can test
    it under StrictUndefined. For an enum-constrained property the typed empty
    value ("") is not a member of the enum, so filling it that way makes valid
    data fail validation.
    """
    defaults = entry_defaults("certifications")
    assert defaults["type"] == "certification"
    assert validate("certifications", [{"name": "X", **defaults}]) == []
