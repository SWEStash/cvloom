# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
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
