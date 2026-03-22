"""Tests for data loader."""

from pathlib import Path

import pytest

from cvloom.loader import load_data, load_profile


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    (d / "basics.yaml").write_text("headline: Engineer\nsummary: Great.\n")
    (d / "work.yaml").write_text(
        "- company: Acme\n  title: Dev\n  start_date: '2020-01'\n"
    )
    (d / "education.yaml").write_text(
        "- institution: Uni\n  degree: BSc\n  start_date: '2018'\n"
    )
    (d / "skills.yaml").write_text(
        "- category: Languages\n  items: [Python]\n"
    )
    projects = d / "projects"
    projects.mkdir()
    (projects / "proj.yaml").write_text(
        "name: proj\ndescription: A project.\ntags: [python]\n"
    )
    return d


@pytest.fixture
def private_dir(tmp_path: Path) -> Path:
    p = tmp_path / "private"
    p.mkdir()
    (p / "contact.yaml").write_text(
        "name: Test User\nemail: test@example.com\n"
    )
    return p


def test_load_data_public(data_dir: Path) -> None:
    result = load_data(data_dir, private_dir=None, public=True)
    assert result["contact"]["name"] == "Your Name"
    assert result["basics"]["headline"] == "Engineer"
    assert len(result["work"]) == 1
    assert len(result["projects"]) == 1


def test_load_data_private(data_dir: Path, private_dir: Path) -> None:
    result = load_data(data_dir, private_dir=private_dir, public=False)
    assert result["contact"]["name"] == "Test User"


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
