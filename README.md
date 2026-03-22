# cvloom

A CLI tool to manage your CV/resume as YAML and generate tailored PDF and HTML outputs per job application — keeping PII out of version control.

```
cvloom build --profile backend-role --private   # → dist/backend-role.pdf
cvloom build --profile general --public         # → dist/cv.html (placeholder contact)
```

## Features

- **Single source of truth** — all CV content in YAML; structured, diffable, git-native
- **Tailored outputs** — named profiles select which sections/projects to include per role
- **PII-safe** — `private/` is gitignored; pre-commit hook blocks accidental commits
- **Three CV templates** — `ats-single` (ATS-optimised), `modern-single` (visual), `academic` (education-first) + cover letter template
- **Profile overlays** — match-and-patch highlights, pick/exclude/replace per job application
- **CLI commands** — `list-projects`, `list-profiles` for quick project/profile inspection
- **No browser needed** — WeasyPrint renders PDF in ~20MB; no headless Chrome
- **GitHub Pages** — built-in workflow deploys a placeholder-contact version automatically

## Quickstart

### Install

```bash
# Install globally with pipx/uv:
uv tool install cvloom

# Development setup:
git clone https://github.com/SWEStash/cvloom
cd cvloom
uv sync --all-extras
```

### Initialise a new CV project

```bash
mkdir my-cv && cd my-cv
uv run cvloom init
```

This scaffolds the directory structure, creates `private/contact.yaml`, and installs the pre-commit PII scanner.

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
# Build with your real contact data (local use):
uv run cvloom build --private

# Build with placeholder contact (safe for CI/GitHub Pages):
uv run cvloom build --public

# Build a specific profile:
uv run cvloom build --profile backend-role --private

# HTML only (no WeasyPrint needed):
uv run cvloom build --skip-pdf --public
```

Outputs land in `dist/`.

## Profiles

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
include_tags: [python, kafka, aws]   # only projects/work tagged with these
job_context:
  company: Acme Corp
  role: Staff Engineer
```

## Templates

| Template | Use case |
|---|---|
| `cv/ats-single` | ATS-optimised, single column, Arial font |
| `cv/modern-single` | Visual hierarchy, accent colour, skill tags |
| `cv/academic` | Education-first layout, serif font, research sections |
| `cover-letter/standard` | Professional cover letter driven by `job_context` |

## Directory structure

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

## PII Safety

See [docs/pii-safety.md](docs/pii-safety.md) for details on the two-layer protection model.

## GitHub Pages

See [docs/github-pages-setup.md](docs/github-pages-setup.md) to set up automatic deployment.

## License

MIT
