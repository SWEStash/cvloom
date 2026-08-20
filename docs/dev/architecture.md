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
├── filters.py          # Jinja2 filters (md, date_range, duration, cert_groups, …) + section_title global
├── dates.py            # The one CV-date parser: parse_partial, granularity, span_months
├── links.py            # Profile-link vocabulary: network_of, link_username, normalize_url
├── select.py           # Per-section content selection: apply_selection()
├── linter.py           # Writing lint: 25 categorized rules, LintFinding, lint()
├── linter_locales/     # Per-locale lexicons, patterns, thresholds (en, es)
├── trim.py             # Per-section word count analysis
├── diff.py             # Profile comparison
├── match.py            # Keyword gap analysis from job descriptions
├── extract.py          # Read a built PDF's text layer back out; five engines
├── fidelity.py         # Recall of the CV's own words in that text layer
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
- Missing-file notices (a section's YAML absent, `private/contact.yaml` absent) are **appended to the `warnings` list the caller passes**, not printed. `load_data` performs no terminal I/O, which is what lets `builder.resolve()` stay pure — the notices ride out on `ResolvedProfile.warnings` alongside the select, overlay and duration warnings, and `cli._resolve` renders them. A caller that passes no list drops them.

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

`cvloom.yaml` at the project root holds settings owned by the project as a whole rather than by one build profile. A profile says how one output variant renders; this says what the project *is*: `locale` (the language it operates in), `ai` (which backend analyses it — never `api_key`, since the file is committed), and `pdf.variant` (a PDF conformance level to declare, absent by default).

`load_project_config(root)` returns a frozen `ProjectConfig`. An absent file is not an error — it yields defaults identical to cvloom's behaviour before the file existed. Anything present is validated against `schemas/project-config.json`, which sets `additionalProperties: false` so a typo'd key fails with the file path rather than being ignored. Failures raise `ConfigError`, which `builder` translates into `ResolveError` so callers keep catching one pipeline error type.

### `locale.py` — locale packs

A pack under `cvloom/locales/<code>.yaml` supplies the document-facing defaults cvloom would otherwise hardcode in English: `html_lang`, `section_titles`, `ongoing`, `duration`, `placeholder_contact`, `cover_letter`, `months`, `date_format`. Packs govern the **rendered document only** — CLI and terminal output stay in English by design.

`en` is an ordinary pack loaded through the same path as any other, with no privileged branch, so every build exercises the mechanism and a resolution bug surfaces in the default build rather than waiting for the first non-English user. It is also the fallback: a key missing from another pack resolves to `en`'s value and reports a warning onto `ResolvedProfile.warnings`; a key missing from `en` is an error, since nothing is left to fall back to. `tests/test_locale.py` asserts `en.yaml` covers every key the code looks up, derived from `LocalePack`'s fields and `sections.TITLE_KEYS` rather than a hand-written list.

`Ongoing` binds `render` and `accepts` together because the field is bidirectional — `render` is written into the document by `filters.date_range`, `accepts` is parsed back out by the chronology lint rule and the JSON Resume export. A pack supplying only one would silently stop the other side from recognising its own output. `Duration` is required whole for the same class of reason: the count picks between `year`/`years` and `month`/`months`, so a pack with one of each pair would write `1 years`.

`load_pack` is cached and its mappings are read-only: every build shares one instance.

`ResolvedProfile.locale` carries the resolved pack so renderer, linter, export and match all read it from one place. `resolve_project()` and `build_project()` are the two entry points that know the project root, so both resolve the locale; `resolve()` and `build()` take an optional pack and stay pure.

The pack governs the **document**. The **linter and keyword analysis** are governed
separately, by `cvloom/linter_locales/` — Python, not the user-editable YAML, because
`section_titles` is content the user owns while a weak-verb list is the tool's editorial
judgement, and putting the latter in a file users edit would create a linter-configuration
API before the configuration model has been designed. The two are keyed by the same locale
code and resolved independently: a document pack with no linter data behind it falls back to
English heuristics rather than failing, and says so through the skipped-rule count.

Consumers, as of 6.8: `renderer` installs the pack as a Jinja global, so `base.html.j2` reads `locale.html_lang` and `filters.section_title` / `filters.date_range` / `filters.duration` read it off the context; `loader` uses `placeholder_contact`; `linter` matches `ongoing.accepts` for chronology, date-format and tense rules and renders `ongoing.render` in a fix hint; `export._heading` uses `section_titles` so the Markdown, text and DOCX exports head sections in the same words as the PDF; `filters.cover_letter_text` resolves `cover_letter` under a `job_context` override, and `builder` writes `today` through `LocalePack.format_date`, since `strftime("%B")` reads the C locale rather than the project's, and recomputes `dates.span_months` against `ongoing` to warn about work entries whose requested duration it could not compute (a Jinja filter has no route to `ResolvedProfile.warnings`). The JSON Resume export needs nothing: it drops any non-ISO date, so an open-ended one becomes an omitted `endDate` whatever word wrote it.

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
| `duration` | `start, end` | The tenure the range covers, in the pack's `duration` words: `(2 years 3 months)`. Inclusive months, capped at the current one. Empty string when the dates are unreadable, so a template can test it |
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

The stop-word list comes from `linter_locales` keyed by `resolved.locale.code`, so a Spanish JD does not return `de / la / que / el` as its top keywords. The tokenizer matches Unicode letters rather than `[a-z]`: an ASCII-only class split `gestión` into `gesti` and `n`, which shattered the keyword set of every accented language. It is exposed as `match.tokenize` because `fidelity` has to split a CV the same way — two tokenizers would disagree about exactly the accented words that matter.

### `fidelity.py`

`recall(resolved, pdf_path) -> RecallReport`

How much of a CV's own text survives into the built PDF's text layer, behind `build --extract-text`. Source tokens come from `sections.iter_visible_text` — including the contact block and profile link labels, the most extraction-fragile text on the page — and are split by `match.tokenize`; each installed engine's extraction is then searched for them. Tokens shorter than four characters must match on a word boundary, because `ai` occurs inside `domain`; longer ones match as substrings, so a word welded to its neighbour still counts as found.

Attribution needs corroboration. A token no engine found is the template's omission rather than an extraction failure, but that inference only holds with **two or more** engines: a lone engine's misses are indistinguishable from words never drawn, and blaming the template for them would drop exactly those tokens from the denominator and score the engine 100% for losing them. Below two engines `RecallReport.attribution_available` is False and nothing is attributed.

The report separates two failures rather than summing them, because they have different fixes. A token **no engine found** is attributed to the template — it was never painted on the page, and no extractor could have helped — and is excluded from every engine's denominator. What remains is per-engine, where disagreement between engines is the signal that the text layer is ambiguous. Told apart by engine agreement, which works precisely because the five engines read the document by different means: all five missing the same word is not five failures.

Scored the naive way, `cv/sidebar-compact` reported 188/198 under all five engines — it renders no education detail, so ten words were never there to find.

Never averaged into a single figure across engines. See [ATS-readiness](../reference/ats-readiness.md) for why cvloom reports no composite score.

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
ai/prompts.py    ← shared: system prompts, context block helpers, prompt assembly
ai/analysis.py   ← shared: the <analysis> block — lint/trim/template facts, budgeted
ai/models.py     ← shared: result dataclasses

ai/analyzer.py   ← review():  build prompt → call API → parse JSON response → ReviewResult
ai/cover.py      ← generate_cover(): same pattern → CoverResult
ai/suggest.py    ← suggest():  same pattern → SuggestResult
ai/align.py      ← align():    runs match() first, passes keyword analysis as context → AlignResult
```

`cv_to_text(data, show_sections, locale=None)` in `provider.py` serializes the resolved CV to plain text for LLM input. It respects section visibility, and walks `sections.DEFAULT_SECTION_ORDER` rather than a list of its own — a hand-written list here went stale the moment a section was added, leaving `certifications`, `publications`, `awards` and `languages` invisible to every AI command even when the profile showed them. `skills` and `basics` stay bespoke, for the same reason they sit outside the registry. The optional `locale` pack supplies the section headings, so the model reads the CV under the same words the rendered document uses.

Every prompt is assembled by `prompts.assemble(*parts)` in one canonical order — `<locale>`, then instruction and schema, then `<analysis>`, `<keyword_analysis>`, `<cv>`, and the job-specific blocks, closing with `CLOSING`. Stable content leads so a caching provider can reuse the prefix; `tests/test_ai_prompt_order.py` is the only thing holding that order, since no type expresses it. `prompts.locale_context_block` states the language every human-readable response field must use, and exempts JSON keys and enum values from it — a model told only "answer in Spanish" returns `"type": "viñeta"` and breaks the CLI's own colour map.

`prompts.GROUNDING` is appended to both `SYSTEM_ANALYSIS` and `SYSTEM_CREATIVE`: every claim must trace to a fact in `<cv>`, and a missing metric is written as an `[add metric: …]` marker rather than invented. `tests/test_ai_grounding.py` enforces it with a reference-free numeric-token check, and asserts the contract reaches all four orchestrators.

`resolve_ai_config(root)` in `provider.py` is the single place the two config layers meet: `CVLOOM_AI_*` beats `cvloom.yaml`'s `ai:` block, which beats the built-in default. It returns an `AIConfig` carrying `base_url_source` / `model_source` alongside the values, because with two layers "which model is it actually using" needs an answer that `cvloom ai config` can print. `is_configured`, `get_client`, `get_model` and `get_config` all route through it and all take `root` **optionally** — the Python API is part of the public contract, so a required parameter would be a breaking change. A malformed `cvloom.yaml` degrades to the environment layer rather than raising: `ai config` is the command a user runs to understand a problem, and failing it on an unrelated typo hides the output that explains it.

The credential is guarded in three places, cheapest first: `schemas/project-config.json` forbids `ai.api_key` structurally, `config.load_project_config` special-cases the key for a message naming the file and its committed status, and `cvloom/hooks/pre-commit` matches `api_key`-shaped and `sk-`-shaped strings on added lines.

`ai/analysis.py` generalizes what `align` did first. All four commands now feed the LLM what cvloom already computed — `linter.lint`, `trim.analyze`, `templates_meta.info_for`, `linter.rules_for` — inside an `<analysis>` block, so the model stops re-deriving what a rule answers exactly and stops missing what the CV text cannot show. `align` and `cover` additionally call `match.analyze_match` for the `<keyword_analysis>` block, which stays separate: its provenance is the job description, not the CV.

The block is budgeted as a fraction of `cv_text` and renders through a downward walk — grouped by `(rule_id, fix_hint)`, then one line per finding, then counts — taking the first that fits. This is a safety mechanism, not only a quality one: Ollama drops the *front* of an over-long prompt and `GROUNDING` lives in the system message, so an oversized block can push the anti-fabrication contract out of the request entirely. Characters rather than tokens, because block and CV share a language and the tokenizer bias cancels between numerator and denominator.

Scope decides what each command receives, keyed on what its consumer can act on rather than on the command name. `review` and `suggest` get every finding; `align` gets counts and an aggregate writing signal; `cover` gets **no defect findings at all** — at temperature 0.7, "No quantified outcome in this entry" is an invitation to invent the number, so it receives the inverse instead: which entries already carry a metric.

One rule sends more than its findings. When `wl-004` survives into the rendered block, `_weak_opener_constraint` appends the locale's whole `weak_openers` set — otherwise the model knows only that *this* opener is weak, rewrites it into another one on the list, and the finding fires again on the bullet it just fixed. It is appended after the walk and sits outside the budget, like the header: one line, and not detail to shed. Gating on the rendered text rather than on `findings` keeps the constraint from appearing without the finding that motivates it when shedding drops that group. `strong_verb_examples` is deliberately never sent alongside it — sharing the rule leaves the vocabulary open, while supplying five approved verbs collapses every generated bullet onto the same ones, which is also why `wl-004`'s own `fix_hint` stopped naming them.

What the block had to shed reaches the user through `context_notes` on each result dataclass, not `ResolvedProfile.warnings` — `cli._resolve` emits those before the AI call runs.

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

AI tools add an extra guard, and it runs *after* the root is resolved — a project
can pin its own backend in `cvloom.yaml`, so asking before the root is known reads
another project's settings:
```python
root = _root(project_root)
if not is_configured(root):
    return json.dumps({"error": "AI provider not configured. …", "project_root": str(root)})
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
uv run pytest -m evals -s             # opt in to the live-model suite (below)
```

### The evaluation suite

`tests/test_ai_evals.py` sends real prompts to a real model. Everything else under
`tests/test_ai_*.py` feeds an orchestrator a hand-written JSON string and checks it
parses — correct, and worth keeping, but it means no prompt change can be shown to
have helped or hurt. That gap is what this closes.

It is gated twice. `addopts = "-m 'not evals'"` deselects it from every ordinary
run, and the tests skip without `CVLOOM_AI_BASE_URL` even when selected — so a
contributor who happens to export a backend does not discover the suite by
watching `uv run pytest` make dozens of model calls. A command-line `-m evals`
replaces the `addopts` value, since the last `-m` wins.

Three modules, split by what needs a backend:

- `tests/ai_corpus.py` — the CVs, including the ones that go wrong. `examples/`
  and `examples-es/` resolved through the real project path, plus synthetic cases
  built to fail one way each: no metrics anywhere, passive throughout, four pages,
  an empty `work`, a one-line CV, a job description that is a privacy policy. The
  deliberately-bad Spanish CV lives here rather than in `examples-es/`, which
  produces exactly one lint finding — enough to prove locale handling, not enough
  to exercise the analysis block, and growing it would make the demo worse for the
  people it is a demo for.
- `tests/ai_rubrics.py` — pure functions returning `None` on pass and a reason on
  failure, so a red run names the defect. Reference-free by construction: there is
  no labelled corpus of good CV feedback, so each check asks whether the output is
  self-consistent with its own inputs. Weaker than "is this good advice", and
  answerable without ground truth.
- `tests/test_ai_rubrics.py` — covers the rubrics offline, with no backend. Without
  it the checks deciding whether a model passed would be the least-tested code in
  the repo, and a rubric that always passes is worse than none: it reports a clean
  run.

**Gates versus measurements.** Language, groundedness, citation, unusable-input
handling and cover-letter shape are gates — contract violations that make a model
unusable for that feature. Restatement is measured and printed, never asserted:
the prompt asks the model not to repeat findings the user has already seen from
`cvloom check`, and small models ignore that reliably enough that gating on it
would paint every pre-release run red while saying nothing about the prompt.

**A red run is an answer, not a broken suite.** This qualifies a *model*; it is
not a CI gate, which is why it is opt-in and deselected by default. The baseline
is recorded in [ai-features.md](../user/ai-features.md#why-the-recommendation-starts-at-27b):
`qwen2.5:3b-instruct` passes 8 of 16, and the split is the useful part — every
check about the *shape* of the answer passes, every check about *what to say and
what to omit* fails. The anti-fabrication instructions are the first ones a small
model drops.

Every gate echoes the graded text on failure. That is not a convenience: a run
takes 25–40 minutes against a local model, so a failure that cannot be diagnosed
from its own output costs another full run. The first version omitted it and
immediately produced a language-mismatch report nobody could adjudicate.

Two of the failures in that first run were bugs in the suite rather than in the
model, both the same mistake — asserting an expectation of `AnalysisBlock` that
contradicted its documented behaviour (narrow scopes never render instances; the
per-rule instance cap is normal rendering and emits no note). A third graded
`review` output against the CV alone when the model had also been handed the
analysis block, so "trim to under 20 words" was reported as an invented `20`.
When this suite goes red, check the rubric against the contract before believing
it about the model.

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

Linting: `uv run ruff check cvloom tests scripts`. Line length 100, target Python 3.11, rules E/F/I/UP.
