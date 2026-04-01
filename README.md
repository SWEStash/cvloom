# cvloom

A CLI tool to manage your CV/resume as YAML and generate tailored PDF and HTML outputs per job application — keeping PII out of version control.

```
$ cvloom build --profile backend-role
  ✓ HTML  → dist/backend-role.html
  ✓ PDF   → dist/backend-role.pdf
  450 words · ~1 page(s)  [work×3  edu×1  skills×4  projects×2]

$ cvloom check --profile backend-role
  ats-001  work  Acme Corp  Passive voice detected: "was built"  Rewrite using an active verb.
  ats-002  work  Old Inc    No quantification found.              Add metrics: percentages, counts.
  2 issue(s) found.

$ cvloom diff general backend-role
  Sections only in general: projects
  Words: 620 vs 450 (-170)
  Highlights: 12 vs 8

$ cvloom match --jd stripe-infra.txt --profile backend-role
  Coverage: 72% (18 of 25 JD keywords found)
  Gaps (7): kubernetes, terraform, grafana, ...
```

## Features

| Category | Feature | Command / Key |
|---|---|---|
| **Build** | YAML → HTML + PDF via WeasyPrint | `cvloom build` |
| | Named profiles with section/tag filtering | `--profile NAME` |
| | Per-job overlays (match-and-patch highlights) | `overlays:` in profile |
| | Section reordering per profile | `section_order:` in profile |
| | Public mode with placeholder contact data | `--public` |
| **Analyse** | ATS linter — 5 rules with per-bullet feedback | `cvloom check` |
| | Per-section word breakdown + trim guidance | `cvloom trim` |
| | Side-by-side profile comparison | `cvloom diff A B` |
| **Match** | Keyword gap analysis from job description | `cvloom match --jd FILE` |
| **Export** | JSON Resume format | `cvloom export --format json-resume` |
| **Inspect** | List projects with tag filtering | `cvloom list-projects` |
| | List all build profiles | `cvloom list-profiles` |
| **Integrate** | MCP server — 12 tools for LLM-driven CV management | `cvloom-mcp` |
| | GitHub Pages deployment | Built-in CI workflow |
| **Safety** | PII compartmentalisation + pre-commit scanner | `private/` + hook |

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

### Upgrade

```bash
# If installed globally:
uv tool upgrade cvloom

# Then refresh the pre-commit hook in your project directory:
cvloom init
```

`init` skips every file that already exists — your `data/`, `profiles/`, and `private/` are untouched. Only the pre-commit hook is always reinstalled. Check the [CHANGELOG](CHANGELOG.md) for any schema changes that require editing your YAML files.

### Initialise a new CV project

```bash
mkdir my-cv && cd my-cv
cvloom init
```

This scaffolds the directory structure, creates sample data files, and installs the pre-commit PII scanner.

### Edit your content

```
data/
├── basics.yaml      # headline, summary, public links
├── work.yaml        # work history
├── education.yaml   # education
├── skills.yaml      # skills by category
└── projects/        # one .yaml per project
    └── my-project.yaml

private/
└── contact.yaml     # name, email, phone, address (GITIGNORED)
```

### Build

```bash
cvloom build                                    # default profile, HTML + PDF
cvloom build --profile backend-role             # specific profile
cvloom build --public --skip-pdf                # HTML only, placeholder contact
```

Outputs land in `dist/`. See [docs/usage.md](docs/usage.md) for the full command reference.

## Templates

| Template | Use case |
|---|---|
| `cv/ats-single` | ATS-optimised, single column, Arial font |
| `cv/modern-single` | Visual hierarchy, accent colour, skill tags |
| `cv/academic` | Education-first layout, serif font, research sections |
| `cover-letter/standard` | Professional cover letter driven by `job_context` |
| `cover-letter/brief` | Compact cover letter, no boilerplate sign-off |
| `project-summary/card` | Single-page project summary card |

## Profiles and Overlays

Each profile in `profiles/` controls which template, sections, and project tags to include:

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
```

Overlays let you patch data per job application — override highlights, exclude entries, filter skills — without duplicating your base CV data:

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

See [docs/profiles-and-overlays.md](docs/profiles-and-overlays.md) for the full overlay reference.

## MCP Server

cvloom includes an MCP server that exposes 8 tools for LLM-driven CV management. Data stays local — nothing leaves your machine.

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

```bash
uv sync --extra mcp    # install MCP dependency
cvloom-mcp           # start the server
```

See [docs/mcp-server.md](docs/mcp-server.md) for setup with Claude Desktop/Claude Code and example workflows.

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

## Documentation

- [Command Reference](docs/usage.md) — all CLI commands with flags and examples
- [Profiles and Overlays](docs/profiles-and-overlays.md) — profile system and per-job data patches
- [ATS Linter Rules](docs/ats-linter-rules.md) — what each rule checks and how to fix findings
- [MCP Server](docs/mcp-server.md) — setup, tool reference, and example workflows
- [PII Safety](docs/pii-safety.md) — two-layer protection model
- [GitHub Pages Setup](docs/github-pages-setup.md) — automatic deployment

## License

MIT
