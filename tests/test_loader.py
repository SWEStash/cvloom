"""Tests for data loader."""

from pathlib import Path

import pytest

from cvloom.loader import (
    flatten_highlights,
    load_data,
    load_profile,
    normalize_highlights,
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    (d / "basics.yaml").write_text("headline: Engineer\nsummary: Great.\n")
    (d / "work.yaml").write_text("- company: Acme\n  title: Dev\n  start_date: '2020-01'\n")
    (d / "education.yaml").write_text("- institution: Uni\n  degree: BSc\n  start_date: '2018'\n")
    (d / "skills.yaml").write_text("- category: Languages\n  items: [Python]\n")
    projects = d / "projects"
    projects.mkdir()
    (projects / "proj.yaml").write_text("name: proj\ndescription: A project.\ntags: [python]\n")
    return d


@pytest.fixture
def private_dir(tmp_path: Path) -> Path:
    p = tmp_path / "private"
    p.mkdir()
    (p / "contact.yaml").write_text(
        "name: Test User\nemail: test@example.com\nphone: '+1 555 000'\n"
        "location: Test City\ngithub: testuser\n"
    )
    return p


def test_load_data_public(data_dir: Path, private_dir: Path) -> None:
    result = load_data(data_dir, private_dir=private_dir, public=True)
    assert result["contact"]["name"] == "Test User"
    assert "email" not in result["contact"]
    assert "phone" not in result["contact"]
    assert result["contact"]["location"] == "Test City"
    assert result["contact"]["github"] == "testuser"
    assert result["basics"]["headline"] == "Engineer"
    assert len(result["work"]) == 1
    assert len(result["projects"]) == 1


def test_load_data_public_no_private_dir(data_dir: Path) -> None:
    result = load_data(data_dir, private_dir=None, public=True)
    assert result["contact"]["name"] == "Your Name"
    assert "email" not in result["contact"]
    assert "phone" not in result["contact"]


def test_load_data_public_name_override(data_dir: Path, tmp_path: Path) -> None:
    p = tmp_path / "private2"
    p.mkdir()
    (p / "contact.yaml").write_text(
        "name: Real Name\npublic_name: Public Alias\nemail: r@example.com\n"
    )
    result = load_data(data_dir, private_dir=p, public=True)
    assert result["contact"]["name"] == "Public Alias"
    assert "public_name" not in result["contact"]
    assert "email" not in result["contact"]


def test_load_data_private_strips_public_name(data_dir: Path, tmp_path: Path) -> None:
    p = tmp_path / "private3"
    p.mkdir()
    (p / "contact.yaml").write_text(
        "name: Real Name\npublic_name: Public Alias\nemail: r@example.com\n"
    )
    result = load_data(data_dir, private_dir=p, public=False)
    assert result["contact"]["name"] == "Real Name"
    assert "public_name" not in result["contact"]
    assert result["contact"]["email"] == "r@example.com"


def test_load_data_private(data_dir: Path, private_dir: Path) -> None:
    result = load_data(data_dir, private_dir=private_dir, public=False)
    assert result["contact"]["name"] == "Test User"
    assert result["contact"]["email"] == "test@example.com"


def test_tag_filtering(data_dir: Path) -> None:
    result = load_data(data_dir, private_dir=None, public=True, include_tags=["python"])
    assert len(result["projects"]) == 1

    result2 = load_data(data_dir, private_dir=None, public=True, include_tags=["rust"])
    assert len(result2["projects"]) == 0


def test_load_profile(tmp_path: Path) -> None:
    p = tmp_path / "general.yaml"
    p.write_text("template: cv/ats-single\noutput_filename: cv\n")
    profile = load_profile(p)
    assert profile["template"] == "cv/ats-single"


def test_load_profile_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path / "nope.yaml")


# ── Edge cases ─────────────────────────────────────────────────────


def test_load_data_missing_projects_dir(tmp_path: Path) -> None:
    d = tmp_path / "data2"
    d.mkdir()
    (d / "basics.yaml").write_text("headline: X\nsummary: Y.\n")
    (d / "work.yaml").write_text("[]\n")
    (d / "education.yaml").write_text("[]\n")
    (d / "skills.yaml").write_text("[]\n")
    result = load_data(d, private_dir=None, public=True)
    assert result["projects"] == []


def test_load_data_empty_yaml(tmp_path: Path) -> None:
    d = tmp_path / "data3"
    d.mkdir()
    (d / "basics.yaml").write_text("headline: X\nsummary: Y.\n")
    (d / "work.yaml").write_text("")  # empty file → yaml.safe_load returns None
    (d / "education.yaml").write_text("")
    (d / "skills.yaml").write_text("")
    (d / "projects").mkdir()
    result = load_data(d, private_dir=None, public=True)
    # Empty YAML files return None from yaml.safe_load
    assert result["work"] is None or result["work"] == []
    assert result["education"] is None or result["education"] == []
    assert result["skills"] is None or result["skills"] == []


# ── Highlight normalization ────────────────────────────────────────


def test_normalize_highlights_strings():
    entries = [{"highlights": ["Built things.", "Fixed bugs."]}]
    normalize_highlights(entries)
    assert all(isinstance(h, dict) for h in entries[0]["highlights"])
    assert entries[0]["highlights"][0]["text"] == "Built things."


def test_normalize_highlights_already_dicts():
    entries = [{"highlights": [{"id": "a", "text": "Built."}]}]
    normalize_highlights(entries)
    assert entries[0]["highlights"][0]["id"] == "a"


def test_flatten_highlights():
    entries = [{"highlights": [{"id": "a", "text": "Built."}, {"id": "b", "text": "Fixed."}]}]
    flatten_highlights(entries)
    assert entries[0]["highlights"] == ["Built.", "Fixed."]


def test_normalize_flatten_roundtrip():
    original = [{"highlights": ["One.", "Two."]}]
    normalize_highlights(original)
    flatten_highlights(original)
    assert original[0]["highlights"] == ["One.", "Two."]
