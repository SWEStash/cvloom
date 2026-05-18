# Contributing

[Back to README](../../README.md)

This guide covers how to set up the development environment, run tests, add a new linter rule, and submit a pull request.

---

## Development Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/SWEStash/cvloom
cd cvloom
uv sync --all-extras
```

`--all-extras` installs all optional dependency groups (`ai`, `mcp`, `docx`) and dev dependencies (`pytest`, `ruff`, `mypy`).

---

## Running Tests

```bash
uv run pytest                          # all tests
uv run pytest tests/test_builder.py   # single file
uv run pytest -k "test_overlay"       # filter by name
uv run pytest --tb=short              # shorter tracebacks
```

Tests use real temporary directories — no mocking of the filesystem. See [Architecture](architecture.md#test-patterns) for the standard fixture pattern.

---

## Code Quality

```bash
uv run ruff check cvloom tests      # lint
uv run ruff format cvloom tests     # auto-format
uv run mypy cvloom                  # type-check (strict mode)
```

**Ruff rules:** E, F, I, UP. Line length 100. Target Python 3.11.

**mypy:** strict mode. All public functions must have type annotations. Use `from __future__ import annotations` at the top of every module.

---

## Adding a New Linter Rule

1. **Open `cvloom/linter.py`.**

2. **Define your check function:**

```python
def _check_my_rule(resolved: ResolvedProfile) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for entry in resolved.data.get("work", []):
        if not resolved.show_sections.get("work", True):
            continue
        # ... your check logic ...
        if condition_met:
            findings.append(LintFinding(
                rule_id="ats-018",
                severity="warning",          # or "suggestion"
                section="work",
                entry=entry["company"],
                bullet_index=None,           # or index into highlights
                bullet_text=None,            # or the highlight text
                message="Description of what was detected",
                fix_hint="Actionable fix suggestion",
            ))
    return findings
```

3. **Register it in `RULES`:**

```python
RULES: list[LintRule] = [
    _check_passive_voice,
    ...
    _check_my_rule,       # add at the end
]
```

4. **Update the docs** — add a row to the Quick Reference table in `docs/reference/ats-linter-rules.md` and a full `###` section with bad/good examples.

5. **Write a test** in `tests/test_linter.py` covering at least one triggering case and one clean case.

6. **Update the CHANGELOG** under `[Unreleased]`.

---

## Commit Style

Conventional Commits format:

```
feat: add ats-018 linter rule for missing role description
fix: passive voice rule no longer flags adjectives ending in -nt
docs: update ATS linter reference with ats-018
test: add linter tests for ats-018
refactor: extract highlight iteration into helper
```

One commit per logical change. Keep commit messages under 72 characters in the subject line.

---

## PR Checklist

Before opening a pull request:

- [ ] `uv run pytest` — all tests pass
- [ ] `uv run ruff check cvloom tests` — no lint errors
- [ ] `uv run mypy cvloom` — no type errors
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New templates include a render test in `tests/`
- [ ] New linter rules include tests for both triggering and clean cases
- [ ] New MCP tools include a test and updated tool count in `docs/reference/mcp-server.md`
- [ ] Public API additions include type annotations

---

## Project Structure

See [Architecture](architecture.md) for a full description of each module and the build pipeline.
