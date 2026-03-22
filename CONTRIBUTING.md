# Contributing to cvloom

Thank you for your interest in contributing.

## Scope

cvloom is intentionally narrow in scope: a local-first, YAML-driven CLI
for managing and building CV/cover-letter outputs without cloud accounts or
headless browsers. Contributions that preserve this scope are most welcome.

**Good fit:**
- Bug fixes and validation improvements
- New built-in templates (CV layouts, cover letter styles)
- ATS linter rules (Phase 2)
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
uv run ruff check cvloom tests    # lint
uv run ruff format cvloom tests   # format
uv run mypy cvloom                # type-check
uv run pytest -v                     # tests with output
```

All four commands must pass cleanly before opening a PR.

## Adding a template

1. Create `templates/<category>/<name>.html.j2`.
2. Extend `base.html.j2` and override the `css_vars`, `css_extra`, and `body`
   blocks as needed. See `templates/cv/ats-single.html.j2` for a minimal
   example.
3. Add a render test in `tests/test_renderer.py` that exercises the template
   with minimal fixture data.
4. Document the template in CHANGELOG.md under `[Unreleased]`.

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

## Adding a linter rule (Phase 2)

*(Placeholder — ATS linter not yet implemented.)*

Each rule will be a small function in `cvloom/linter.py` with a docstring
explaining what it checks and why. Rules should return per-bullet feedback with
the specific issue and a suggested fix.

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
- [ ] `uv run ruff check cvloom tests` passes (no errors)
- [ ] `uv run mypy cvloom` passes
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] New templates include a render test
