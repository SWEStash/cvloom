# cvloom

**Manage your CV as one YAML dataset and generate any number of per-job-tailored PDFs from it — deterministically, with an agent-safe MCP layer and PII kept out of git.**

Per-job **overlays** let you tailor a CV for each application by declarative config, not by
copying files — so twenty variants stay consistent with one source of truth, and every variant is
diffable and reviewable.

> RenderCV renders one CV beautifully; cvloom manages twenty tailored variants of one dataset — with an agent-safe MCP layer.

![PyPI](https://img.shields.io/pypi/v/cvloom)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

Every command below is runnable in [`examples/`](examples/):

```
$ cvloom build --profile general          # your full CV, from one dataset
  ✓ HTML  → dist/cv.html
  ✓ PDF   → dist/Your_Name_Resume.pdf

$ cvloom build --profile example-job      # …same data, tailored for a specific role
  ✓ HTML  → dist/example-job-cv.html

$ cvloom diff general example-job         # tailoring is declarative + diffable
  Words: 195 vs 184 (-11)
  Highlights: 12 vs 12

$ cvloom check --profile example-job      # writing lint — no fake "ATS score"
  wl-002  writing  projects  cvloom  No quantification found  Add metrics.

$ cvloom match --jd stripe-infra-jd.txt --profile example-job
  Coverage: 41% (27 of 66 JD keywords found)
```

Change a fact once in `data/` and every profile that uses it updates on the next build. See the
worked [one dataset, N applications](docs/reference/profiles-and-overlays.md#one-dataset-n-applications--a-worked-example)
example.

---

## Features

| Category | Feature | Command |
|---|---|---|
| **Build** | YAML → HTML + PDF via WeasyPrint | `cvloom build` |
| | Named profiles with per-section content selection | `--profile NAME` |
| | Per-job overlays — patch highlights without duplicating data | `overlays:` in profile |
| | Per-section reordering and visibility | `section_order:` / `sections:` |
| | Rename any section heading, styling untouched | `section_titles:` in profile |
| | Build every profile in one run | `cvloom build --all` |
| | Public mode with placeholder contact data | `--public` |
| **Localise** | Write and grade the CV in your own language — English and Spanish | `locale:` in `cvloom.yaml` |
| | Scaffold a project in a language | `cvloom init --locale es` |
| **Analyse** | Writing lint — 25 rules across writing / structure / ats-parse axes | `cvloom check` |
| | Per-axis lint breakdown inline after build (no fake "ATS score") | `--check` / `--strict N` |
| | Per-section word breakdown and trim guidance | `cvloom trim` |
| | Side-by-side profile comparison | `cvloom diff A B` |
| **Match** | Keyword gap analysis from job description | `cvloom match --jd FILE` |
| **AI** | Section scoring with strengths, weaknesses, priorities | `cvloom ai review` |
| | Tailored cover letter from CV + JD | `cvloom ai cover` |
| | Content improvement suggestions for a target role | `cvloom ai suggest` |
| | Qualitative JD alignment — tone, framing, repositioning | `cvloom ai align` |
| **Export** | JSON Resume, Markdown, plain text, DOCX | `cvloom export` |
| **Inspect** | List projects with tag filtering | `cvloom list-projects` |
| | List all build profiles | `cvloom list-profiles` |
| | List templates with their PDF text-extraction rating | `cvloom list-templates` |
| | List locales with their document and lint-rule coverage | `cvloom list-locales` |
| **Integrate** | Agent-safe MCP server — 17 tools over a schema-validated, PII-fenced data model | `cvloom-mcp` |
| | Publish to GitHub Pages — reusable, opt-in workflow scaffolded by `init` | `publish-cv.yml` |
| **Safety** | PII compartmentalisation + pre-commit scanner + `--public` builds | `private/` + hook |

---

## Quickstart

### Install

```bash
# Install globally:
uv tool install cvloom

# Development setup:
git clone https://github.com/SWEStash/cvloom
cd cvloom
uv sync --all-extras
```

The repo root is the tool itself; a runnable demo CV lives in [`examples/`](examples/)
(`cd examples && cvloom build --profile general --public`).
[`examples-es/`](examples-es/) is the same project in Spanish — a separate directory
because a cvloom project operates in one language. See
[Locales](docs/reference/locales.md).

### Initialise a new CV project

```bash
mkdir my-cv && cd my-cv
cvloom init                # or: cvloom init --locale es
```

Scaffolds the directory structure, creates sample YAML files, writes `cvloom.yaml`, and installs
the pre-commit PII scanner. `cvloom list-locales` shows the languages available and how completely
each is supported.

### Upgrade

```bash
uv tool upgrade cvloom
cvloom sync   # refresh scaffolded files (hook, publish workflow); reports first, --force applies
```

See [Keeping your instance updated](docs/user/keeping-updated.md); check the
[CHANGELOG](CHANGELOG.md) for breaking changes before a major upgrade.

### Edit your content

```
cvloom.yaml              # project settings — `locale:` is the language it operates in

data/
├── basics.yaml          # headline, summary, public links
├── work.yaml            # work history
├── education.yaml       # education
├── skills.yaml          # skills by category
├── projects/            # one .yaml per project
└── (optional)           # publications, certifications, awards, languages

private/
└── contact.yaml         # name, email, phone, address — GITIGNORED
```

### Build

```bash
cvloom build                          # default profile, HTML + PDF
cvloom build --profile backend-role   # specific profile
cvloom build --public --skip-pdf      # HTML only, placeholder contact
cvloom build --profile NAME --check   # build + writing-lint breakdown
```

Outputs land in `dist/`. See [docs/user/cli-reference.md](docs/user/cli-reference.md) for the full command reference.

---

## AI Features

Optional AI-powered analysis layered on top of the rules-based tools. Works with **any OpenAI-compatible backend** — local models via [Ollama](https://ollama.ai), cloud routing via [LiteLLM](https://docs.litellm.ai), or OpenAI directly. All existing commands work unchanged when AI is not configured.

### Setup

```bash
uv tool install 'cvloom[ai]'   # see docs/user/ai-features.md#installation for pipx/pip/dev-checkout

export CVLOOM_AI_BASE_URL=http://localhost:11434/v1   # Ollama, LiteLLM, OpenAI, etc.
export CVLOOM_AI_API_KEY=ollama                        # or your real key
export CVLOOM_AI_MODEL=gemma3:27b                      # or gpt-4o, claude-sonnet-4-6

cvloom ai config   # verify
```

### Commands

**`ai review`** — score each CV section 1–10 with strengths, weaknesses, and the three highest-impact improvements across the whole CV.

```bash
cvloom ai review --profile general
```

**`ai cover`** — generate a tailored cover letter from your CV and a job description file.

```bash
cvloom ai cover --profile backend-role --jd stripe-infra.txt --output cover.md
```

**`ai suggest`** — get specific content improvements: new bullet points, skill additions, rewordings, and removals for a target role.

```bash
cvloom ai suggest --profile backend-role --role "Senior Platform Engineer"
```

**`ai align`** — qualitative analysis of how well your CV is *positioned* for a specific JD — tone, framing, narrative gaps — beyond keyword coverage.

```bash
cvloom ai align --profile backend-role --jd stripe-infra.txt
```

See [docs/user/ai-features.md](docs/user/ai-features.md) for backend quickstarts (Ollama, LiteLLM, OpenAI) and all configuration options.

---

## Templates

`Parses` is how the rendered PDF survives text extraction — the step every ATS runs
first. Ratings are measured with five independent extractors, from raw content-stream
order through geometric reconstruction to the PDF structure tree; only what
survives all five is rated safe. It is a property of the layout, not of your writing, so `cvloom check` does not
cover it; `cvloom list-templates` prints this table, and `build` warns on anything not
rated safe. See [ATS-readiness](docs/reference/ats-readiness.md) for the measurements.

| Template | Cols | Parses | Font | Use case |
|---|:--:|:--:|---|---|
| `cv/ats-clean` | 1 | ✅ safe | Arial (system) | Single column, no web fonts. The one to upload to a portal. |
| `cv/academic` | 1 | ✅ safe | Georgia (system) | Education-first serif CV. Runs long by convention; no page-count warning. |
| `cv/modern-single` | 1 | ✅ safe | Lato | Single column, slate rule system, aligned skills column. |
| `cv/timeline-clean` | 1 | ✅ safe | Inter | Swiss minimal, timeline rule down the experience section. |
| `cv/executive-dark` | 1 | ✅ safe | Source Sans 3 | Carbon header band, steel accent, title-first entries. |
| `cv/sidebar-compact` | 2 | ⚠️ caution | Lato | Two-column coloured sidebar. Best-looking for a human; pdftotext interleaves it, the other four engines do not. |

The non-CV templates are unrated — they are not documents an ATS parses:

| Template | Use case |
|---|---|
| `cover-letter/standard` | Professional cover letter driven by `job_context` |
| `cover-letter/brief` | Compact cover letter, no boilerplate sign-off |
| `project-summary/card` | Single-page project summary card |

---

## Profiles and Overlays

Each profile in `profiles/` controls template, section visibility, content selection, section order, and heading text:

```yaml
# profiles/backend-role.yaml
template: cv/ats-clean
output_filename: jane-smith-backend
sections:
  work: true
  education: true
  skills: true
  projects: true
select:
  work:
    tags: [python, kafka, aws]
section_titles:
  work: "Professional Experience"   # text only — styling stays in the template
job_context:
  company: Stripe
  role: Senior Platform Engineer
```

**Overlays** let you patch data per job application — override highlights, exclude entries, filter skills — without duplicating your base CV:

```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}
      highlights:
        mode: pick
        items: [perf-boost, api-redesign]
```

Choosing *which* content appears is a separate `select` block — per-section, so
narrowing `work` leaves `education` alone:

```yaml
select:
  work:
    tags: [python, kafka, aws]
  skills:
    categories: [Languages, Cloud]
```

Because tailoring is declarative config, two variants are **diffable** (`cvloom diff A B`) and always consistent — update a fact once in `data/` and every profile that uses it updates on the next build. See the worked [one dataset, N applications example](docs/reference/profiles-and-overlays.md#one-dataset-n-applications--a-worked-example), or the [full overlay reference](docs/reference/profiles-and-overlays.md).

---

## MCP Server

cvloom includes an MCP server exposing 17 tools for LLM-driven CV management. Data stays local — nothing leaves your machine.

```bash
uv tool install 'cvloom[mcp]'   # see docs/reference/mcp-server.md#installation for pipx/pip/dev-checkout
cvloom-mcp
```

| Tool | What it does |
|---|---|
| `list_profiles` | List all build profiles |
| `list_projects` | List projects, filter by tags |
| `get_section` | Read raw YAML for any section |
| `build_cv` | Build CV and return stats |
| `create_profile` | Create a new profile |
| `upsert_project` | Create or update a project |
| `validate_data` | Run schema validation |
| `export_json_resume` | Export as JSON Resume |
| `check_cv` | Run writing lint, return categorized findings |
| `trim_report` | Per-section word counts and trim recommendations |
| `diff_profiles` | Compare two profiles side by side |
| `match_jd` | Keyword gap analysis against a JD |
| `ai_review_cv` | AI section scoring and feedback |
| `ai_generate_cover` | AI cover letter from CV + JD text |
| `ai_suggest_improvements` | AI content improvement suggestions |
| `ai_align_to_jd` | AI qualitative JD alignment analysis |

> AI tools require the `ai` extra and `CVLOOM_AI_BASE_URL` to be set.

See [docs/reference/mcp-server.md](docs/reference/mcp-server.md) for setup with Claude Desktop, Claude Code, and example workflows.

---

## Directory Structure

```
my-cv/
├── .gitignore          # private/ is LINE 1
├── cvloom.yaml         # project settings — the language it operates in
├── data/               # CV content (committed, PII-free)
├── profiles/           # build configs (committed)
├── private/            # GITIGNORED — contact.yaml, cover letters
├── dist/               # GITIGNORED — build output
├── hooks/              # pre-commit PII scanner
└── templates/          # Jinja2 templates (or use built-in)
```

---

## Documentation

### User Guides

| Guide | What's covered |
|---|---|
| [Getting Started](docs/user/getting-started.md) | Installation, init, and all features via step-by-step scenarios |
| [CLI Reference](docs/user/cli-reference.md) | Every command with flags, options, and examples |
| [User Guide](docs/user/user-guide.md) | Complete config and features manual — data files, templates, exports, env vars |
| [AI Features](docs/user/ai-features.md) | Setup, backends, and all AI commands |
| [PII Safety](docs/user/pii-safety.md) | Two-layer protection model |
| [GitHub Pages Setup](docs/user/github-pages-setup.md) | Automatic public CV deployment |

### Reference

| Guide | What's covered |
|---|---|
| [Writing Lint Rules](docs/reference/ats-linter-rules.md) | All 25 rules with categories, examples, and fix hints |
| [ATS-readiness model](docs/reference/ats-readiness.md) | The three honest axes, and why there is no single "ATS score" |
| [MCP Server](docs/reference/mcp-server.md) | Setup, all 17 tools, and example workflows |
| [Profiles and Overlays](docs/reference/profiles-and-overlays.md) | Full overlay system reference |
| [Locales](docs/reference/locales.md) | Running a project in your own language — pack keys, coverage, adding a locale |

### Developer Guides

| Guide | What's covered |
|---|---|
| [Architecture](docs/dev/architecture.md) | Build pipeline, module responsibilities, data flow |
| [Custom Templates](docs/dev/custom-templates.md) | Writing Jinja2 templates, available blocks and filters |
| [Contributing](CONTRIBUTING.md) | Dev setup, testing, adding linter rules, PR checklist |

---

## License

MIT
