"""Validate cvloom's JSON Resume export against the real JSON Resume schema.

``export --format json-resume`` is an interop promise. Before this suite existed
the promise was never checked, and the demo project exported two violations:
``basics.email: ""`` (a --public build strips email, and "" fails the `email`
format) and ``endDate: "Present"`` (JSON Resume has no such sentinel — a current
role omits endDate).

The schema is vendored at ``tests/fixtures/jsonresume-schema.json`` so the suite
stays hermetic. Refresh it from:
https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json

Two annotation-only edits are applied to the vendored copy, neither of which can
affect validation: ``examples`` blocks are removed and the one ``description``
containing a real address is neutralised, because upstream embeds a third
party's email address that our own PII pre-commit hook (correctly) rejects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from cvloom import builder
from cvloom.export import to_json_resume
from tests.conftest import SPARSE_PROJECT_FILES, make_project, make_resolved

_SCHEMA_PATH = Path(__file__).parent / "fixtures" / "jsonresume-schema.json"


@pytest.fixture(scope="module")
def validator() -> jsonschema.Draft7Validator:
    schema = json.loads(_SCHEMA_PATH.read_text())
    return jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())


def _assert_valid(validator: jsonschema.Draft7Validator, doc: dict[str, Any]) -> None:
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    assert not errors, "\n".join(
        f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
    )


_FULL_DATA: dict[str, Any] = {
    "work": [
        {
            "company": "Acme",
            "title": "Engineer",
            "location": "Remote",
            "start_date": "2021-03",
            "end_date": "Present",
            "highlights": ["Built things."],
            "tags": ["python", "kafka"],
        }
    ],
    "education": [
        {
            "institution": "Uni",
            "degree": "BSc",
            "field": "CS",
            "start_date": "2016",
            "end_date": "2020",
            "grade": "3.9",
            "highlights": ["Dean's list."],
            "tags": ["degree"],
        }
    ],
    "skills": [{"category": "Languages", "items": ["Python", {"name": "Go", "level": "expert"}]}],
    "projects": [
        {
            "name": "proj",
            "description": "A project.",
            "tags": ["python"],
            "url": "https://example.com",
            "start_date": "2024-01",
            "highlights": ["Built it."],
        }
    ],
    "publications": [
        {
            "name": "A paper",
            "publisher": "A Journal",
            "release_date": "2018",
            "identifier": "ISBN 978-0-0000-0000-1",
            "tags": ["research"],
        }
    ],
    "certifications": [
        {
            "name": "CKA",
            "issuer": "CNCF",
            "date": "2022-09",
            "expiry_date": "2025-09",
            "identifier": "CKA-123",
            "tags": ["cloud"],
        }
    ],
    "awards": [
        {
            "title": "Best Paper Award",
            "awarder": "ACM SIGPLAN",
            "date": "2019",
            "summary": "For work on incremental type inference.",
            "tags": ["research"],
        }
    ],
    "languages": [
        {"language": "Spanish", "fluency": "Native speaker"},
        {"language": "Portuguese"},
    ],
}


def _full_resolved():
    return make_resolved(
        contact={"name": "Jane", "email": "jane@example.com", "phone": "+1 (555) 123-4567"},
        basics={
            "headline": "Engineer",
            "summary": "A summary.",
            "public_links": [{"label": "Blog", "url": "https://example.com/blog"}],
        },
        **_FULL_DATA,
    )


def test_full_export_conforms(validator: jsonschema.Draft7Validator) -> None:
    """Every section populated, including the ones with no exact spec mapping."""
    _assert_valid(validator, to_json_resume(_full_resolved()))


def test_public_export_conforms(validator: jsonschema.Draft7Validator) -> None:
    """A --public build strips email/phone; empty strings must not be emitted."""
    resolved = _full_resolved()
    resolved.data["contact"] = {"name": "Jane"}
    _assert_valid(validator, to_json_resume(resolved))


def test_sparse_export_conforms(validator: jsonschema.Draft7Validator, tmp_path: Path) -> None:
    """Entries carrying only schema-required fields still export cleanly."""
    root = make_project(tmp_path, files=SPARSE_PROJECT_FILES)
    resolved = builder.resolve_project(root, profile_name="general", public=True)
    _assert_valid(validator, to_json_resume(resolved))


def test_examples_project_exports_conform(validator: jsonschema.Draft7Validator) -> None:
    """The shipped demo project — what a new user sees first."""
    examples = Path(__file__).parent.parent / "examples"
    if not examples.exists():  # pragma: no cover - examples ship with the repo
        pytest.skip("examples/ not present")
    for profile in ("general", "example-job", "modern"):
        resolved = builder.resolve_project(examples, profile_name=profile, public=True)
        _assert_valid(validator, to_json_resume(resolved))


def test_free_text_dates_do_not_break_conformance(
    validator: jsonschema.Draft7Validator,
) -> None:
    """cvloom allows free-text dates; the export must omit rather than emit them."""
    resolved = make_resolved(
        work=[
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "summer 2020",
                "end_date": "Present",
            }
        ]
    )
    doc = to_json_resume(resolved)
    _assert_valid(validator, doc)
    assert "startDate" not in doc["work"][0]
    assert "endDate" not in doc["work"][0]
