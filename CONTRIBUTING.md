# Contributing to cvloom

Thank you for your interest in contributing.

## Scope

cvloom is intentionally narrow in scope: a local-first, YAML-driven CLI
for managing and building CV/cover-letter outputs without cloud accounts or
headless browsers. Contributions that preserve this scope are most welcome.

**Good fit:**
- Bug fixes and validation improvements
- New built-in templates (CV layouts, cover letter styles)
- New ATS linter rules (see `docs/reference/ats-linter-rules.md`)
- Documentation and examples
- Test coverage

**Out of scope:**
- Web UI or server components
- Cloud storage or account systems
- Headless browser PDF (WeasyPrint is the canonical approach)
- AI content generation (AI-assisted *analysis* is different — discuss first)

## Getting started

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/SWEStash/cvloom
cd cvloom
uv sync --all-extras        # installs dev deps
uv run pytest               # run all tests
uv run cvloom --help     # smoke test
```

## Development workflow

```bash
uv run ruff check cvloom tests           # lint
uv run ruff format --check cvloom tests  # format check
uv run mypy cvloom                       # type-check (strict mode)
uv run pytest -v                            # tests with output
```

All four commands must pass cleanly before opening a PR — CI enforces them
on Python 3.11, 3.12, and 3.13.

## Adding a template

1. Create `templates/<category>/<name>.html.j2`.
2. Extend `base.html.j2` and override the `css_vars`, `css_extra`, and `body`
   blocks as needed. See `templates/cv/ats-single.html.j2` for a minimal
   example.
3. Add a render test in `tests/test_renderer.py` that exercises the template
   with minimal fixture data.
4. Document the template in CHANGELOG.md under `[Unreleased]`.

**Typography conventions:**

- Use at most **2 font families** per template (body + headings). More families add visual noise and slow PDF render.
- Prefer **Inter** or **Roboto** (sans-serif) for modern/professional templates; **Georgia** for academic templates.
- Always include system font fallbacks in every `--font-body` stack (e.g. `Inter, Arial, Helvetica, sans-serif`). Web fonts load over HTTPS; fallbacks ensure output when offline.
- Load web fonts via `{% block fonts %}` (defined in `base.html.j2`). Override it in your template with a Google Fonts `<link>` tag. Do not load more than 2 typefaces per template.
- `ats-single` intentionally uses **no web fonts** — keep it system fonts only for ATS compatibility.

**Template contract:**

| Variable | Type | Notes |
|---|---|---|
| `contact` | dict | Keys: name, email, phone, location, linkedin, github, website |
| `basics` | dict | Keys: headline, summary, public_links |
| `work` | list | Each entry: company, title, start_date, end_date?, location?, highlights?, tags? |
| `education` | list | Each entry: institution, degree, field?, start_date, end_date?, location?, highlights? |
| `skills` | list | Each entry: category, items (list of str or {name, level}) |
| `projects` | list | Each entry: name, description, tags, url?, start_date?, end_date?, highlights? |
| `show` | dict | Boolean flags: work, education, skills, projects |
| `job_context` | dict | Keys: company?, role?, hiring_manager?, notes? |
| `profile` | dict | Full profile config |
| `public` | bool | True when running in --public mode |
| `today` | str | Current date as "Month DD, YYYY" |

All Jinja2 filters defined in `cvloom/filters.py` are available:
`md` (Markdown → HTML), `date_range`, `skill_level_bar`.

## Third-party template convention

If you publish a template as a standalone package (not a PR to this repo), follow
this naming convention:

- **Package name:** `cvloom-template-<name>` (e.g. `cvloom-template-minimal`)
- **Template file:** `templates/<category>/<name>.html.j2` extending `base.html.j2`
- **pyproject.toml:** include `cvloom-template` as a keyword for discoverability
- **Required:** a render test, a CHANGELOG entry, and a README with a screenshot

This convention enables ecosystem discovery and makes it easy for users to find
community templates.

## Adding a linter rule

Each rule is a function `(ResolvedProfile) -> list[LintFinding]` registered in
the `RULES` list in `cvloom/linter.py`.

1. Write a check function following the existing pattern. Use `_check_highlights()`
   if your rule applies to individual bullet points (work/education/projects).
2. Create a `LintRule` entry with a unique `ats-NNN` ID, a short name, description,
   and your check function.
3. Append it to `RULES`.
4. Add tests in `tests/test_linter.py` covering both positive and negative cases.
5. Document the rule in `docs/reference/ats-linter-rules.md`.

See `_check_passive_voice` (ats-001) for a minimal example.

## Adding an export format

Export functions live in `cvloom/export.py`. Each format needs:

1. A `to_<format>(resolved: ResolvedProfile) -> dict` pure function that maps
   resolved CV data to the target schema.
2. An `export_<format>(resolved, output_path: Path) -> None` function that
   writes the file.
3. A new `--format` choice added to the `export` command in `cli.py`.
4. Tests in `tests/test_export.py`.

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add cover-letter/brief template
fix: handle missing end_date in date_range filter
docs: add template contribution guide
test: cover list-projects tag filtering
```

## Pull request checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check cvloom tests` and `uv run ruff format --check cvloom tests` pass
- [ ] `uv run mypy cvloom` passes
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] `docs/` updated if user-facing behaviour changed
- [ ] New templates include a render test
- [ ] New linter rules include tests for both triggering and clean cases
- [ ] New MCP tools include a test and an updated tool count in `docs/reference/mcp-server.md`
