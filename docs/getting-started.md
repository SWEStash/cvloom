# Getting Started with cvloom

[Back to README](../README.md)

cvloom is a CLI tool that manages your CV/resume as structured YAML data and generates tailored PDF and HTML outputs for each job application. You write your experience once, then create **profiles** that filter, reorder, and customize the content for different roles — all without duplicating files.

This tutorial walks you through every feature, step by step. By the end you will have built multiple CV variants, a cover letter, run the linter, and explored the full toolset.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Scenario 1: Scaffold a New Project](#scenario-1-scaffold-a-new-project)
3. [Scenario 2: Fill In Your Data](#scenario-2-fill-in-your-data)
4. [Scenario 3: First Build](#scenario-3-first-build)
5. [Scenario 4: Lint Your CV](#scenario-4-lint-your-cv)
6. [Scenario 5: Trim Analysis](#scenario-5-trim-analysis)
7. [Scenario 6: Create a Tailored Profile](#scenario-6-create-a-tailored-profile)
8. [Scenario 7: Compare Profiles](#scenario-7-compare-profiles)
9. [Scenario 8: Export to JSON Resume](#scenario-8-export-to-json-resume)
10. [Scenario 9: Cover Letters](#scenario-9-cover-letters)
11. [Scenario 10: MCP Server](#scenario-10-mcp-server)
12. [Scenario 11: PII Safety and GitHub Pages](#scenario-11-pii-safety-and-github-pages)
13. [Next Steps](#next-steps)

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **WeasyPrint system dependencies** (for PDF generation):
  - Debian/Ubuntu: `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0`
  - macOS: `brew install pango`
  - Or skip PDFs with `--skip-pdf` if you just want HTML

Install cvloom with all extras:

```bash
uv sync --all-extras
```

---

## Scenario 1: Scaffold a New Project

Create a fresh project directory and initialize it:

```bash
mkdir my-cv
cd my-cv
uv run cvloom init
```

This creates the following structure:

```
my-cv/
├── data/
│   ├── basics.yaml           # Headline, summary, public links
│   ├── work.yaml             # Work history
│   ├── education.yaml        # Education
│   ├── skills.yaml           # Skills by category
│   └── projects/
│       └── example-project.yaml
├── profiles/
│   ├── general.yaml          # Default CV profile
│   └── cover-letter.yaml     # Cover letter profile
├── private/
│   └── contact.yaml          # Your real name, email, phone (gitignored)
└── .gitignore                # Protects private/ and dist/
```

**Key directories:**

| Directory    | Purpose                                  | In git? |
|-------------|------------------------------------------|---------|
| `data/`     | All CV content (PII-free)                | Yes     |
| `profiles/` | Build configurations                     | Yes     |
| `private/`  | Contact info, cover letter prose         | No      |
| `dist/`     | Generated HTML and PDF output            | No      |

Verify the scaffold worked:

```bash
uv run cvloom list-profiles
uv run cvloom list-projects
```

You should see the `general` and `cover-letter` profiles, plus the example project.

---

## Scenario 2: Fill In Your Data

Replace the sample content with your own. Open each file in your editor.

### 2.1 Private contact info

Edit `private/contact.yaml`:

```yaml
name: "Jane Smith"
email: "jane.smith@example.com"
phone: "+1 (555) 123-4567"
location: "San Francisco, CA"
website: "https://janesmith.dev"
linkedin: "janesmith"
github: "janesmith"
```

Only `name` and `email` are required. Everything else is optional.

### 2.2 Basics

Edit `data/basics.yaml`:

```yaml
headline: "Senior Backend Engineer"
summary: >
  Backend engineer with 7+ years building scalable distributed systems
  in Python and Go. Passionate about developer tooling, observability,
  and clean architecture.

public_links:
  - label: GitHub
    url: https://github.com/janesmith
  - label: Website
    url: https://janesmith.dev
```

### 2.3 Work experience

Edit `data/work.yaml`. Notice two formats for highlights — plain strings and `{id, text}` objects. Using IDs lets you target specific bullets in overlays later:

```yaml
- company: Acme Corp
  title: Senior Backend Engineer
  location: Remote
  start_date: "2021-03"
  end_date: Present
  highlights:
    - id: microservices
      text: "Led migration of monolith to 12 microservices, reducing deploy time by 60%."
    - id: kafka-pipeline
      text: "Designed event-driven pipeline processing 50k events/sec with Kafka."
    - id: oncall
      text: "Reduced P1 incidents by 40% through improved alerting and runbook automation."
    - "Mentored 3 junior engineers through structured pairing program."
  tags: [python, kafka, microservices, aws]

- company: Startup Inc
  title: Software Engineer
  location: "New York, NY"
  start_date: "2018-06"
  end_date: "2021-02"
  highlights:
    - id: api-redesign
      text: "Redesigned REST API, reducing p95 latency from 800ms to 120ms."
    - id: ci-pipeline
      text: "Built CI/CD pipeline with GitHub Actions, cutting release cycle from 2 weeks to 2 days."
    - "Implemented OAuth 2.0 integration serving 50k monthly active users."
  tags: [python, fastapi, postgresql, aws]
```

**Tips:**
- `start_date` and `end_date` accept `YYYY-MM` or `YYYY`. Use `Present` for current roles.
- `tags` are used for filtering in profiles (covered in Scenario 6).
- Work entries without `tags` are always included regardless of filtering.

### 2.4 Education

Edit `data/education.yaml`:

```yaml
- institution: State University
  degree: "Bachelor of Science"
  field: Computer Science
  location: "Anytown, USA"
  start_date: "2014"
  end_date: "2018"
  highlights:
    - "GPA 3.8/4.0"
    - "Teaching assistant for Data Structures and Algorithms"
```

### 2.5 Skills

Edit `data/skills.yaml`. Items can be plain strings or `{name, level}` objects:

```yaml
- category: Languages
  items:
    - name: Python
      level: expert
    - name: Go
      level: advanced
    - name: SQL
      level: advanced
    - name: TypeScript
      level: intermediate

- category: Frameworks & Libraries
  items: [FastAPI, Django, SQLAlchemy, Pydantic, Gin]

- category: Data & Messaging
  items: [PostgreSQL, Redis, Kafka, Elasticsearch]

- category: Infrastructure & Cloud
  items: [AWS, Docker, Kubernetes, Terraform, GitHub Actions]
```

Valid levels are: `beginner`, `intermediate`, `advanced`, `expert`.

### 2.6 Add a project

Create `data/projects/portfolio-api.yaml`:

```yaml
name: portfolio-api
description: >
  Open-source REST API framework with automatic OpenAPI documentation
  and built-in rate limiting.
url: https://github.com/janesmith/portfolio-api
start_date: "2023-06"
end_date: Present
highlights:
  - id: stars
    text: "800+ GitHub stars with contributions from 15 external developers."
  - "Automated release pipeline publishing to PyPI on every tag."
tags: [python, fastapi, open-source]
```

**Required fields** for projects: `name`, `description`, `tags`.

Verify your data is valid:

```bash
uv run cvloom list-projects
```

You should see your project listed with its tags.

---

## Scenario 3: First Build

### 3.1 Build the default profile

```bash
uv run cvloom build
```

This builds `profiles/general.yaml` using your real contact info from `private/contact.yaml`. The output tells you:

```
Profile:   general
Template:  cv/ats-single
HTML:      dist/cv.html
PDF:       dist/cv.pdf
Words:     ~480
Pages:     ~1
```

Open `dist/cv.html` in your browser to review the result.

### 3.2 Try different templates

Override the template at build time without changing the profile:

```bash
# Modern single-column design with accent colors
uv run cvloom build --template cv/modern-single

# Academic layout (education-first, serif font)
uv run cvloom build --template cv/academic
```

Available CV templates:
- `cv/ats-single` — ATS-optimized, clean, single-column
- `cv/modern-single` — Visual hierarchy with accent color and skill tags
- `cv/academic` — Education-first, serif font, suited for longer CVs

### 3.3 Public build (no real contact data)

For sharing publicly or in CI, use placeholder contact info:

```bash
uv run cvloom build --public --skip-pdf
```

This replaces your real name/email/phone with safe placeholders. The `--skip-pdf` flag skips WeasyPrint, producing HTML only (useful if you haven't installed the system dependencies).

### 3.4 Custom output directory

```bash
uv run cvloom build --output-dir out/
```

---

## Scenario 4: Lint Your CV

The ATS linter checks your bullet points for common quality issues. It runs 5 rules:

| Rule | What it catches |
|------|----------------|
| `ats-001` | Passive voice ("was built", "is designed") |
| `ats-002` | Missing metrics (no numbers in a bullet) |
| `ats-003` | Noise skills (MS Word, Google Docs) |
| `ats-004` | Weak verbs ("helped", "assisted", "worked on") |
| `ats-005` | Bullet too short (<8 words) or too long (>25 words) |

### 4.1 Run the linter

```bash
uv run cvloom check
```

If all your bullets are strong, you will see a clean pass. To see the linter in action, temporarily add some weak content to `data/work.yaml`:

```yaml
# Add these to the Acme Corp highlights (temporarily):
- "Was responsible for the deployment process."
- "Helped with testing."
- "Improved performance."
```

Now run the linter again:

```bash
uv run cvloom check
```

You will see findings like:

```
Rule     Section  Entry       Message                                     Fix
───────  ───────  ──────────  ──────────────────────────────────────────  ────────────────────────
ats-001  work     Acme Corp   "Was responsible for..." — passive voice    Use active voice
ats-004  work     Acme Corp   "Helped with testing" — weak verb           Start with a strong verb
ats-002  work     Acme Corp   "Improved performance" — no metrics         Add a number or %
ats-005  work     Acme Corp   3 words (min 8)                             Add context and impact
```

The exit code is `1` when issues are found — useful for CI.

**Fix the bullets** by replacing them with strong alternatives:

```yaml
- "Automated deployment pipeline, reducing release time from 4 hours to 15 minutes."
- "Wrote 200+ integration tests, increasing code coverage from 45% to 85%."
- "Improved API response time by 35% through query optimization and caching."
```

Run the linter again — it should pass cleanly now. Remove the temporary bullets when done.

For the full rule reference, see [ATS Linter Rules](ats-linter-rules.md).

---

## Scenario 5: Trim Analysis

The trim command analyzes word counts per section and recommends cuts to fit a page target.

### 5.1 Run the analysis

```bash
uv run cvloom trim
```

Sample output:

```
Section      Words   Entries
───────────  ──────  ───────
work           280        2
education       45        1
skills          38        4
projects        55        1
───────────  ──────  ───────
Total          418
Estimated    ~1.2 pages
Target       1 page
To cut       ~68 words

Recommendations:
  - work / Acme Corp: 160 words (largest entry — trim first)
  - work / Acme Corp: 22 words/bullet avg (consider tightening)
```

### 5.2 Target a different page count

For an academic CV where 2 pages is acceptable:

```bash
uv run cvloom trim --target-pages 2
```

### 5.3 Iterate

Act on the recommendations — tighten your longest bullets or remove low-impact ones. Then rebuild and re-trim to verify:

```bash
uv run cvloom build
uv run cvloom trim
```

---

## Scenario 6: Create a Tailored Profile

This is where cvloom shines. You will create a job-specific profile that:
- Filters entries by tags
- Overrides headline and summary
- Cherry-picks specific highlights
- Reorders sections
- Filters skill categories

### 6.1 Create the profile

Create `profiles/backend-role.yaml`:

```yaml
template: cv/ats-single
output_filename: backend-role-cv

# Only include entries tagged with at least one of these
include_tags: [python, kafka, aws, microservices]

# Lead with skills for this role
section_order: [skills, work, projects, education]

sections:
  work: true
  education: true
  skills: true
  projects: true

# Job metadata (useful for cover letters, available in templates)
job_context:
  company: "DataStream Inc"
  role: "Senior Backend Engineer"

# Per-job data patches
overlays:
  # Custom headline and summary for this application
  basics:
    headline: "Senior Backend Engineer — Python & Distributed Systems"
    summary: >
      Backend engineer with 7+ years specializing in event-driven
      architectures and high-throughput data pipelines. Deep experience
      with Kafka, AWS, and microservice orchestration at scale.

  # Cherry-pick the most relevant highlights from each job
  work:
    - match: {company: "Acme Corp"}
      highlights:
        mode: pick
        items: [microservices, kafka-pipeline]
        append:
          - "Designed zero-downtime deployment for 200-node Kafka cluster."

    - match: {company: "Startup Inc"}
      highlights:
        mode: pick
        items: [api-redesign]
        replace:
          api-redesign: "Redesigned REST API handling 10k req/sec, reducing p95 latency by 85%."

  # Only show relevant skill categories, remove a niche item
  skills:
    include_categories: [Languages, "Data & Messaging", "Infrastructure & Cloud"]
    category_overrides:
      Languages:
        exclude_items: [TypeScript]
```

### 6.2 Build the tailored profile

```bash
uv run cvloom build --profile backend-role
```

Open `dist/backend-role-cv.html` and compare it to your general CV. Notice:
- The headline and summary are customized
- Only tagged entries appear
- Work highlights are cherry-picked
- Skills show only 3 categories
- Sections are reordered (skills first)

### 6.3 Overlay reference

Here is a summary of overlay operations:

**Basics overlay** — shallow merge (override headline, summary):
```yaml
overlays:
  basics:
    headline: "Custom Title"
    summary: "Custom summary..."
```

**Array overlays** (work, education, projects) — match and patch:
```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}     # Find the entry
      title: "Custom Job Title"          # Override a field
      exclude: true                      # Or remove it entirely
      highlights:
        mode: pick | exclude | all       # Filter highlights by ID
        items: [id1, id2]               # IDs to pick or exclude
        replace: {id1: "New text"}       # Replace text by ID
        append: ["New bullet"]           # Add new highlights
```

**Skills overlay** — filter categories and items:
```yaml
overlays:
  skills:
    include_categories: [Languages, Cloud]   # Keep only these
    # OR: exclude_categories: [Frameworks]   # Remove these
    category_overrides:
      Languages:
        exclude_items: [Go, Rust]            # Remove specific items
```

For the full overlay reference, see [Profiles and Overlays](profiles-and-overlays.md).

---

## Scenario 7: Compare Profiles

The diff command shows what changed between two profiles:

```bash
uv run cvloom diff general backend-role
```

Sample output:

```
                general          backend-role
Template:       cv/ats-single    cv/ats-single
Words:          418              312 (-106)

Sections only in general:
  (none)

Sections only in backend-role:
  (none)

Entries only in general:
  - work / Startup Inc (partial — some highlights removed)

Entries only in backend-role:
  (none)

Highlight counts:
  work:       7 → 4 (-3)
  projects:   2 → 2 (0)
```

This helps you see at a glance how much content differs and whether you have trimmed enough for the targeted role.

---

## Scenario 8: Export to JSON Resume

Export your CV to the [JSON Resume](https://jsonresume.org) standard for uploading to job boards:

```bash
uv run cvloom export --format json-resume
```

This exports the default (`general`) profile. To export a specific profile:

```bash
uv run cvloom export --profile backend-role --format json-resume
```

To specify a custom output path:

```bash
uv run cvloom export --format json-resume --output resume.json
```

The exported file follows JSON Resume v1.0.0 and can be used with any tool or service that supports the format.

---

## Scenario 9: Cover Letters

cvloom can generate cover letters using the same data pipeline.

### 9.1 Create a cover letter profile

Create `profiles/datastream-letter.yaml`:

```yaml
template: cover-letter/standard
output_filename: datastream-cover-letter

job_context:
  company: "DataStream Inc"
  role: "Senior Backend Engineer"
  hiring_manager: "Alex Johnson"
  notes: |
    I am writing to express my interest in the Senior Backend Engineer
    position at DataStream Inc. With 7+ years of experience building
    high-throughput distributed systems, I am confident I can contribute
    to your team's mission of real-time data infrastructure.

    At Acme Corp, I led the migration from a monolithic architecture to
    12 microservices, reducing deploy time by 60%. I also designed an
    event-driven pipeline processing 50k events per second with Kafka —
    directly relevant to DataStream's core product.

    I would welcome the opportunity to discuss how my experience aligns
    with your team's goals. Thank you for your consideration.
```

### 9.2 Build the cover letter

```bash
uv run cvloom build --profile datastream-letter
```

Open `dist/datastream-cover-letter.html` to review. The cover letter template uses your contact info and the `job_context` fields to produce a formatted letter.

Available cover letter templates:
- `cover-letter/standard` — full formal cover letter
- `cover-letter/brief` — compact, one-paragraph format

---

## Scenario 10: MCP Server

> **Optional** — requires an MCP-compatible client (Claude Desktop, Claude Code).

cvloom ships an MCP server that lets AI assistants build CVs, create profiles, validate data, and more — all through a structured tool interface.

### 10.1 Install the MCP extra

```bash
uv sync --extra mcp
```

### 10.2 Connect to a client

**Claude Code:**
```bash
claude mcp add cvloom -- cvloom-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "cvloom": {
      "command": "cvloom-mcp",
      "args": []
    }
  }
}
```

The MCP server exposes 8 tools: `list_profiles`, `list_projects`, `get_section`, `build_cv`, `create_profile`, `upsert_project`, `validate_data`, and `export_json_resume`.

For the full tool reference and example workflows, see [MCP Server](mcp-server.md).

---

## Scenario 11: PII Safety and GitHub Pages

### 11.1 How PII is protected

Your real contact info lives in `private/contact.yaml`, which is gitignored. The pre-commit hook (installed by `cvloom init`) scans staged files for email addresses and phone numbers. If it finds a match outside `private/`, the commit is blocked.

Two build modes keep your data safe:

| Flag | Contact data | Use case |
|------|-------------|----------|
| *(default)* | `private/contact.yaml` | Local builds for applications |
| `--public` | Placeholder values | CI, GitHub Pages, sharing |

### 11.2 GitHub Pages deployment

You can publish a public CV (with placeholder contact) automatically:

1. Go to **Settings > Pages > Source** and select **GitHub Actions**.
2. The workflow at `.github/workflows/build.yml` runs `cvloom build --public` on push to `main`.
3. Your CV is available at `https://<username>.github.io/<repo>/`.

For full setup instructions, see [GitHub Pages Setup](github-pages-setup.md) and [PII Safety](pii-safety.md).

---

## Next Steps

You have now used every major feature of cvloom. Here are some things to explore next:

- **Create more profiles** for different roles — each one takes minutes once your base data is complete.
- **Add more projects** in `data/projects/` — one YAML file per project.
- **Customize templates** — put custom Jinja2 templates in `templates/` at your project root.
- **Automate with CI** — use `--public --skip-pdf` for fast HTML-only builds in GitHub Actions.

### Reference Documentation

| Document | Description |
|----------|-------------|
| [CLI Command Reference](usage.md) | Every command, flag, and option |
| [Profiles and Overlays](profiles-and-overlays.md) | Deep dive into the profile and overlay system |
| [ATS Linter Rules](ats-linter-rules.md) | Full rule reference with examples |
| [MCP Server](mcp-server.md) | MCP tool reference and workflow examples |
| [PII Safety](pii-safety.md) | How contact data is protected |
| [GitHub Pages Setup](github-pages-setup.md) | Automated public CV deployment |
