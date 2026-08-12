# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.9.0](https://github.com/SWEStash/cvloom/compare/v0.8.0...v0.9.0) (2026-08-12)


### Features

* **ai:** add --body-only cover letters and harden the provider ([#22](https://github.com/SWEStash/cvloom/issues/22)) ([5e20bc0](https://github.com/SWEStash/cvloom/commit/5e20bc02c1ec613c6a83544db5287fa14a591a16))
* **ai:** give the model what the linter already knows ([#21](https://github.com/SWEStash/cvloom/issues/21)) ([abbf3c0](https://github.com/SWEStash/cvloom/commit/abbf3c01ff5b1869b1f7671df5ebdf07544d92f9))
* **ai:** replace AI scores with anchored qualitative bands ([e864509](https://github.com/SWEStash/cvloom/commit/e8645093ca35cc53b50c69ba0cd80409d2e49378))
* **ai:** tell the model which openers the linter will flag ([#25](https://github.com/SWEStash/cvloom/issues/25)) ([650bc3b](https://github.com/SWEStash/cvloom/commit/650bc3b188d273c816ff2e5be2c56dc594054957))


### Bug Fixes

* **ai:** answer in the CV's own language ([#20](https://github.com/SWEStash/cvloom/issues/20)) ([f77f771](https://github.com/SWEStash/cvloom/commit/f77f77198cbde52b58aaaadf5061b54dc5c2f105))
* **ai:** ground the AI layer in the CV it was actually given ([#17](https://github.com/SWEStash/cvloom/issues/17)) ([c40c708](https://github.com/SWEStash/cvloom/commit/c40c708b8c100d311c284398a80fd33c10cd3703))
* **ai:** stop the model reviewing a CV that isn't there ([#19](https://github.com/SWEStash/cvloom/issues/19)) ([b898ee8](https://github.com/SWEStash/cvloom/commit/b898ee8e7bbac444500856553c724423f54f36b6))

## [0.8.0](https://github.com/SWEStash/cvloom/compare/v0.7.0...v0.8.0) (2026-08-07)


### Features

* show how long each role lasted ([#15](https://github.com/SWEStash/cvloom/issues/15)) ([ddfff1b](https://github.com/SWEStash/cvloom/commit/ddfff1bd3da0a5c89ae3e45c803b29809926c938))

## [0.7.0](https://github.com/SWEStash/cvloom/compare/v0.6.1...v0.7.0) (2026-08-07)


### Features

* add cvloom.yaml project config and locale packs ([#7](https://github.com/SWEStash/cvloom/issues/7)) ([bed99bc](https://github.com/SWEStash/cvloom/commit/bed99bc27da919e6ee4184dd153670bcbed8035c))
* consume the locale pack in templates, linter and export ([#8](https://github.com/SWEStash/cvloom/issues/8)) ([361cb68](https://github.com/SWEStash/cvloom/commit/361cb68ca1743492eaa3d50463da06bf62288022))
* grade and match Spanish CVs with Spanish rules ([#10](https://github.com/SWEStash/cvloom/issues/10)) ([123080d](https://github.com/SWEStash/cvloom/commit/123080df8c6ad65b6e73f144d9f7933f39adcb24))
* localize cover-letter furniture and dates ([#12](https://github.com/SWEStash/cvloom/issues/12)) ([284dabc](https://github.com/SWEStash/cvloom/commit/284dabcfdcd4b13ed54b8db5669418262fd5b770))
* read AI provider config from cvloom.yaml ([#13](https://github.com/SWEStash/cvloom/issues/13)) ([f417f8b](https://github.com/SWEStash/cvloom/commit/f417f8b163d9892200440b468d38c6abf843258e))
* remove cvloom's own connecting words from every output ([#4](https://github.com/SWEStash/cvloom/issues/4)) ([26128d0](https://github.com/SWEStash/cvloom/commit/26128d04b61062c34542db01b3eced76268b44da))
* surface locale in the CLI, init, MCP and the docs ([#11](https://github.com/SWEStash/cvloom/issues/11)) ([a444e0d](https://github.com/SWEStash/cvloom/commit/a444e0d4a7cfa5be2137cc59c62549269cc9caab))


### Bug Fixes

* let one command bring a project up to date after an upgrade ([#14](https://github.com/SWEStash/cvloom/issues/14)) ([7b6db67](https://github.com/SWEStash/cvloom/commit/7b6db672e64878b426531acce762ebe76719383e))


### Documentation

* fix extra-install instructions for uv tool/pipx/pip installs ([#6](https://github.com/SWEStash/cvloom/issues/6)) ([4e1604b](https://github.com/SWEStash/cvloom/commit/4e1604bb45a1c2313edc7a007fb3561374af33c7))
* state the &lt;h2&gt; constraint the qa locale audit depends on ([#9](https://github.com/SWEStash/cvloom/issues/9)) ([48a535f](https://github.com/SWEStash/cvloom/commit/48a535f883105a6e01a6abf044f13667c34a7ead))

## [0.6.1](https://github.com/SWEStash/cvloom/compare/v0.6.0...v0.6.1) (2026-08-05)


### Bug Fixes

* **mcp:** friendly error when cvloom-mcp runs without the [mcp] extra ([64994a9](https://github.com/SWEStash/cvloom/commit/64994a9cf6b5a41291c65cb1f9eb5c0cacbd5c91))


### Documentation

* add GitHub issue templates (bug, feature) + security routing ([e73a170](https://github.com/SWEStash/cvloom/commit/e73a170eeb155563b0fcb62ee41845cd6aefc582))

---

## [0.6.0] — 2026-08-05

First public release on PyPI — `pip install cvloom` or `uv tool install cvloom`. Pre-1.0: the
CV/profile schema and CLI may still change on a MINOR bump. This entry consolidates all work since
0.5.0; the git history carries the per-change rationale.

### Breaking
- `export --format linkedin` is now `--format text` and exports the whole CV (output moves to `dist/<profile>.resume.txt`).
- Template `cv/ats-single` renamed `cv/ats-clean`.
- Per-job filtering: `include_tags` / `include_entries` replaced by per-section `select`; an untagged entry no longer matches an include list, and entry `tags` are no longer rendered.
- Profile links moved to `data/basics.yaml` as `links` (full URLs); the old handle fields in `private/contact.yaml` and `basics.public_links` are gone.
- Lint rule IDs renamed `ats-NNN` -> `wl-NNN`.
- The single "ATS score 0-100" is gone; `--strict N` is now a findings budget (fail if more than N findings).

### Added
- New CV sections -- `publications`, `certifications`, `awards`, `languages` -- all mapping to native JSON Resume arrays. Certifications take a `type` (certification / license / course / micro-credential) that splits credentials from coursework; `tags` are now allowed on education entries.
- `cvloom list-templates` -- each template's column count, PDF text-extraction rating (safe / caution / unsafe), fonts, and caveats.
- `cvloom build --all` builds every profile in one run (stops on the first failure).
- `cvloom build --extract-text` writes the PDF text layer per engine, so you can see what an ATS actually reads.
- `section_titles` in a profile renames any section heading (text only; styling stays in the template).
- Global `--verbose` flag; ordinary mistakes now print one line instead of a Python traceback.
- Header links are real, clickable anchors (`link_anchor` filter); `public_name` for pen-name `--public` builds.
- Six new lint rules: `wl-018` education-size, `wl-019` chronological-order, `wl-020` date-sanity, `wl-021` unfilled-placeholders, `wl-022` duplicate-links, `wl-023` non-ascii-dashes.
- Build- and check-time warnings for any template not rated ATS-safe, recommending the DOCX export.
- Contact icons on the design-led templates.
- `cvloom import --format json-resume` (PII-aware split), `cvloom sync` (refresh scaffolded files), and a reusable opt-in GitHub Pages publish workflow scaffolded by `init`.
- MCP agent-safety hardening (structured errors, PII fence); `SECURITY.md`, MIT `LICENSE`, and CI gates (ruff / format / mypy across Python 3.11-3.13).

### Changed
- ATS ratings are measured from five independent PDF extraction engines on every build, not asserted; five of six templates rate `safe`, `cv/sidebar-compact` `caution`.
- Everything cvloom emits uses ASCII hyphens and pipes for ranges and separators; `ats-clean` / `academic` are ASCII throughout while the design templates keep the middot / en-dash.
- Section and entry titles are real `<h2>` / `<h3>` and reach the PDF structure tree as `/H2` / `/H3`.
- Dates run inline on the entry meta line (except `cv/sidebar-compact`), fixing the extraction column that scrambled date order.
- Fonts and palettes refreshed (Lato, Source Sans 3; steel and slate accents); default section order now leads with work, not skills; page ceiling raised 2 -> 3.
- The pre-commit PII hook scans only a diff's added lines and allows reserved documentation placeholders (RFC 2606 domains, `555` / Ofcom phone ranges).
- `resolve()` is now a pure function (raises a typed `ResolveError`); the pipeline is driven by a section registry; `cli.py` was decomposed and scaffolding moved to a `cvloom.scaffold` package.
- README repositioned around the wedge; demo content moved to `examples/`; docs reconciled and template tables generated from `templates_meta`; `__version__` single-sourced from `pyproject.toml`; `LICENSE` holder set to SWEStash.
- The `[mcp]` extra is pinned to `mcp>=1.0,<2` (mcp 2.0 removed the bundled FastMCP).

### Fixed
- Many PDF text-extraction defects that were invisible on the page but broke what an ATS reads: kerning splitting words (`font-kerning: none`), heading letter-spacing (`.06em`), right-aligned date columns, the timeline rule/dot, and `cv/sidebar-compact` print styling (also ~10x faster via a CSS table instead of grid).
- Markdown never actually rendered (autoescape swallowed the generated HTML); the filter now returns `Markup` with raw HTML disabled, which also closes an injection vector on published Pages builds.
- JSON Resume export now conforms to the schema (empty and non-ISO fields omitted), and the export -> import round-trip preserves tags and other extras via an `x-cvloom-*` namespace.
- `cvloom match` counts every section toward keyword coverage; omitting an optional field no longer crashes the build under `StrictUndefined`; the post-build section summary is no longer swallowed by Rich markup.
- Lint false positives fixed: `wl-002` reports once per entry, `wl-007` ignores roman numerals, `wl-013` ignores present-tense `-ed` verbs, `wl-019` checks certification groups independently.
- `--help` on a subcommand exits 0; the MCP `uvx` client config is runnable (`uvx --from "cvloom[mcp]" cvloom-mcp`); MCP tools return real validation `details` instead of "exit code 1".

### Removed
- `include_tags` / `include_entries` (replaced by `select`) and the rendering of entry `tags`.
- Handle-based profile links in `private/contact.yaml` and `basics.public_links` (replaced by `basics.links`).

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
- **Typography (Phase 4):** Added `{% block fonts %}` to `base.html.j2`; `timeline-clean`, `modern-single`, `executive-dark`, and `sidebar-compact` now load Google Fonts (Inter or Roboto) via HTTPS `<link>` tags. `ats-clean` and `academic` remain system-fonts-only by design.
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
- Two built-in templates: `cv/ats-clean` (ATS-optimised single column) and
  `cv/modern-single` (visual hierarchy with skill tags).
- PII separation: contact data lives in gitignored `private/contact.yaml`;
  `--public` mode substitutes placeholder data.
- Per-project YAML files under `data/projects/*.yaml` with tag-based filtering.
- Named build profiles (`profiles/*.yaml`) with section visibility control,
  `include_tags`, and `job_context`.
- GitHub Actions workflow: test → build (public mode) → deploy to GitHub Pages.
- Pre-commit hook that scans staged files for contact data patterns.
- Word count and page estimate after each build.
