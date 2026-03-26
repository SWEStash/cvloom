# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — Phase 3

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

## [Unreleased] — Phase 2

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

## [Unreleased] — Phase 1

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

## [0.1.0] — Phase 0 — 2026-03-20

Initial working prototype.

### Added
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
