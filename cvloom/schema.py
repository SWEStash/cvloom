"""JSON Schema validation for all CV data files."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema

from cvloom import sections

_SCHEMAS_DIR = Path(__file__).parent / "schemas"

# Empty value to stand in for each JSON Schema type we default.
_TYPE_DEFAULTS: dict[str, Any] = {"string": "", "array": [], "object": {}}


def _load_schema(name: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((_SCHEMAS_DIR / f"{name}.json").read_text())
    return result


def entry_defaults(name: str, prop: str | None = None) -> dict[str, Any]:
    """Return empty values for every optional property schema *name* declares.

    Pass *prop* to descend into a nested object property instead of the root
    (e.g. ``entry_defaults("profile", "job_context")``).

    Templates render under Jinja2's ``StrictUndefined``, where reading a key
    that is simply absent raises instead of evaluating falsy — so ``{% if
    edu.field %}`` blows up on an entry that legitimately omits ``field``.
    Filling the schema's own optional properties keeps "optional" meaning
    optional. Required properties are left out so validation still catches
    genuinely missing data.
    """
    schema = _load_schema(name)
    if prop is not None:
        schema = schema["properties"][prop]
    entry = schema["items"] if schema.get("type") == "array" else schema
    required = set(entry.get("required", []))
    return {
        prop: copy.deepcopy(_TYPE_DEFAULTS[spec["type"]])
        for prop, spec in entry.get("properties", {}).items()
        if prop not in required and spec.get("type") in _TYPE_DEFAULTS
    }


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


def validate_all(
    data: dict[str, Any],
    private_path: str = "",
) -> list[str]:
    """Validate all sections in *data* and return the list of error messages.

    Pure: never prints or raises. Callers decide how to surface failures
    (``builder.resolve`` raises :class:`~cvloom.builder.ResolveError`).
    """
    all_errors: list[str] = []

    # basics and skills have bespoke shapes; the rest come from the registry.
    for name in ("basics", "skills"):
        if name in data:
            all_errors.extend(validate(name, data[name], source_path=f"data/{name}.yaml"))

    for section in sections.SECTIONS:
        if section.name not in data:
            continue
        if section.from_directory:
            # One file per entry — report against the file the entry came from.
            for entry in data[section.name]:
                slug = entry.get(section.label_key, "?")
                all_errors.extend(
                    validate(
                        section.schema,
                        entry,
                        source_path=f"data/{section.name}/{slug}.yaml",
                    )
                )
        else:
            all_errors.extend(
                validate(
                    section.schema,
                    data[section.name],
                    source_path=f"data/{section.name}.yaml",
                )
            )

    if "contact" in data:
        all_errors.extend(
            validate(
                "contact",
                data["contact"],
                source_path=private_path or "private/contact.yaml",
            )
        )

    return all_errors
