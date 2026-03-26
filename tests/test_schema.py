"""Tests for schema validation."""

from cvloom.schema import validate, validate_all


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
    errors = validate("work", [
        {"company": "Acme", "title": "Dev", "start_date": "2020-01", "highlights": "not a list"},
    ])
    assert len(errors) > 0


def test_skills_items_wrong_type():
    errors = validate("skills", [{"category": "Languages", "items": "Python"}])
    assert len(errors) > 0


# ── Profile schema validation ─────────────────────────────────────


def test_valid_profile_minimal():
    data = {"template": "cv/ats-single"}
    assert validate("profile", data) == []


def test_valid_profile_full():
    data = {
        "template": "cv/ats-single",
        "output_filename": "my-cv",
        "sections": {"work": True, "education": True, "skills": True, "projects": False},
        "include_tags": ["python"],
        "section_order": ["skills", "work", "education", "projects"],
    }
    assert validate("profile", data) == []


def test_profile_missing_template():
    errors = validate("profile", {"output_filename": "cv"})
    assert any("template" in e for e in errors)


def test_profile_unknown_field():
    errors = validate("profile", {"template": "cv/ats-single", "unknown": True})
    assert len(errors) > 0


# ── validate_all ──────────────────────────────────────────────────


def test_validate_all_valid_data():
    data = {
        "basics": {"headline": "Engineer", "summary": "A summary."},
        "work": [{"company": "Acme", "title": "Dev", "start_date": "2020-01"}],
        "education": [{"institution": "MIT", "degree": "BSc", "start_date": "2016"}],
        "skills": [{"category": "Languages", "items": ["Python"]}],
        "projects": [{"name": "proj", "description": "desc", "tags": ["py"]}],
        "contact": {"name": "Jane", "email": "j@e.com"},
    }
    errors = validate_all(data, private_path="dummy", raise_on_error=False)
    assert errors == []


def test_validate_all_returns_errors_no_raise():
    data = {
        "basics": {"headline": 123},  # wrong type, missing summary
        "work": [],
        "education": [],
        "skills": [],
        "projects": [],
        "contact": {"name": "Jane", "email": "j@e.com"},
    }
    errors = validate_all(data, private_path="dummy", raise_on_error=False)
    assert len(errors) > 0
