"""Tests for JSON Resume import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from cvloom import importer
from cvloom.cli import cli
from cvloom.export import to_json_resume
from cvloom.loader import load_data
from cvloom.models import ResolvedProfile

# JSON Resume "personal" fields that must never land in data/.
PII_VALUES = ["Jane Doe", "jane@example.com", "+1 555-1234", "San Francisco, CA"]


def _sample_resume() -> dict[str, Any]:
    return {
        "basics": {
            "name": "Jane Doe",
            "label": "Senior Software Engineer",
            "email": "jane@example.com",
            "phone": "+1 555-1234",
            "url": "https://jane.dev",
            "summary": "Backend engineer with a decade of distributed-systems work.",
            "location": {"city": "San Francisco", "region": "CA", "countryCode": "US"},
            "profiles": [
                {"network": "LinkedIn", "username": "janedoe", "url": "https://x/janedoe"},
                {"network": "GitHub", "username": "janedoe", "url": "https://gh/janedoe"},
                {"network": "Mastodon", "url": "https://mas.to/@jane"},
            ],
        },
        "work": [
            {
                "name": "Acme Corp",
                "position": "Senior Engineer",
                "startDate": "2021-03",
                "endDate": "Present",
                "location": "Remote",
                "highlights": ["Led the migration to microservices."],
            }
        ],
        "education": [
            {
                "institution": "State University",
                "studyType": "BSc",
                "area": "Computer Science",
                "startDate": "2014",
                "endDate": "2018",
                "score": "3.8 GPA",
                "highlights": ["Teaching assistant."],
            }
        ],
        "skills": [
            {"name": "Languages", "keywords": ["Python", "Go"]},
            {"name": "Cloud", "keywords": ["AWS", "Kubernetes"]},
        ],
        "projects": [
            {
                "name": "cvloom",
                "description": "CV-as-YAML tool.",
                "url": "https://github.com/x/cvloom",
                "startDate": "2026-01",
                "keywords": ["python", "cli"],
                "highlights": ["Single source of truth."],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------


def test_from_json_resume_splits_pii_into_contact() -> None:
    imported = importer.from_json_resume(_sample_resume())
    assert imported.contact["name"] == "Jane Doe"
    assert imported.contact["email"] == "jane@example.com"
    assert imported.contact["phone"] == "+1 555-1234"
    assert imported.contact["website"] == "https://jane.dev"
    assert imported.contact["location"] == "San Francisco, CA, US"
    assert imported.contact["linkedin"] == "janedoe"
    assert imported.contact["github"] == "janedoe"


def test_from_json_resume_maps_non_pii_basics() -> None:
    imported = importer.from_json_resume(_sample_resume())
    assert imported.basics is not None
    assert imported.basics["headline"] == "Senior Software Engineer"
    assert imported.basics["summary"].startswith("Backend engineer")
    # Non-linkedin/github profile becomes a public link, not a contact field.
    assert imported.basics["public_links"] == [{"label": "Mastodon", "url": "https://mas.to/@jane"}]
    assert "name" not in imported.basics
    assert "email" not in imported.basics


def test_from_json_resume_maps_sections() -> None:
    imported = importer.from_json_resume(_sample_resume())
    assert imported.work[0] == {
        "company": "Acme Corp",
        "title": "Senior Engineer",
        "start_date": "2021-03",
        "end_date": "Present",
        "location": "Remote",
        "highlights": ["Led the migration to microservices."],
    }
    assert imported.education[0]["degree"] == "BSc"
    assert imported.education[0]["field"] == "Computer Science"
    assert imported.education[0]["grade"] == "3.8 GPA"
    assert imported.skills[0] == {"category": "Languages", "items": ["Python", "Go"]}
    assert imported.projects[0]["tags"] == ["python", "cli"]


def test_location_prefers_explicit_address() -> None:
    doc = _sample_resume()
    doc["basics"]["location"] = {"address": "123 Main St, Springfield"}
    imported = importer.from_json_resume(doc)
    assert imported.contact["location"] == "123 Main St, Springfield"


def test_imported_data_validates_against_schema() -> None:
    imported = importer.from_json_resume(_sample_resume())
    assert importer.validate_imported(imported) == []


# ---------------------------------------------------------------------------
# Partial / malformed input
# ---------------------------------------------------------------------------


def test_partial_document_only_writes_present_sections() -> None:
    doc = {"basics": {"name": "Solo", "label": "Dev", "summary": "Hi."}}
    imported = importer.from_json_resume(doc)
    assert imported.work == []
    assert imported.education == []
    assert imported.projects == []
    assert importer.validate_imported(imported) == []


def test_non_object_document_raises() -> None:
    with pytest.raises(importer.ImportProblem):
        importer.from_json_resume(["not", "an", "object"])


def test_malformed_section_raises() -> None:
    doc = _sample_resume()
    doc["work"] = "should be a list"
    with pytest.raises(importer.ImportProblem):
        importer.from_json_resume(doc)


def test_load_json_resume_rejects_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json ", encoding="utf-8")
    with pytest.raises(importer.ImportProblem):
        importer.load_json_resume(bad)


# ---------------------------------------------------------------------------
# Writing + PII fence
# ---------------------------------------------------------------------------


def test_write_imported_keeps_pii_out_of_data(tmp_path: Path) -> None:
    imported = importer.from_json_resume(_sample_resume())
    data_dir = tmp_path / "data"
    private_dir = tmp_path / "private"
    importer.write_imported(imported, data_dir, private_dir)

    # PII lives only in private/contact.yaml.
    contact_text = (private_dir / "contact.yaml").read_text()
    for value in PII_VALUES:
        assert value in contact_text or value.replace(", US", "") in contact_text

    for data_file in data_dir.rglob("*.yaml"):
        text = data_file.read_text()
        for value in PII_VALUES:
            assert value not in text, f"PII {value!r} leaked into {data_file}"


def test_plan_writes_flags_conflicts(tmp_path: Path) -> None:
    imported = importer.from_json_resume(_sample_resume())
    data_dir = tmp_path / "data"
    private_dir = tmp_path / "private"
    data_dir.mkdir()
    (data_dir / "work.yaml").write_text("[]\n")

    plans = importer.plan_writes(imported, data_dir, private_dir)
    conflicts = {p.path.name for p in plans if p.exists}
    assert conflicts == {"work.yaml"}


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_round_trip_core_fields_stable(tmp_path: Path) -> None:
    original = _sample_resume()
    imported = importer.from_json_resume(original)
    data_dir = tmp_path / "data"
    private_dir = tmp_path / "private"
    importer.write_imported(imported, data_dir, private_dir)

    loaded = load_data(data_dir, private_dir, public=False)
    resolved = ResolvedProfile(
        profile={},
        data=loaded,
        show_sections={},
        section_order=[],
        template_name="x",
        output_filename="x",
    )
    exported = to_json_resume(resolved)

    assert exported["basics"]["name"] == original["basics"]["name"]
    assert exported["basics"]["label"] == original["basics"]["label"]
    assert exported["basics"]["summary"] == original["basics"]["summary"]
    assert exported["work"][0]["name"] == "Acme Corp"
    assert exported["work"][0]["position"] == "Senior Engineer"
    assert exported["skills"][0]["keywords"] == ["Python", "Go"]
    assert exported["projects"][0]["name"] == "cvloom"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_source(root: Path) -> Path:
    source = root / "resume.json"
    source.write_text(json.dumps(_sample_resume()), encoding="utf-8")
    return source


def test_cli_import_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_source(tmp_path)
    result = CliRunner().invoke(cli, ["import", "resume.json"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "private" / "contact.yaml").exists()
    assert (tmp_path / "data" / "work.yaml").exists()
    assert (tmp_path / "data" / "projects" / "cvloom.yaml").exists()
    # PII must not be in any data/ file.
    assert "jane@example.com" not in (tmp_path / "data" / "work.yaml").read_text()


def test_cli_import_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_source(tmp_path)
    result = CliRunner().invoke(cli, ["import", "resume.json", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would write" in result.output
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "private").exists()


def test_cli_import_refuses_conflict_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_source(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "work.yaml").write_text("- company: Old\n")

    result = CliRunner().invoke(cli, ["import", "resume.json"])
    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.output
    # Untouched.
    assert "Old" in (tmp_path / "data" / "work.yaml").read_text()


def test_cli_import_force_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_source(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "work.yaml").write_text("- company: Old\n")

    result = CliRunner().invoke(cli, ["import", "resume.json", "--force"])
    assert result.exit_code == 0, result.output
    work = yaml.safe_load((tmp_path / "data" / "work.yaml").read_text())
    assert work[0]["company"] == "Acme Corp"


def test_cli_import_bad_json_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "resume.json").write_text("{ broken", encoding="utf-8")
    result = CliRunner().invoke(cli, ["import", "resume.json"])
    assert result.exit_code == 1
    assert "Import failed" in result.output


# ── publications ─────────────────────────────────────────────────────


def test_from_json_resume_maps_publications() -> None:
    imported = importer.from_json_resume(
        {
            "basics": {"name": "Jane"},
            "publications": [
                {
                    "name": "A paper",
                    "publisher": "Journal of Systems Research",
                    "releaseDate": "2018",
                    "url": "https://example.com/p",
                    "summary": "About things.",
                }
            ],
        }
    )
    assert imported.publications == [
        {
            "name": "A paper",
            "publisher": "Journal of Systems Research",
            "release_date": "2018",
            "url": "https://example.com/p",
            "summary": "About things.",
        }
    ]
    assert importer.validate_imported(imported) == []


def test_publications_written_to_data_dir(tmp_path: Path) -> None:
    """Publications carry no PII, so they belong under data/, not private/."""
    imported = importer.from_json_resume(
        {"basics": {"name": "Jane"}, "publications": [{"name": "A paper"}]}
    )
    data_dir, private_dir = tmp_path / "data", tmp_path / "private"
    plans = importer.plan_writes(imported, data_dir, private_dir)
    pub_plan = next(p for p in plans if p.path.name == "publications.yaml")
    assert pub_plan.is_private is False
    assert pub_plan.path == data_dir / "publications.yaml"

    written = importer.write_imported(imported, data_dir, private_dir)
    assert data_dir / "publications.yaml" in written
    assert yaml.safe_load((data_dir / "publications.yaml").read_text()) == [{"name": "A paper"}]


def test_publications_absent_writes_no_file(tmp_path: Path) -> None:
    imported = importer.from_json_resume({"basics": {"name": "Jane"}})
    assert imported.publications == []
    written = importer.write_imported(imported, tmp_path / "data", tmp_path / "private")
    assert not any(p.name == "publications.yaml" for p in written)


def test_from_json_resume_rejects_non_array_publications() -> None:
    with pytest.raises(importer.ImportProblem):
        importer.from_json_resume({"basics": {"name": "Jane"}, "publications": {"name": "x"}})
