# Architecture

[Back to README](../../README.md)

This document describes how cvloom is structured internally — the build pipeline, module responsibilities, data flow, and key design decisions. It targets contributors and developers who want to understand or extend the codebase.

---

## Table of Contents

1. [Repository Layout](#repository-layout)
2. [Build Pipeline](#build-pipeline)
3. [Module Reference](#module-reference)
4. [Data Models](#data-models)
5. [Overlay System](#overlay-system)
6. [Linter Architecture](#linter-architecture)
7. [AI Subsystem](#ai-subsystem)
8. [MCP Server](#mcp-server)
9. [Test Patterns](#test-patterns)

---

## Repository Layout

```
cvloom/
├── cli.py              # Click command group and all subcommands
├── builder.py          # Core pipeline: resolve() and build()
├── models.py           # ResolvedProfile, BuildResult dataclasses
├── loader.py           # YAML loading, tag filtering, public/private contact
├── schema.py           # JSON Schema validation (Draft 2020-12)
├── overlays.py         # Match-and-patch system for per-job customization
├── renderer.py         # Jinja2 rendering, template discovery
├── filters.py          # Custom Jinja2 filters: md, date_range, skill_level_bar
├── linter.py           # ATS linter: 17 rules, LintFinding, lint()
├── trim.py             # Per-section word count analysis
├── diff.py             # Profile comparison
├── match.py            # Keyword gap analysis from job descriptions
├── export.py           # to_json_resume(), markdown, linkedin, docx exporters
├── mcp_server.py       # FastMCP server exposing 16 tools
├── ai/
│   ├── provider.py     # Config loading, OpenAI-compatible client, cv_to_text()
│   ├── prompts.py      # System prompts and CV context block helpers
│   ├── models.py       # Result dataclasses: ReviewResult, CoverResult, etc.
│   ├── analyzer.py     # review() — section scoring with feedback
│   ├── cover.py        # generate_cover() — tailored cover letter
│   ├── suggest.py      # suggest() — improvement suggestions for a target role
│   └── align.py        # align() — qualitative JD alignment analysis
├── schemas/            # JSON Schema files for each data type
└── templates/          # Built-in Jinja2 templates
    ├── base.html.j2
    ├── cv/
    ├── cover-letter/
    └── project-summary/

tests/                  # pytest test suite
```

---

## Build Pipeline

The central pipeline is:

```
cli.py
  └─► builder.resolve()
        ├─► loader.load_data()           load YAML from data/ and private/
        ├─► schema.validate_all()        JSON Schema validation
        ├─► loader.apply_force_includes() force-include tag-excluded entries
        ├─► loader.normalize_highlights() convert {id, text} dicts to strings (keep IDs)
        ├─► overlays.apply_overlays()    match-and-patch profile overlays
        └─► returns ResolvedProfile

  └─► builder.build()  (wraps resolve(), then:)
        ├─► renderer.render()            Jinja2 → HTML string
        ├─► write HTML to dist/
        ├─► WeasyPrint HTML → PDF
        └─► returns BuildResult
```

### `resolve()` vs `build()`

`resolve()` is a **pure function** — no file I/O, no rendering, no side effects. It returns a `ResolvedProfile` with fully patched data. Use it for programmatic access (linter, trim, diff, match, export, MCP tools) without triggering a build.

`build()` calls `resolve()`, then renders and writes files. It returns a `BuildResult` containing the resolved profile, rendered HTML, file paths, and metrics.

---

## Module Reference

### `cli.py`

Click command group with all top-level commands. Each command:
1. Validates inputs and constructs `Path` objects from `Path.cwd()`
2. Calls the appropriate domain function (builder, linter, etc.)
3. Formats and prints output using `rich`

The `ai` subgroup is defined here and delegates to `ai/analyzer.py`, `ai/cover.py`, `ai/suggest.py`, `ai/align.py`.

### `builder.py`

Two public entry points:

```python
def resolve(data_dir, private_dir, profiles_dir, profile_name, template_override, public) -> ResolvedProfile
def build(data_dir, private_dir, profiles_dir, output_dir, profile_name, ...) -> BuildResult
```

`builder.py` orchestrates all other modules. It does not contain business logic — it delegates to `loader`, `schema`, `overlays`, and `renderer`.

### `loader.py`

Loads and merges YAML from `data/` and `private/`. Key responsibilities:
- Tag-based filtering of work and project entries
- Public/private contact mode (removes `email` and `phone` in `--public`)
- `apply_force_includes()` — second unfiltered load to retrieve excluded entries and merge them back
- `normalize_highlights()` — converts `{id, text}` dicts to plain strings while retaining IDs for overlay matching

### `schema.py`

Validates data against JSON Schema files in `cvloom/schemas/`. Schema files cover: `basics`, `work`, `education`, `skills`, `project`, `profile`, `contact`.

`validate_all(data, raise_on_error=False)` — returns `list[str]` of error messages. When `raise_on_error=True` (the default in build), raises `SchemaError` on the first failure.

### `overlays.py`

Applies profile overlays after loading. Three overlay types:
- **Basics overlay** — shallow merge onto `data["basics"]`
- **Array section overlays** (work, education, projects) — match by field, then apply: `exclude`, field overrides, highlight pick/exclude/replace/append
- **Skills overlay** — filter categories and exclude items within categories

`validate_overlays(resolved)` checks for unmatched entries, nonexistent highlight IDs, unknown field names, and nonexistent skill categories — warnings surfaced during `resolve()`.

### `renderer.py`

Jinja2 environment with `StrictUndefined`. Template discovery:
1. Project-local `templates/` (user overrides)
2. `cvloom/templates/` (built-in)

`render(resolved, public, templates_dir)` builds the context dict and renders the template. `template_exists(name)` and `list_templates()` are helpers used for error messages.

### `filters.py`

Three custom Jinja2 filters registered via `register_filters(env)`:

| Filter | Input | Output |
|---|---|---|
| `md` | Markdown string | HTML; unwraps single `<p>` for inline use |
| `date_range` | `start, end` | Formatted date range string |
| `skill_level_bar` | Level string | `<span class="skill-level skill-level-N">` |

### `linter.py`

`lint(resolved, rule_ids=None) -> list[LintFinding]`

Rules are stored in a module-level list `RULES: list[LintRule]`. Each `LintRule` is a callable that takes a `ResolvedProfile` and returns `list[LintFinding]`. The `lint()` function iterates the list and collects all findings. Pass `rule_ids` to run a subset.

`ats_score(findings) -> int` — computes 0–100 score: `100 - warnings×5 - suggestions×2`, floored at 0.

### `trim.py`

`analyze(resolved, target_pages) -> TrimReport`

Counts words per section and computes cut recommendations to reach the page target. Word counting strips HTML tags and CSS blocks.

### `diff.py`

`compare(resolved_a, resolved_b) -> ProfileDiff`

Compares sections, entries, word counts, and highlight counts between two resolved profiles. Entry comparison is by company/institution/name key.

### `match.py`

`analyze_match(resolved, jd_text) -> MatchReport`

Tokenizes CV content and JD text, removes stop words, classifies keywords as matched or gap, sorts by JD frequency. `MatchReport.reorder_hints` compares JD keyword overlap per work entry and suggests reordering.

### `export.py`

- `to_json_resume(resolved)` — maps `ResolvedProfile` to JSON Resume schema
- `to_markdown(resolved)` — plain Markdown
- `to_linkedin(resolved)` — plain text structured for LinkedIn sections
- `to_docx(resolved)` — Word document via `python-docx` (optional dependency)

### `mcp_server.py`

FastMCP server. Each tool function:
1. Resolves `project_root` (defaults to `Path.cwd()`)
2. Calls the appropriate domain function
3. Returns a JSON string

AI tools check `ai.provider.is_configured()` and return `{"error": "..."}` if not set rather than raising.

---

## Data Models

### `ResolvedProfile`

```python
@dataclass
class ResolvedProfile:
    profile: dict[str, Any]          # raw profile YAML
    data: dict[str, Any]             # resolved CV data (work, education, skills, projects, basics, contact)
    show_sections: dict[str, bool]   # section visibility flags
    section_order: list[str]         # render order
    template_name: str               # e.g. "cv/ats-single"
    output_filename: str             # base filename for output
```

### `BuildResult`

```python
@dataclass
class BuildResult:
    resolved: ResolvedProfile
    html: str
    html_path: Path | None
    pdf_path: Path | None
    words: int
    pages: int
    section_word_counts: dict[str, int]
```

### `LintFinding`

```python
@dataclass
class LintFinding:
    rule_id: str
    severity: str                    # "warning" | "suggestion"
    section: str
    entry: str
    bullet_index: int | None
    bullet_text: str | None
    message: str
    fix_hint: str
```

---

## Overlay System

Overlays are applied in `overlays.py` after loading and force-includes, before rendering. The sequence for array section overlays:

1. Find the target entry using `match` field(s) — fails silently if not found (warning emitted)
2. If `exclude: true`, remove the entry entirely
3. Apply field overrides (e.g. `title`)
4. Apply highlight operations in order:
   - **Mode filter** (`pick` or `exclude`) — select or remove by highlight ID
   - **Replace** — swap text of specific highlights by ID
   - **Append** — add new highlights to the end

Highlights without IDs cannot be targeted by `pick`/`exclude`/`replace` but are kept in `all` mode and appear in rendered output.

---

## Linter Architecture

Adding a new rule:

1. Define a function `def check_my_rule(resolved: ResolvedProfile) -> list[LintFinding]`
2. Append it to the `RULES` list in `linter.py`
3. Assign a stable `rule_id` in the `ats-NNN` sequence
4. Choose `severity`: `"warning"` (counts toward score ×5) or `"suggestion"` (×2)

Rules that check hidden sections should respect `resolved.show_sections` — skip sections with `show_sections[section] == False`.

---

## AI Subsystem

The AI subsystem is structured to keep each command self-contained:

```
ai/provider.py   ← shared: config, client factory, cv_to_text()
ai/prompts.py    ← shared: system prompts, context block helpers
ai/models.py     ← shared: result dataclasses

ai/analyzer.py   ← review():  build prompt → call API → parse JSON response → ReviewResult
ai/cover.py      ← generate_cover(): same pattern → CoverResult
ai/suggest.py    ← suggest():  same pattern → SuggestResult
ai/align.py      ← align():    runs match() first, passes keyword analysis as context → AlignResult
```

`cv_to_text(data, show_sections)` in `provider.py` serializes the resolved CV to plain text for LLM input. It respects section visibility.

`ai/align.py` is the only AI command that calls another domain function (`match.analyze_match`) before calling the LLM — it passes the keyword gap analysis as structured context so the AI can focus on qualitative insights rather than rediscovering keyword gaps.

All AI functions require `openai` (installed via `--extra ai`). They import it at function call time so the rest of the codebase works without it.

---

## MCP Server

The MCP server uses **FastMCP** (from the `fastmcp` package, installed via `--extra mcp`). Each tool is a plain Python function decorated with `@mcp.tool()`.

Tools follow a consistent pattern:
```python
@mcp.tool()
def tool_name(param: str, project_root: str | None = None) -> str:
    root = Path(project_root) if project_root else Path.cwd()
    result = domain_function(root / "data", root / "private", ...)
    return json.dumps(result)
```

AI tools add an extra guard:
```python
if not is_configured():
    return json.dumps({"error": "CVLOOM_AI_BASE_URL is not set"})
```

---

## Test Patterns

Tests live in `tests/`. The test suite uses `pytest` with no mocking of the database or filesystem — tests operate on real temporary directories.

```bash
uv run pytest                          # run all tests
uv run pytest tests/test_builder.py   # single file
uv run pytest -k "test_overlay"       # filter by name
```

Typical fixture pattern:
```python
@pytest.fixture
def project(tmp_path):
    # write minimal YAML files to tmp_path/data/, tmp_path/profiles/, etc.
    return tmp_path

def test_something(project):
    result = builder.resolve(project / "data", project / "private", project / "profiles")
    assert ...
```

Type checking: `uv run mypy cvloom` (strict mode). All public functions must have full annotations.

Linting: `uv run ruff check cvloom tests`. Line length 100, target Python 3.11, rules E/F/I/UP.
