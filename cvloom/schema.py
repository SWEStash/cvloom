"""JSON Schema validation for all CV data files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from rich.console import Console

_SCHEMAS_DIR = Path(__file__).parent / "schemas"
_console = Console(stderr=True)


def _load_schema(name: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(
        (_SCHEMAS_DIR / f"{name}.json").read_text()
    )
    return result


def validate(name: str, data: Any, source_path: str = "") -> list[str]:
    """Validate *data* against schema *name*. Returns a list of error messages."""
    schema = _load_schema(name)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        location = f"{source_path}:{path}" if source_path else path
        errors.append(f"{location}: {error.message}")
    return errors


def validate_all(data: dict[str, Any], private_path: str = "") -> None:
    """Validate all sections in *data*, printing errors and raising on failure."""
    all_errors: list[str] = []

    section_schemas = {
        "basics": "basics",
        "work": "work",
        "education": "education",
        "skills": "skills",
    }
    for key, schema_name in section_schemas.items():
        if key in data:
            errs = validate(schema_name, data[key], source_path=f"data/{key}.yaml")
            all_errors.extend(errs)

    if "contact" in data:
        errs = validate(
            "contact", data["contact"],
            source_path=private_path or "private/contact.yaml",
        )
        all_errors.extend(errs)

    for project in data.get("projects", []):
        slug = project.get("name", "?")
        errs = validate("project", project, source_path=f"data/projects/{slug}.yaml")
        all_errors.extend(errs)

    if all_errors:
        _console.print("[bold red]Validation errors:[/bold red]")
        for err in all_errors:
            _console.print(f"  [red]✗[/red] {err}")
        raise SystemExit(1)
