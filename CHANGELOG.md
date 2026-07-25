# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Fixed
- **JSON Resume export now actually conforms to JSON Resume.** It never had. Validated against the official schema, the shipped demo project produced two violations: `basics.email: ""` (a `--public` build strips email, and the empty string fails the schema's `email` format) and `endDate: "Present"` (JSON Resume has no such sentinel — a current role omits `endDate`). Empty fields are now omitted rather than exported as `""`, and dates that aren't ISO 8601 are omitted rather than emitted invalid. A new suite (`tests/test_export_jsonresume_conformance.py`) validates every export — full, public, sparse, and all three demo profiles — against a vendored copy of the official schema, so this is a checked promise rather than an aspiration.
- **`basics.public_links` are now exported.** They were dropped entirely; they map to JSON Resume's `basics.profiles` with the link label standing in for `network`, skipping any URL already covered by the linkedin/github entries. Import already read them back, so the round-trip now closes.
- **An `export` → `import` round-trip no longer silently strips your tags.** `tags` survived only for projects (which map to the spec's `keywords`); on work, education, publications, and certifications they were dropped outright — meaning a round-trip returned your content but quietly destroyed the tag taxonomy that every profile's `include_tags` filtering depends on. Fields JSON Resume has no home for are now carried under an `x-cvloom-*` namespace the schema permits and other tools ignore: `x-cvloom-tags`, plus certifications' `expiry_date`/`identifier` and per-item skill `level` (previously rendered by `skill_level_bar` but lost on export). Education bullets now map to the spec's `courses` field instead of a non-standard `highlights` key, and import accepts either.

### Changed (internal)
- **Section registry (`sections.SECTIONS`), no behavior change.** Adding a section previously meant editing ~16 sites across 13 files — `_ENTRY_SCHEMAS`, file loading, tag filtering, `validate_all`, three `sections.py` constants, `section_defaults`, `default_order`, `_section_summary`, export headings, and more — where forgetting one failed *silently*. The entry-list sections are now frozen `Section` records carrying `schema`, `label_key`, `heading`, `summary_label`, `from_directory`, `warn_if_missing`, and `strict_tags`; loader, schema validation, builder, CLI and export all derive from them. `skills` and `basics` stay out deliberately — their shapes genuinely differ, and forcing them in would buy uniformity at the price of exceptions everywhere. `tests/test_sections_registry.py` guards what the registry cannot derive: `profile.json`'s `sections`/`section_order` enum, and each section's entry schema existing.
- `export.py`'s five near-identical `_map_*` functions — each a hand-rolled block of conditional field assignments — collapsed into one table-driven `_map_entry` over `_Field(src, dest, kind)` tuples. Adding the namespaced extensions above was then a table edit rather than a sixth copy of the same block. `tests/conftest.py`'s `make_resolved` factory had drifted behind the data model; it now derives its section defaults from the registry itself, so it cannot drift again.

### Added
- **`awards` and `languages` sections.** Two more optional data files — `data/awards.yaml` (`title` required, plus `awarder`, `date`, `summary`, `tags`) and `data/languages.yaml` (`language` required, plus `fluency`, `tags`). Both map field-for-field to JSON Resume's native `awards` and `languages` arrays. Languages render as a single inline run (`Spanish (Native speaker) · English (C1)`) rather than a stack of entry blocks, since two short fields per language don't warrant the vertical space. These were the first sections added since the registry landed: adding each to the pipeline was one `sections.SECTIONS` entry — loading, tag filtering, validation, visibility, ordering and the CLI summary all followed automatically.
- **First-class `certifications` section.** A new optional `data/certifications.yaml` for certifications, licences, and short courses — `name` (required) plus `issuer`, `date`, `expiry_date`, `identifier`, `url`, `tags`. All six CV templates render it **compactly** — a title row plus one meta line, with no bullet list — rather than giving it the full entry treatment education gets. That is the point: a CV with 2 degrees and 21 vendor certs previously rendered all 23 with equal weight and no way to differentiate them. Exports to JSON Resume's native `certificates` array (see the export fix above for how `expiry_date` and `identifier` are carried).
- **`tags` on education entries**, with tag filtering in the loader. Education was the only array section that could not be tag-filtered. The user guide already documented `tags` as an education field, so this was a documented-but-unimplemented feature: adding `tags:` to an education entry previously failed schema validation with `Additional properties are not allowed`. Filtering follows `work`'s lenient semantics — an untagged entry is always included — rather than `projects`' strict semantics, where `tags` is a required field. The education `grade` field is now documented too.
- **Lint rule `wl-018` (education-size, structure):** warns when the education section exceeds 6 entries and points at `certifications.yaml`.
- **First-class `publications` section.** A new optional `data/publications.yaml` holds papers, articles, and talks — `name` (required) plus `publisher`, `release_date`, `identifier` (ISBN/DOI/arXiv), `url`, `summary`, and `tags`. All six CV templates render it; `cv/academic` places it directly after education. Profiles control it like any other section (`sections: { publications: false }`, `section_order`, `include_tags` — with `work`'s forgiving semantics, where untagged entries are always included). Export maps it to JSON Resume's native `publications` array (`identifier` is folded into `summary`, since JSON Resume has no field for it) and `import` maps it back; Markdown and DOCX export gained the section too. Omitting the file entirely is the normal case and produces no warning.
- `docs/user/user-guide.md` documented the section, and its **stale claim that `cv/academic` already "supports research and publications sections"** — which was never true; the template had the same four sections as every other one — is corrected to describe what that template actually does.

### Changed
- **The pre-commit PII hook no longer cries wolf.** It scanned whole staged files, so any commit touching a file that has always contained a placeholder (`your.email@example.com` in `loader.py`, `+1 (555) 000-0000` in the test fixtures) was blocked — training the reflex of passing `--no-verify`, which is exactly how real PII eventually slips through. The hook now scans only the **added lines** of a diff, and allows values reserved for documentation: RFC 2606 / 6761 domains (`example.com`, `.example`, `.test`, `.invalid`, `.localhost`) and the fictional phone ranges (NANP `555`, UK Ofcom `7700 900xxx`). It also prints the offending value instead of just the filename, so the warning can be judged without re-grepping. Existing projects pick this up via `cvloom sync`.

### Changed (internal / tests)
- Slop-audit cleanup, phase 5 (SLOP-024, no behavior change): decomposed the `cli.py` God-file. The project-scaffolding logic (`init`/`sync` file operations and the managed-file registry) moved into a new `cvloom.scaffold` package, and the ~100 lines of embedded sample-YAML string constants became real files under `cvloom/scaffold/samples/`, loaded at runtime. `cli.py` dropped from ~1,190 to ~940 lines and no longer mixes command definitions with scaffold internals and inline data. Verified: a fresh `cvloom init` scaffolds and builds identically.
- Slop-audit cleanup, phase 4: added `tests/conftest.py` with shared `make_resolved` and `make_project` factories. The six per-file `_make_resolved` copies now delegate to one `ResolvedProfile` builder (defaults no longer drift), and the duplicated on-disk project scaffolds for the builder and MCP suites are single-sourced through `make_project`. (Bespoke fixtures whose content is load-bearing for their own assertions — loader, match, CLI-list — keep their tailored data.)

### Fixed
- **Omitting an optional field no longer crashes the build.** Templates render under Jinja2's `StrictUndefined`, where reading a dict key that is simply *absent* raises `UndefinedError` rather than evaluating falsy — so `{% if edu.field %}` blew up on any `work`/`education`/`project` entry that left out a field the schema and docs both call optional (`field`, `location`, `highlights`, `url`, `start_date`, `description`, `tags`, …). Every built-in template was affected, and the only workaround was to write out `field: ""`, `highlights: []` by hand. `resolve()` now fills each entry's schema-declared optional keys with typed empties (`""`/`[]`) via the new `schema.entry_defaults()`, so "optional" means optional for current and future templates alike. The same fix covers partially-specified `job_context` in cover-letter profiles. `contact` is deliberately excluded — its templates guard with `is defined` so that `--public` redaction keeps email/phone invisible rather than blank — and the three templates that instead tested contact keys for truthiness (`cover-letter/brief`, `cover-letter/standard`, `project-summary/card`, which crashed on any public build) now check presence first. Regression test renders all 9 templates against a project carrying only schema-required fields.
- MCP tools now surface **real validation errors**. Previously every pipeline failure collapsed to the unactionable string `"exit code 1"`; the tools now return `{"error": "resolve failed", "details": [...]}` with the actual schema/profile messages an agent needs. The four AI tools also resolve inside their `try` block (a resolve failure no longer escapes uncaught) and catch specific error types instead of a blanket `except Exception`.

### Changed
- Internal slop-audit cleanup, phase 3: made the pipeline's `resolve()` a **pure function** as documented — it no longer prints Rich output or raises `SystemExit` from the library layer. It raises a typed `builder.ResolveError(errors)` instead; the CLI catches it, renders the errors, and exits, while the MCP server returns them as structured `details`. `schema.validate_all` and `overlays` lost their terminal I/O too (no more module-level `Console`), overlay non-match warnings are reported once (via `validate_overlays`, returned on `ResolvedProfile.warnings`) instead of twice, and the overlay exclude path drops its `None`-sentinel `type: ignore`. Behavior change is confined to the error/warning path; new tests assert `resolve()` writes nothing to stderr and that MCP errors carry real `details`.
- Internal slop-audit cleanup, phase 2 (no behavior change): killed the two biggest sources of structural duplication. Added `builder.resolve_project`/`build_project` wrappers over the fixed `data/`+`private/`+`profiles/` project layout and migrated all 23 call sites in the CLI and MCP server, so the 5-argument wiring block exists once. Added `cvloom/projects.py` (a shared profile/project-listing data layer behind both the CLI table and the MCP JSON) and `cvloom/sections.py` (single home for the CV data walk: `highlight_text`, `skill_name`, `entry_label`, `iter_entry_text`/`count_words`, and one NFKD-normalizing `slugify`). The `~18` copies of the `str | {text}` highlight guard, the three hand-copied word-count walks, the section→label maps, and the two divergent slugifiers now resolve to those shared helpers
- Internal slop-audit cleanup, phase 1 (no behavior change): removed a meaningless, never-surfaced `frequency_cv` field from `match`; factored the four AI orchestrators' identical LLM call-and-parse block into a shared `ai.provider.complete_json` helper; unified the four AI MCP tool responses on `dataclasses.asdict`; corrected `filters.register_filters` to a real `jinja2.Environment` type (dropping three `type: ignore`s); tightened several tests (real assertions for the unmatched-overlay warning, the `init --force` overwrite, and the `_suggest_section` "work" branch) and removed a dead fixture, a subsumed test, and dead code (a no-op contact `pop`, unused `_init_*` `force` params, a stale renderer comment). The `dev` extra now pulls `cvloom[docx]` instead of re-pinning `python-docx`

---

## [0.6.0] — 2026-07-18

First public release on PyPI. Install with `pip install cvloom` or `uv tool install cvloom`.
This is a pre-1.0 release: the CV/profile schema and CLI are still free to change on MINOR
version bumps. Note the **breaking changes** below if migrating from a pre-release checkout.

### Added
- `SECURITY.md` — private vulnerability disclosure process (GitHub Security Advisories) and a note that any real-contact-data leak (tracked file, `--public` build, Pages artifact, or MCP response) is treated as a security issue
- `cvloom sync` — refresh cvloom-managed scaffold files (the pre-commit hook and the Pages publish workflow) to the installed package's versions after `uv tool upgrade cvloom`. Reports `up to date` / `out of date` / `missing` by default and writes nothing; `--force` applies. `init` and `sync` now share one managed-file registry. New guide: [keeping your instance updated](docs/user/keeping-updated.md)
- Reusable **GitHub Pages publish workflow**: `cvloom init` now scaffolds `.github/workflows/publish-cv.yml`, which builds your CV in public mode (email/phone stripped) and deploys to Pages — gated behind a `DEPLOY_PAGES=true` repo variable so nothing publishes until you opt in. An optional `CONTACT_YAML` secret adds your real name/links. The tool's own repo uses the same pattern to publish `examples/`
- `cvloom import --format json-resume <file>` — import a [JSON Resume](https://jsonresume.org/) document into cvloom's layout (the inverse of `export`), with a PII-aware split that routes contact details to `private/contact.yaml` and everything else to `data/`. Supports `--dry-run` and `--force`; imported data is schema-validated before any file is written
- `docs/reference/ats-readiness.md` — explains the three honest, measurable axes of ATS-readiness (writing quality, JD keyword coverage, parseability) and why a single "ATS score 0–100" is not honestly achievable
- Lint findings now carry a `category` (`writing` / `structure` / `ats-parse`), surfaced in `cvloom check`, `build --check`, and the `check_cv` MCP tool
- MCP agent-safety hardening: documented and tested guarantees that mutating tools reject malformed writes with a structured `{"error", "details"}` (no partial write), and that read/analysis tools never surface contact email/phone. The `export_json_resume` MCP tool now defaults to `public=true` (PII fenced); pass `public=false` to opt into real contact details
- MIT `LICENSE` file (the license was previously declared but not shipped)
- Fake-client tests for all four AI orchestrators (`review`, `generate_cover`, `suggest`, `align`) and all four AI MCP tools, including malformed-response cases — AI orchestration modules now at 100% coverage
- CI quality gates: `ruff check`, `ruff format --check`, and strict `mypy` now run in the test job, across Python 3.11, 3.12, and 3.13

### Changed
- **Documentation sweep** for gaps/drift: refreshed a stale `CLAUDE.md` (pre-rename `simple_cv` paths, "ATS linter with 5 rules", a non-existent `--private` flag, missing `import`/`sync`); normalized end-user docs to `cvloom` (from `uv run cvloom`); replaced the old "re-run `init` to refresh the hook" upgrade step with `cvloom sync`. All internal doc links verified
- `LICENSE` copyright holder set to **SWEStash**
- **README repositioned** to lead with the differentiators — declarative per-job overlays (one dataset → N tailored, diffable CVs), the agent-safe MCP data layer, and PII compartmentalisation — with the AI commands demoted to a supporting section
- **Repo restructure:** the sample CV data moved from root `data/`/`profiles/` into [`examples/`](examples/); the repository root is now unambiguously the tool. The README hero commands are now real and runnable against `examples/` (added a sample `examples/stripe-infra-jd.txt` for `match`). Contributors and the CI Pages demo build from `examples/` (`cd examples && cvloom build`); end users scaffold their own project with `cvloom init`. The removed stale `simple_cv/` leftover directory is gone
- **Breaking:** lint rule IDs renamed from `ats-NNN` to `wl-NNN` (writing-lint), reflecting that most rules measure writing quality, not ATS parsing. Update any scripts or overlays that filter by rule ID
- **Breaking:** dropped the single "ATS score 0–100" from `build --check`; it now prints a per-axis findings breakdown. `--strict N` now fails when there are *more than N findings* (a lint budget) instead of when a score is below N
- `__version__` is now read from package metadata (`pyproject.toml` is the single source of truth)
- Codebase formatted with `ruff format`; formatting is now enforced in CI
- Root `CONTRIBUTING.md` is the canonical contributing guide; `docs/dev/contributing.md` now points to it

### Fixed
- All outstanding `ruff` and `mypy` errors on `main`
- README MCP tool table now lists all 16 tools (`trim_report` and `diff_profiles` were missing)

---

## [0.5.0] — 2026-04-29

### Added
- `cvloom ai align` — qualitative AI analysis of CV-to-JD alignment: narrative summary, repositioning actions, tone gaps, and strengths; combines rules-based keyword analysis with AI qualitative insight
- `ai_align_to_jd` MCP tool for LLM-driven CV-to-JD alignment analysis
- `cvloom ai suggest` — AI-generated improvement ideas (new bullets, skill additions, rewordings) for a target role; `--role` option or falls back to `job_context.role` from the profile
- `ai_suggest_improvements` MCP tool for LLM-driven CV improvement suggestions
- `cvloom ai cover` — AI-generated cover letter from CV + job description file (`--jd FILE`), with optional `--output FILE` to write to disk
- `ai_generate_cover` MCP tool for LLM-driven cover letter generation
- `cvloom ai review` — AI-powered section scoring (1–10) with strengths, weaknesses, and improvement suggestions per section plus top-3 priorities across the whole CV
- `ai_review_cv` MCP tool for LLM-driven CV scoring
- `docs/ai-features.md` — installation, configuration, and backend quickstart guide for AI features (Ollama, LiteLLM, OpenAI)

---

## [0.4.0] — 2026-04-25

### Added
- Linter rule ats-016: Readability — flags highlights with Flesch-Kincaid grade level >12 (too complex) or <6 (too simple); suggestion severity.
- Linter rule ats-017: Tech mentions in work — flags work entries whose highlights contain no skill item name; suggestion severity.
- `MatchReport.reorder_hints`: when `match --jd` is used, suggests moving the most JD-relevant work entry to the top; shown in `cvloom match` output.
- Linter rule ats-006: Bullet count per role — warns if a work entry has fewer than 3 or more than 8 highlights.
- Linter rule ats-007: First-person pronouns — flags `I/my/me/mine/myself` in highlights and summary.
- Linter rule ats-008: Vague buzzwords — detects terms like "motivated", "proactive", "passionate", etc.
- Linter rule ats-009: Skill count — warns if total skills listed is below 8 or above 25.
- Linter rule ats-010: Profile links presence — warns if no LinkedIn or GitHub link is found in contact or public_links.
- Linter rule ats-011: Page count estimate — warns if estimated page count exceeds 2 (skipped for academic templates).
- Linter rule ats-012: Date format consistency — flags mixed YYYY-MM / YYYY within a section.
- Linter rule ats-013: Tense consistency — past tense for past roles, present for current.
- Linter rule ats-014: Summary length — warns if summary is <20 or >80 words.
- Linter rule ats-015: Action→result — flags highlights with a metric but no result framing (suggestion severity).
- `MatchReport.suggestions`: for each gap keyword, recommends the section to add it to; shown in `cvloom match` output.
- Smart PDF filename: defaults to `FirstName_LastName_Resume.pdf` derived from `contact.name`; customisable via `pdf_filename_format` in profile YAML.
- PDF metadata: `<meta name="author">` added to base template; `<title>` updated to `{name} — Resume`.
- Skill-level bar CSS: `.skill-level-1` through `.skill-level-4` styles added to `base.html.j2` (the `skill_level_bar` filter now renders visually).
- `cvloom build --check`: runs ATS linter post-build and prints a 0–100 score.
- `cvloom build --strict N`: exits non-zero if ATS score is below N (implies `--check`).
- Grayscale print safety: `sidebar-compact` forces light sidebar background + dark text in `@media print`; `executive-dark` forces dark heading colours for B&W printing.
- `cvloom export --format markdown`: exports CV as a Markdown file (`dist/<profile>.resume.md`).
- `cvloom export --format linkedin`: exports CV as LinkedIn-pasteable plain text (`dist/<profile>.linkedin.txt`); warns when About section exceeds LinkedIn's 2600-character limit.
- `cvloom export --format docx`: exports CV as a `.docx` file via `python-docx` (optional dependency: `uv pip install python-docx` or `uv sync --extra docx`).

### Changed
- **Typography (Phase 4):** Added `{% block fonts %}` to `base.html.j2`; `timeline-clean`, `modern-single`, `executive-dark`, and `sidebar-compact` now load Google Fonts (Inter or Roboto) via HTTPS `<link>` tags. `ats-single` and `academic` remain system-fonts-only by design.
- `h2` base font size increased `11pt` → `12pt` for improved section heading legibility.
- Body `line-height` tightened `1.45` → `1.35` to improve print density while preserving readability.
- `modern-single`, `executive-dark`, and `sidebar-compact` font stacks updated to lead with their respective web font (Inter / Roboto).

---

## [0.3.0] — Phase 3 — 2026-03-26

### Added
- `cvloom match --jd <file> [--profile]` — keyword gap analysis comparing CV
  content against a plain-text job description. Reports coverage percentage,
  matched/missing keywords by section, and top JD keywords.
- MCP server parity: 4 new tools (`check_cv`, `trim_report`, `diff_profiles`,
  `match_jd`) bringing the total from 8 to 12 tools.
- `validate_overlays()` now checks for: unmatched overlay entries, nonexistent
  highlight IDs in pick/exclude/replace, unknown match field names, and
  non-existent skill categories.
- `renderer.template_exists()` and `renderer.list_templates()` helper functions.
- Template existence pre-check in `builder.resolve()` with available templates
  listed in the error message.
- `cvloom-template-*` naming convention for third-party templates.

### Fixed
- MCP `upsert_project` slug generation now handles accents, special characters,
  consecutive spaces, and empty names via `_slugify()`.
- ATS linter passive voice rule (ats-001) no longer flags adjectives ending in
  -nt, -lt, etc. (e.g. "is present", "was efficient").
- Overlay warnings now surface during `builder.resolve()` instead of being
  silently discarded.

---

## [0.2.0] — Phase 2 — 2026-03-24

### Added
- `cvloom check [--profile]` — ATS linter with 5 built-in rules: passive
  voice, missing quantification, noise skills, weak action verbs, highlight
  length. Per-bullet feedback with fix hints.
- `cvloom trim [--profile] [--target-pages]` — per-section word breakdown
  with cut recommendations to reach target page count.
- `cvloom diff <profile-a> <profile-b>` — compare two profiles: sections,
  entries, word counts, and highlight counts side by side.
- `cvloom export --format json-resume [--profile]` — export CV data to
  JSON Resume schema for interoperability with the JSON Resume ecosystem.
- `cvloom-mcp` — MCP server exposing 8 tools (list_profiles, list_projects,
  get_section, build_cv, create_profile, upsert_project, validate_data,
  export_json_resume) for LLM-accessible CV management. Data stays local.
- `templates/cover-letter/brief.html.j2` — compact cover letter template.
- `templates/project-summary/card.html.j2` — single-page project summary card.
- `builder.resolve()` — pure function returning `ResolvedProfile` for
  programmatic access to the build pipeline without rendering or file I/O.
- `builder.build()` now returns `BuildResult` with structured data (words,
  pages, section word counts, file paths).
- Per-section word counts in build output via `_word_count_by_section()`.
- `schema.validate_all()` accepts `raise_on_error=False` for programmatic use.
- Profile YAML is now validated against the profile schema during build.

### Fixed
- `_estimate_pages()` now strips `<style>` blocks before word counting,
  preventing CSS tokens from inflating word counts.
- `pytest-cov` moved from runtime to dev dependencies.
- Removed dead `_apply_include_entries()` placeholder in overlays.py.

---

## [0.1.0] — Phase 0 + Phase 1 — 2026-03-20

### Added
- `cvloom list-projects [--tag TAG]` — list projects from `data/projects/`,
  optionally filtered by one or more tags.
- `cvloom list-profiles` — tabular listing of all profiles in `profiles/`
  with their template, output filename, tag filters, and job context.
- `templates/cover-letter/standard.html.j2` — professional cover letter
  template driven by `job_context` in the build profile. Renders date, sender,
  recipient, salutation, and body from profile data.
- `templates/cv/academic.html.j2` — academic CV template: education-first
  layout, serif body font, positions/research/projects sections.
- Build output now shows per-section item counts alongside word count and page
  estimate (e.g. `450 words · ~1 page  [work×3  edu×1  skills×4  projects×2]`).
- `today` variable available in all templates (formatted as `Month DD, YYYY`).
- `profiles/cover-letter.yaml` scaffold created by `cvloom init`.
- Profile overlays: per-job data patches with match-and-patch, highlight
  pick/exclude/replace for tailoring CV content per application.
- `section_order` profile key for reordering template sections.
- `include_entries` for force-including tag-filtered entries back into a build.

---

### Added (Phase 0)
- `cvloom build [--profile] [--template] [--public] [--skip-pdf]` — full
  build pipeline: YAML → JSON Schema validation → Jinja2 HTML → WeasyPrint PDF.
- `cvloom init` — scaffold project structure, install pre-commit PII scanner
  hook, verify `.gitignore` contains `private/`.
- JSON Schema validation for all data types: basics, contact, work, education,
  skills, project, profile.
- Two built-in templates: `cv/ats-single` (ATS-optimised single column) and
  `cv/modern-single` (visual hierarchy with skill tags).
- PII separation: contact data lives in gitignored `private/contact.yaml`;
  `--public` mode substitutes placeholder data.
- Per-project YAML files under `data/projects/*.yaml` with tag-based filtering.
- Named build profiles (`profiles/*.yaml`) with section visibility control,
  `include_tags`, and `job_context`.
- GitHub Actions workflow: test → build (public mode) → deploy to GitHub Pages.
- Pre-commit hook that scans staged files for contact data patterns.
- Word count and page estimate after each build.
