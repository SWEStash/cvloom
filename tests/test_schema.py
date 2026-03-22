"""Tests for schema validation."""

from cvloom.schema import validate


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
