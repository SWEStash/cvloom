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
├── config.py           # cvloom.yaml project config: ProjectConfig, load_project_config()
├── locale.py           # Locale packs: LocalePack, load_pack() with en fallback, pack_coverage()
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
├── linter.py           # Writing lint: 25 categorized rules, LintFinding, lint()
├── linter_locales/     # Per-locale lexicons, patterns, thresholds (en, es)
├── trim.py             # Per-section word count analysis
├── diff.py             # Profile comparison
├── match.py            # Keyword gap analysis from job descriptions
├── export.py           # to_json_resume(), markdown, text, docx exporters
├── importer.py         # from_json_resume(); PII-aware split into data/ + private/
├── mcp_server.py       # FastMCP server exposing 17 tools
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
├── locales/            # Locale packs (en.yaml, es.yaml); document-facing defaults only
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

The `list-*` commands are the disclosure surface: `list-templates` prints per-template parse risk, and `list-locales` prints per-locale coverage on both the document and lint axes. Neither needs a project root. `_lint_coverage()` and `_rule_cell()` both partition through `linter.rules_for()`; the counts are never literals.

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

Validates data against JSON Schema files in `cvloom/schemas/`. Schema files cover: `basics`, `work`, `education`, `skills`, `project`, `publications`, `certifications`, `awards`, `languages`, `profile`, `contact`, `project-config`, `locale`.

Note `project` types a *portfolio project entry* (`data/projects/*.yaml`); the project-level config file is `project-config`.

`entry_defaults(name, prop=None)` — returns the typed empty value (`""` / `[]` / `{}`) for every *optional* property a schema declares. Single source of truth for `loader.normalize_optional_fields()` and for `job_context` defaults in `builder.build()`.

`validate_all(data, private_path="")` — returns `list[str]` of error messages. Pure: it never prints and never raises, so callers decide how to surface failures. `builder.resolve()` turns a non-empty list into `ResolveError`; `mcp_server.validate_data` returns it as JSON.

### `config.py` — project-level configuration

`cvloom.yaml` at the project root holds settings owned by the project as a whole rather than by one build profile. A profile says how one output variant renders; this says what the project *is*. Today that is one key, `locale`.

`load_project_config(root)` returns a frozen `ProjectConfig`. An absent file is not an error — it yields defaults identical to cvloom's behaviour before the file existed. Anything present is validated against `schemas/project-config.json`, which sets `additionalProperties: false` so a typo'd key fails with the file path rather than being ignored. Failures raise `ConfigError`, which `builder` translates into `ResolveError` so callers keep catching one pipeline error type.

### `locale.py` — locale packs

A pack under `cvloom/locales/<code>.yaml` supplies the document-facing defaults cvloom would otherwise hardcode in English: `html_lang`, `section_titles`, `ongoing`, `placeholder_contact`, `cover_letter`, `months`, `date_format`. Packs govern the **rendered document only** — CLI and terminal output stay in English by design.

`en` is an ordinary pack loaded through the same path as any other, with no privileged branch, so every build exercises the mechanism and a resolution bug surfaces in the default build rather than waiting for the first non-English user. It is also the fallback: a key missing from another pack resolves to `en`'s value and reports a warning onto `ResolvedProfile.warnings`; a key missing from `en` is an error, since nothing is left to fall back to. `tests/test_locale.py` asserts `en.yaml` covers every key the code looks up, derived from `LocalePack`'s fields and `sections.TITLE_KEYS` rather than a hand-written list.

`Ongoing` binds `render` and `accepts` together because the field is bidirectional — `render` is written into the document by `filters.date_range`, `accepts` is parsed back out by the chronology lint rule and the JSON Resume export. A pack supplying only one would silently stop the other side from recognising its own output.

`load_pack` is cached and its mappings are read-only: every build shares one instance.

`ResolvedProfile.locale` carries the resolved pack so renderer, linter, export and match all read it from one place. `resolve_project()` and `build_project()` are the two entry points that know the project root, so both resolve the locale; `resolve()` and `build()` take an optional pack and stay pure.

The pack governs the **document**. The **linter and keyword analysis** are governed
separately, by `cvloom/linter_locales/` — Python, not the user-editable YAML, because
`section_titles` is content the user owns while a weak-verb list is the tool's editorial
judgement, and putting the latter in a file users edit would create a linter-configuration
API before the configuration model has been designed. The two are keyed by the same locale
code and resolved independently: a document pack with no linter data behind it falls back to
English heuristics rather than failing, and says so through the skipped-rule count.

Consumers, as of 6.7: `renderer` installs the pack as a Jinja global, so `base.html.j2` reads `locale.html_lang` and `filters.section_title` / `filters.date_range` read it off the context; `loader` uses `placeholder_contact`; `linter` matches `ongoing.accepts` for chronology, date-format and tense rules and renders `ongoing.render` in a fix hint; `export._heading` uses `section_titles` so the Markdown, text and DOCX exports head sections in the same words as the PDF; `filters.cover_letter_text` resolves `cover_letter` under a `job_context` override, and `builder` writes `today` through `LocalePack.format_date`, since `strftime("%B")` reads the C locale rather than the project's. The JSON Resume export needs nothing: it drops any non-ISO date, so an open-ended one becomes an omitted `endDate` whatever word wrote it.

The audit against English creeping back into a template is `tests/test_locale_qa.py`, which renders **every** template `renderer.list_templates()` returns under a pseudo-locale (`tests/fixtures/locales/qa.yaml`) that brackets every pack-sourced string. Two assertions: no `<h2>` came out unbracketed in the `cv/*` templates, and no pack-owned string appears unbracketed in any rendered body. Both the template list and the string list are derived — from `list_templates()` and from `LocalePack`'s fields — because the first version hardcoded the six `cv/*` templates and grepped `<h2>`, and so could not see the cover letters, which have no headings. The pack is a test fixture rather than a shipped locale, so it never appears in `available_locales()`.

`pack_coverage(code) -> PackCoverage` is the structured form of the gaps, and is what
`cvloom list-locales` and the `list_locales` MCP tool tabulate. It reads the pack *file*
rather than a loaded `LocalePack`, which has already had its gaps filled. It reports two
things `load_pack` cannot: `inherited_keys` is the structured version of the fallback
warnings, and `missing_titles` has no warning at all, because `load_pack`'s fallback is
per top-level key — a pack that defines `section_titles` but omits one heading inherits
nothing, and `filters.section_title` falls through to the raw key. The user-facing
reference is `docs/reference/locales.md`.

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
| `date_range` | `start, end, sep="-"` | Formatted date range; a missing end renders the locale pack's `ongoing.render`. Identical endpoints collapse to one date |
| `skill_level_bar` | Level string | `<span class="skill-level skill-level-N">` — **renders no text**, so nothing an ATS can read; unused by every built-in template |
| `link_anchor` | One `basics.links` entry | Anchor whose visible text is the URL itself |
| `cert_groups` | Certification entries | `(title_key, entries)` per group |

| Global | Signature | Purpose |
|---|---|---|
| `section_title` | `(key, default=None) -> str` | Profile's `section_titles` override, else the locale pack, else the caller's own fallback. Packaged templates pass none — per-template wording is a `templates_meta.suggested_titles` suggestion instead. Reads the context, so a caller supplying neither overrides nor a pack still renders. |

### `templates_meta.py`

`info_for(template_name) -> TemplateInfo | None` — the per-template parse-risk registry
(`columns`, `ats`, `fonts`, `summary`, `caveat`, `suggested_titles`). Deliberately outside the linter:
`check` grades what the user wrote, and whether a layout survives PDF text extraction is
a property of the template. Surfaced by `cvloom list-templates` and warned about by
`build` and `check`. `None` means unrated — a template of the user's own — and is
reported as such rather than assumed safe. A test fails for any packaged `cv/` template
missing an entry.

### `linter.py`

`lint(resolved, rule_ids=None) -> list[LintFinding]`

Rules are stored in a module-level list `RULES: list[LintRule]`. Each `LintRule` carries a `rule_id`, `name`, `description`, `category` (`writing`/`structure`/`ats-parse`), a `check` callable taking `(ResolvedProfile, LintLocale)`, and a `locales` declaration. `lint()` resolves the locale's data once via `linter_locales.pack_for()`, runs the active rules, stamps each finding with its rule's `category`, and collects them. Pass `rule_ids` to run a subset.

`rules_for(code) -> (active, skipped)` is pure and does the dispatch. The registry may hold one `rule_id` twice — one entry per locale — which is how a rule whose *logic* differs between languages is expressed, and how a rule supported in only one language declares itself. A locale-specific implementation wins over the language-neutral one; a `rule_id` with no applicable implementation is skipped, and `check` prints the count and the reason so a clean run never quietly means fewer rules.

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

The stop-word list comes from `linter_locales` keyed by `resolved.locale.code`, so a Spanish JD does not return `de / la / que / el` as its top keywords. The tokenizer matches Unicode letters rather than `[a-z]`: an ASCII-only class split `gestión` into `gesti` and `n`, which shattered the keyword set of every accented language.

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

1. Resolves the root through `_root()`
2. Calls the appropriate domain function
3. Returns a JSON string

`_root()` resolves four sources, narrowest winning: the per-call `project_root` argument,
the `--project-root` flag (parsed in `main()` into module state, since the tools are plain
decorated functions with no server object to hang it on), `CVLOOM_PROJECT_ROOT`, then
`Path.cwd()`. Both server-level mechanisms ship because MCP clients disagree about whether
they can pass `args` or `env`, and the widely-copied `{"command": "cvloom-mcp", "args": []}`
config has no `--directory` equivalent. Getting the root wrong now applies another
project's *settings* and not just its data, which is why `validate_data` and `check_cv`
both report the locale they resolved under.

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

1. Define a function `def check_my_rule(resolved: ResolvedProfile, lex: LintLocale) -> list[LintFinding]`
2. Append a `LintRule(rule_id, name, description, category, check)` to the `RULES` list in `linter.py`
3. Assign a stable `rule_id` in the `wl-NNN` sequence
4. Choose a `category`: `CATEGORY_WRITING`, `CATEGORY_STRUCTURE`, or `CATEGORY_ATS_PARSE`
5. Choose `severity`: `"warning"` or `"suggestion"`
6. Read any lexicon, pattern or threshold off `lex` rather than a module constant, and add
   the field to `LintLocale` plus every locale module. A rule that needs different *logic*
   per language registers once per locale with a `locales=frozenset({...})` declaration
   instead; one that only makes sense in one language registers with just that one, and
   `check` reports it as skipped elsewhere.

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
