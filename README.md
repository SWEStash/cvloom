# cvloom

**YAML-driven CV builder with per-job tailoring, ATS linting, and optional AI analysis.**

Keep your CV as structured data. Generate tailored PDF and HTML outputs per job application. PII stays out of version control.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Version 0.5.0](https://img.shields.io/badge/version-0.5.0-informational)

---

```
$ cvloom build --profile backend-role
  ✓ HTML  → dist/backend-role.html
  ✓ PDF   → dist/backend-role.pdf
  450 words · ~1 page(s)  [work×3  edu×1  skills×4  projects×2]

$ cvloom check --profile backend-role
  ats-001  work  Acme Corp  Passive voice detected: "was built"  Rewrite using an active verb.
  ats-002  work  Old Inc    No quantification found.              Add metrics: percentages, counts.

$ cvloom match --jd stripe-infra.txt --profile backend-role
  Coverage: 72% (18 of 25 JD keywords found)
  Gaps (7): kubernetes, terraform, grafana, ...

$ cvloom ai align --profile backend-role --jd stripe-infra.txt
  Alignment Score: 6.8/10

  The CV demonstrates solid backend experience but is framed around individual
  delivery rather than the infrastructure ownership Stripe emphasises...

  Repositioning Actions:
    1. Lead with distributed systems experience, not feature delivery
    2. Surface on-call and reliability work that is currently buried
    3. Replace "built" with ownership framing: "owned", "operated", "scaled"
```

---

## Features

| Category | Feature | Command |
|---|---|---|
| **Build** | YAML → HTML + PDF via WeasyPrint | `cvloom build` |
| | Named profiles with section and tag filtering | `--profile NAME` |
| | Per-job overlays — patch highlights without duplicating data | `overlays:` in profile |
| | Section reordering and force-include per profile | `section_order:` |
| | Public mode with placeholder contact data | `--public` |
| **Analyse** | ATS linter — 17 rules with per-bullet feedback | `cvloom check` |
| | ATS score (0–100) inline after build | `--check` / `--strict N` |
| | Per-section word breakdown and trim guidance | `cvloom trim` |
| | Side-by-side profile comparison | `cvloom diff A B` |
| **Match** | Keyword gap analysis from job description | `cvloom match --jd FILE` |
| **AI** | Section scoring with strengths, weaknesses, priorities | `cvloom ai review` |
| | Tailored cover letter from CV + JD | `cvloom ai cover` |
| | Content improvement suggestions for a target role | `cvloom ai suggest` |
| | Qualitative JD alignment — tone, framing, repositioning | `cvloom ai align` |
| **Export** | JSON Resume, Markdown, LinkedIn text, DOCX | `cvloom export` |
| **Inspect** | List projects with tag filtering | `cvloom list-projects` |
| | List all build profiles | `cvloom list-profiles` |
| **Integrate** | MCP server — 16 tools for LLM-driven CV management | `cvloom-mcp` |
| | GitHub Pages deployment | Built-in CI workflow |
| **Safety** | PII compartmentalisation + pre-commit scanner | `private/` + hook |

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

### Initialise a new CV project

```bash
mkdir my-cv && cd my-cv
cvloom init
```

Scaffolds the directory structure, creates sample YAML files, and installs the pre-commit PII scanner.

### Upgrade

```bash
uv tool upgrade cvloom
cvloom init   # refreshes the pre-commit hook; existing files are untouched
```

Check the [CHANGELOG](CHANGELOG.md) for any schema changes before upgrading.

### Edit your content

```
data/
├── basics.yaml          # headline, summary, public links
├── work.yaml            # work history
├── education.yaml       # education
├── skills.yaml          # skills by category
└── projects/            # one .yaml per project

private/
└── contact.yaml         # name, email, phone, address — GITIGNORED
```

### Build

```bash
cvloom build                          # default profile, HTML + PDF
cvloom build --profile backend-role   # specific profile
cvloom build --public --skip-pdf      # HTML only, placeholder contact
cvloom build --profile NAME --check   # build + ATS score
```

Outputs land in `dist/`. See [docs/user/cli-reference.md](docs/user/cli-reference.md) for the full command reference.

---

## AI Features

Optional AI-powered analysis layered on top of the rules-based tools. Works with **any OpenAI-compatible backend** — local models via [Ollama](https://ollama.ai), cloud routing via [LiteLLM](https://docs.litellm.ai), or OpenAI directly. All existing commands work unchanged when AI is not configured.

### Setup

```bash
uv sync --extra ai

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

| Template | Use case |
|---|---|
| `cv/ats-single` | ATS-optimised, single column, Arial font, no web fonts |
| `cv/modern-single` | Visual hierarchy, accent colour, skill tags, Inter |
| `cv/academic` | Education-first layout, serif font, research sections |
| `cv/timeline-clean` | Timeline-style work history, Roboto |
| `cv/executive-dark` | Dark headings, bold typographic hierarchy |
| `cv/sidebar-compact` | Two-column with sidebar, compact for dense CVs |
| `cover-letter/standard` | Professional cover letter driven by `job_context` |
| `cover-letter/brief` | Compact cover letter, no boilerplate sign-off |
| `project-summary/card` | Single-page project summary card |

---

## Profiles and Overlays

Each profile in `profiles/` controls template, sections, tag filtering, and section order:

```yaml
# profiles/backend-role.yaml
template: cv/ats-single
output_filename: jane-smith-backend
sections:
  work: true
  education: true
  skills: true
  projects: true
include_tags: [python, kafka, aws]
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
  skills:
    include_categories: [Languages, Cloud]
```

See [docs/reference/profiles-and-overlays.md](docs/reference/profiles-and-overlays.md) for the full overlay reference.

---

## MCP Server

cvloom includes an MCP server exposing 16 tools for LLM-driven CV management. Data stays local — nothing leaves your machine.

```bash
uv sync --extra mcp
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
| `check_cv` | Run ATS linter, return findings |
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
| [ATS Linter Rules](docs/reference/ats-linter-rules.md) | All 17 rules with examples and fix hints |
| [MCP Server](docs/reference/mcp-server.md) | Setup, all 16 tools, and example workflows |
| [Profiles and Overlays](docs/reference/profiles-and-overlays.md) | Full overlay system reference |

### Developer Guides

| Guide | What's covered |
|---|---|
| [Architecture](docs/dev/architecture.md) | Build pipeline, module responsibilities, data flow |
| [Custom Templates](docs/dev/custom-templates.md) | Writing Jinja2 templates, available blocks and filters |
| [Contributing](docs/dev/contributing.md) | Dev setup, testing, adding linter rules, PR checklist |

---

## License

MIT
