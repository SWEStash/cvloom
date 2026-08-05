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
9. [PDF Reading Order and Where the Date Goes](#pdf-reading-order-and-where-the-date-goes)
10. [Test Patterns](#test-patterns)

---

## Repository Layout

```
cvloom/
├── cli.py              # Click command group and all subcommands
├── builder.py          # Core pipeline: resolve() and build()
├── models.py           # ResolvedProfile, BuildResult dataclasses
├── loader.py           # YAML loading and merge, public/private contact
├── sections.py         # Section registry + shared CV data walk
├── schema.py           # JSON Schema validation (Draft 2020-12)
├── overlays.py         # Match-and-patch system for per-job customization
├── projects.py         # Shared profile/project listing behind the CLI and MCP
├── renderer.py         # Jinja2 rendering, template discovery
├── templates_meta.py   # Per-template parse-risk registry: columns, ats rating, fonts, caveat
├── filters.py          # Jinja2 filters (md, date_range, cert_groups, …) + section_title global
├── links.py            # Profile-link vocabulary: network_of, link_username, normalize_url
├── select.py           # Per-section content selection: apply_selection()
├── linter.py           # Writing lint: 22 categorized rules, LintFinding, lint()
├── trim.py             # Per-section word count analysis
├── diff.py             # Profile comparison
├── match.py            # Keyword gap analysis from job descriptions
├── export.py           # to_json_resume(), markdown, text, docx exporters
├── importer.py         # from_json_resume(); PII-aware split into data/ + private/
├── mcp_server.py       # FastMCP server exposing 16 tools
├── ai/
│   ├── provider.py     # Config loading, OpenAI-compatible client, cv_to_text()
│   ├── prompts.py      # System prompts and CV context block helpers
│   ├── models.py       # Result dataclasses: ReviewResult, CoverResult, etc.
│   ├── analyzer.py     # review() — section scoring with feedback
│   ├── cover.py        # generate_cover() — tailored cover letter
│   ├── suggest.py      # suggest() — improvement suggestions for a target role
│   └── align.py        # align() — qualitative JD alignment analysis
├── hooks/              # pre-commit PII hook, scaffolded by `init`/`sync`
├── scaffold/           # `init`/`sync` file operations, managed-file registry
│   └── samples/        # Sample YAML written by `cvloom init`
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
        ├─► select.apply_selection()     narrow the sections `select` names
        ├─► schema.validate_all()        JSON Schema validation
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

- Public/private contact mode (removes `email` and `phone` in `--public`)
- `normalize_highlights()` — converts `{id, text}` dicts to plain strings while retaining IDs for overlay matching
- `normalize_optional_fields()` — fills each entry's schema-optional keys with typed empties. Templates render under `StrictUndefined`, where an *absent* key raises rather than evaluating falsy, so `{% if edu.field %}` needs the key to exist. `contact` is excluded on purpose: its templates guard with `is defined` so `--public` redaction stays invisible.

### `select.py`

Owns per-section content selection from a profile's `select` block, so `loader` stays I/O
and merge only. Include-only for entry `tags` — an entry with no tags does not match an
include list, uniformly across every section. Skills are keyed on `category` and take both
`categories` and `exclude_categories`, because that set is closed and enumerable. Returns
warnings (unknown section/category, a selector matching nothing, untagged entries dropped)
onto `ResolvedProfile.warnings`.

### `sections.py` — the section registry

`SECTIONS` is a tuple of frozen `Section` records: the single source of truth for
cvloom's entry-list sections (work, education, projects, publications, certifications,
awards, languages). Each record carries what the pipeline needs:

| Field | Drives |
|---|---|
| `name` | data key; profile `sections` / `section_order` key |
| `schema` | which `cvloom/schemas/*.json` validates one entry |
| `label_key` | entry labels in diff and trim reports |
| `heading` | Markdown / DOCX export headings |
| `summary_label` | the CLI's post-build section summary |
| `from_directory` | `data/<name>/*.yaml` (projects) vs one `data/<name>.yaml` |
| `warn_if_missing` | whether an absent file warns; false for opt-in sections |

`loader`, `schema.validate_all`, `builder`, `cli`, `export`, `trim`, `diff` and `select` all derive
from it, so adding a section is a table entry plus its schema, template macros and
export/import mapping — not an edit across a dozen files where forgetting one fails
silently.

`skills` and `basics` are deliberately **not** in the registry: their entry shapes are
genuinely different, and forcing them in would buy uniformity at the price of exceptions
everywhere. Consumers that need them name them explicitly.

It also owns the shared data walk — `highlight_text`, `skill_name`, `entry_label`,
`iter_entry_text` / `count_words`, and `slugify`.

`tests/test_sections_registry.py` guards the two things the registry cannot derive:
`profile.json`'s `sections` / `section_order`, and the existence of each entry schema.

### `schema.py`

Validates data against JSON Schema files in `cvloom/schemas/`. Schema files cover: `basics`, `work`, `education`, `skills`, `project`, `publications`, `certifications`, `awards`, `languages`, `profile`, `contact`.

`entry_defaults(name, prop=None)` — returns the typed empty value (`""` / `[]` / `{}`) for every *optional* property a schema declares. Single source of truth for `loader.normalize_optional_fields()` and for `job_context` defaults in `builder.build()`.

`validate_all(data, raise_on_error=False)` — returns `list[str]` of error messages. When `raise_on_error=True` (the default in build), raises `SchemaError` on the first failure.

### `overlays.py`

Applies profile overlays after loading. Three overlay types:

- **Basics overlay** — shallow merge onto `data["basics"]`
- **Array section overlays** (work, education, projects) — match by field, then apply: `exclude`, field overrides, highlight pick/exclude/replace/append. `publications` is not overlay-addressable: entries carry no highlights, so there is nothing for the pick/exclude/replace machinery to act on.
- **Skills overlay** — filter categories and exclude items within categories

`validate_overlays(resolved)` checks for unmatched entries, nonexistent highlight IDs, unknown field names, and nonexistent skill categories — warnings surfaced during `resolve()`.

### `renderer.py`

Jinja2 environment with `StrictUndefined`. Template discovery:

1. Project-local `templates/` (user overrides)
2. `cvloom/templates/` (built-in)

`render(resolved, public, templates_dir)` builds the context dict and renders the template. `template_exists(name)` and `list_templates()` are helpers used for error messages.

### `filters.py`

Registered via `register_filters(env)`, which also installs the one Jinja global:

| Filter | Input | Output |
|---|---|---|
| `md` | Markdown string | HTML; unwraps single `<p>` for inline use |
| `date_range` | `start, end, sep="–"` | Formatted date range; identical endpoints collapse to one date |
| `skill_level_bar` | Level string | `<span class="skill-level skill-level-N">` — **renders no text**, so nothing an ATS can read; unused by every built-in template |
| `link_anchor` | One `basics.links` entry | Anchor whose visible text is the URL itself |
| `cert_groups` | Certification entries | `(title_key, default_heading, entries)` per group |

| Global | Signature | Purpose |
|---|---|---|
| `section_title` | `(key, default) -> str` | Profile's `section_titles` override, else the template's own wording. Reads the context, so a caller that supplies no overrides still renders. |

### `templates_meta.py`

`info_for(template_name) -> TemplateInfo | None` — the per-template parse-risk registry
(`columns`, `ats`, `fonts`, `summary`, `caveat`). Deliberately outside the linter:
`check` grades what the user wrote, and whether a layout survives PDF text extraction is
a property of the template. Surfaced by `cvloom list-templates` and warned about by
`build` and `check`. `None` means unrated — a template of the user's own — and is
reported as such rather than assumed safe. A test fails for any packaged `cv/` template
missing an entry.

### `linter.py`

`lint(resolved, rule_ids=None) -> list[LintFinding]`

Rules are stored in a module-level list `RULES: list[LintRule]`. Each `LintRule` carries a `rule_id`, `name`, `description`, `category` (`writing`/`structure`/`ats-parse`), and a `check` callable that takes a `ResolvedProfile` and returns `list[LintFinding]`. The `lint()` function iterates the list, stamps each finding with its rule's `category`, and collects all findings. Pass `rule_ids` to run a subset.

`category_counts(findings) -> dict[str, int]` — tallies findings per axis. There is deliberately no single "ATS score"; see [ATS-readiness model](../reference/ats-readiness.md).

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
- `to_text(resolved)` — plain text; same content as the Markdown export
- `to_docx(resolved)` — Word document via `python-docx` (optional dependency)

Field mapping to JSON Resume is table-driven: `_Field(src, dest, kind)` tuples per
section, applied by `_map_entry`. `kind` controls emptiness handling — `date` fields
are dropped unless they match ISO 8601 (JSON Resume has no `"Present"` sentinel; a
current role omits `endDate`). Fields with no spec equivalent are emitted under the
`x-cvloom-*` namespace and read back by `importer._restore_extensions`, so a
round-trip is lossless.

`tests/test_export_jsonresume_conformance.py` validates exports against a vendored
copy of the official schema (`tests/fixtures/jsonresume-schema.json`).

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
    data: dict[str, Any]             # resolved CV data (all sections + basics, contact)
    show_sections: dict[str, bool]   # section visibility flags
    section_order: list[str]         # render order
    template_name: str               # e.g. "cv/ats-clean"
    output_filename: str             # base filename for output
    warnings: list[str]              # non-fatal select/overlay warnings
    profile_name: str                # profile this resolved from
    section_titles: dict[str, str]   # heading overrides; empty = template defaults stand
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

Overlays are applied in `overlays.py` after selection, before rendering — so they only ever see the entries that survived `select`. The sequence for array section overlays:

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
2. Append a `LintRule(rule_id, name, description, category, check)` to the `RULES` list in `linter.py`
3. Assign a stable `rule_id` in the `wl-NNN` sequence
4. Choose a `category`: `CATEGORY_WRITING`, `CATEGORY_STRUCTURE`, or `CATEGORY_ATS_PARSE`
5. Choose `severity`: `"warning"` or `"suggestion"`

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

## PDF Reading Order and Where the Date Goes

This section records a decision that was made, reversed, and re-made on evidence.
It is here rather than in code comments because it is about the format, not about
any one function.

### A PDF has more than one reading order

A PDF says where each glyph is painted; it does not, on its own, say what order a
human reads them in. Three orders matter:

| Order | What it is | Who reads it that way |
|---|---|---|
| **Construction** | The sequence of text operators in the page content stream | Apache Tika and PDFBox *by default* (`sortByPosition=false`) — the naive end of the market |
| **Geometric** | Re-derived from glyph coordinates by clustering into lines and columns | poppler's `pdftotext`, pdfminer.six, most commercial parsers |
| **Structure** | The `/StructTreeRoot` tag tree — the order the standard actually defines | PDF/UA consumers, screen readers, accessibility tooling |

Construction order has no guaranteed relationship to reading order. A generator may
group text by font, paint templates last, or emit a right-hand column separately.
That is legal, and it is what every generator does with right-aligned content.

### What was measured

Rendering the same multi-page CV with right-aligned dates and dumping construction
order shows the date deferred to the end of the page — in WeasyPrint, in headless
Chrome, **and in a real `.docx` right tab stop exported by LibreOffice**. Word does
not solve this problem; Word users mostly sidestep it by submitting `.docx`, where a
tab is a literal character in a linear paragraph stream.

The difference that matters is elsewhere: Word and Chrome emit **tagged** PDFs and
cvloom, until this change, did not. In the structure tree, every date sits
immediately after its own title, on its own baseline, in the correct entry —
including for the last entry on a page.

### The decisions

1. **`builder._render_pdf` passes `pdf_tags=True`.** WeasyPrint defaults it off. A
   tagged PDF carries logical reading order explicitly and is also the accessible
   form of the document. There is no reason to ship the untagged one.
2. **The date is inline on the meta line, not right-aligned.** See below: a
   right-hand date column leaves an empty band that geometric extractors read as a
   column, and how wide that band is depends on the user's content.
3. **`extract.py` ships five engines, not three.** `construction` and `structure`
   were added so both ends of the spectrum are measured rather than assumed. The
   spread between engines *is* the measurement; agreement is evidence, not a
   certificate.

### Where it landed

Right-aligned dates were removed. The date runs inline on the entry's meta line —
`company · date · location` — in every template except `cv/sidebar-compact`, which
is rated unsafe for a separate reason.

The decisive measurement was not about alignment. What geometric extractors detect
is an **empty vertical band down the right of the page**, and whether one exists is
governed by the user's bullet length, not by the template:

| Bullet length | construction | poppler | pypdf | pdfminer | structure |
|---|---|---|---|---|---|
| ~30 chars | 0 | 1 | 0 | 14 | 0 |
| ~95 chars | 0 | 0 | 0 | 0 | 0 |

That makes it uncontrollable from the template, which is why it was removed rather
than tuned. Capping the header width does not help — the gap grows back whenever a
title is short.

Ruled out by measurement, so nobody re-tests them:

- **The producer.** WeasyPrint, headless Chrome and a hand-written PDF are identical.
- **Text-run structure.** One `TJ` run with an internal offset (the Word tab-stop
  shape) extracts exactly like two separate text objects at the same positions.
- **Tagging, for these engines.** poppler and pdfminer never read the structure tree.

The one construct that works is filling the band with glyphs — a dot leader scores 0
everywhere in a hand-built PDF. No CSS implementation reproduces it: floating or
flexing the date to the margin moves it to a separate paint pass, fixing poppler and
pdfminer while breaking construction order and pypdf. Emitting that construct would
need direct PDF generation, which means owning layout — line breaking, pagination,
keep-together — that WeasyPrint currently provides.

### What is not claimed

Turning tags on does not change what poppler, pypdf, or pdfminer return — they
ignore the structure tree. Whether a given ATS honours tags is unverified, and
vendor marketing on this subject is not a source. What is verifiable is that a
tagged PDF is standards-correct where an untagged one is ambiguous, and that with the
date inline every engine reads every date inside its own entry — measured on
multi-page documents with short bullets, the worst case.

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
