# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

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
