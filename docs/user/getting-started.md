# Getting Started with cvloom

[Back to README](../../README.md)

cvloom is a CLI tool that manages your CV/resume as structured YAML data and generates tailored PDF and HTML outputs for each job application. You write your experience once, then create **profiles** that filter, reorder, and customize the content for different roles — all without duplicating files.

This tutorial walks you through every feature, step by step. By the end you will have built multiple CV variants, a cover letter, run the linter, used AI analysis, and explored the full toolset.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Scenario 1: Scaffold a New Project](#scenario-1-scaffold-a-new-project)
3. [Scenario 2: Fill In Your Data](#scenario-2-fill-in-your-data)
4. [Scenario 3: First Build](#scenario-3-first-build)
5. [Scenario 4: Lint Your CV](#scenario-4-lint-your-cv)
6. [Scenario 5: Trim Analysis](#scenario-5-trim-analysis)
7. [Scenario 6: Match Against a Job Description](#scenario-6-match-against-a-job-description)
8. [Scenario 7: Create a Tailored Profile](#scenario-7-create-a-tailored-profile)
9. [Scenario 8: Compare Profiles](#scenario-8-compare-profiles)
10. [Scenario 9: Export Formats](#scenario-9-export-formats)
11. [Scenario 10: Cover Letters](#scenario-10-cover-letters)
12. [Scenario 11: MCP Server](#scenario-11-mcp-server)
13. [Scenario 12: PII Safety and GitHub Pages](#scenario-12-pii-safety-and-github-pages)
14. [Scenario 13: AI-Powered Analysis](#scenario-13-ai-powered-analysis)
15. [Upgrading cvloom](#upgrading-cvloom)
16. [Next Steps](#next-steps)

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
├── templates/                 # Custom Jinja2 templates (optional)
└── .gitignore                # Protects private/ and dist/
```

**Key directories:**

| Directory    | Purpose                                  | In git? |
|-------------|------------------------------------------|---------|
| `data/`     | All CV content (PII-free)                | Yes     |
| `profiles/` | Build configurations                     | Yes     |
| `private/`  | Contact info, cover letter prose         | No      |
| `templates/`| Custom Jinja2 template overrides (optional) | Yes  |
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

Only `name` is required. Everything else is optional.

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
- `tags` are used for filtering in profiles (covered in Scenario 7).
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
# ATS-optimized, single-column (no web fonts)
uv run cvloom build --template cv/ats-single

# Modern single-column with accent colors and skill tags
uv run cvloom build --template cv/modern-single

# Timeline-style work history
uv run cvloom build --template cv/timeline-clean

# Dark headings, bold typographic hierarchy
uv run cvloom build --template cv/executive-dark

# Two-column with sidebar — compact for dense CVs
uv run cvloom build --template cv/sidebar-compact

# Academic layout (education-first, serif font)
uv run cvloom build --template cv/academic
```

Available CV templates:

| Template | Use case |
|---|---|
| `cv/ats-single` | ATS-optimised, clean, single-column |
| `cv/modern-single` | Visual hierarchy with accent color and skill tags |
| `cv/timeline-clean` | Timeline-style work history |
| `cv/executive-dark` | Bold typographic hierarchy with dark headings |
| `cv/sidebar-compact` | Two-column sidebar layout for dense CVs |
| `cv/academic` | Education-first, serif font, suited for longer CVs |

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

The writing lint checks your bullet points and CV structure for common quality issues. It runs 17 built-in rules across three honest axes (`writing`, `structure`, `ats-parse`) — see the [ATS-readiness model](../reference/ats-readiness.md) for why there is no single "ATS score":

| Rule | Severity | What it catches |
|------|:--------:|----------------|
| `wl-001` | warning | Passive voice ("was built", "is designed") |
| `wl-002` | warning | Missing metrics (no numbers in a bullet) |
| `wl-003` | warning | Noise skills (MS Word, Google Docs) |
| `wl-004` | warning | Weak verbs ("helped", "assisted", "worked on") |
| `wl-005` | warning | Bullet too short (<8 words) or too long (>25 words) |
| `wl-006` | warning | Too few (<3) or too many (>8) bullets per work entry |
| `wl-007` | warning | First-person pronouns (I/my/me) |
| `wl-008` | warning | Vague buzzwords (motivated, passionate, proactive, …) |
| `wl-009` | warning | Fewer than 8 or more than 25 total skills |
| `wl-010` | warning | No LinkedIn or GitHub link in contact |
| `wl-011` | warning | Estimated page count exceeds 2 |
| `wl-012` | warning | Mixed date formats (YYYY-MM vs YYYY) |
| `wl-013` | warning | Wrong verb tense for current vs past roles |
| `wl-014` | warning | Summary shorter than 20 or longer than 80 words |
| `wl-015` | suggestion | Metric present but no result-framing phrase |
| `wl-016` | suggestion | Flesch-Kincaid grade level outside 6–12 |
| `wl-017` | suggestion | Work entry highlights mention no skill item |

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
wl-001  work     Acme Corp   "Was responsible for..." — passive voice    Use active voice
wl-004  work     Acme Corp   "Helped with testing" — weak verb           Start with a strong verb
wl-002  work     Acme Corp   "Improved performance" — no metrics         Add a number or %
wl-005  work     Acme Corp   3 words (min 8)                             Add context and impact
```

The exit code is `1` when issues are found — useful for CI.

**Fix the bullets** by replacing them with strong alternatives:

```yaml
- "Automated deployment pipeline, reducing release time from 4 hours to 15 minutes."
- "Wrote 200+ integration tests, increasing code coverage from 45% to 85%."
- "Improved API response time by 35% through query optimization and caching."
```

Run the linter again — it should pass cleanly now. Remove the temporary bullets when done.

For the full rule reference, see [ATS Linter Rules](../reference/ats-linter-rules.md).

### 4.2 Build with inline writing-lint breakdown

Run the linter automatically after every build with `--check`:

```bash
uv run cvloom build --profile backend-role --check
```

To fail CI if there are more than N lint findings, use `--strict`:

```bash
uv run cvloom build --profile backend-role --strict 10
```

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

## Scenario 6: Match Against a Job Description

Before tailoring your CV, run a keyword gap analysis to see how well your current content matches a specific job description.

### 6.1 Create a job description file

Save the job description as a plain text file:

```bash
cat > jd-backend.txt << 'EOF'
Senior Backend Engineer — DataStream Inc

We are looking for a Senior Backend Engineer with deep experience in
Python, distributed systems, and event-driven architectures. You will
design and maintain high-throughput data pipelines using Kafka and AWS.
Experience with microservices, CI/CD, and observability is required.
Strong skills in PostgreSQL and REST API design preferred.
EOF
```

### 6.2 Run the match

```bash
uv run cvloom match --jd jd-backend.txt
```

By default this uses the `general` profile. To match against a specific profile:

```bash
uv run cvloom match --jd jd-backend.txt --profile backend-role
```

### 6.3 Read the report

Sample output:

```
Coverage: 72% (13 of 18 JD keywords found)
JD keyword count: 68

        Top JD Keywords
Keyword          JD Freq  In CV?  CV Sections
python                 3    ✓     work, skills
kafka                  2    ✓     work, skills
microservices          2    ✓     work
aws                    2    ✓     work, skills
distributed            1    ✓     basics
postgresql             1    ✓     work
observability          1    ✗

Gaps (5):
  ✗ observability
  ✗ event-driven
  ✗ high-throughput
  ✗ rest api design
  ✗ ci/cd
```

### 6.4 Reorder suggestions

If your work entries are not in the optimal order for the target role, the match report will add a **Reorder Suggestions** section:

```
Reorder Suggestions
  ↕  Work: move 'Backend Engineer at Stripe' before 'Analyst at Initech'
         (5 vs 1 JD keyword matches)
```

This means the second work entry has more JD keyword overlap than the first. Reorder them in your `data/work.yaml` (or use a profile overlay) so recruiters and ATS systems see your most relevant experience first.

### 6.5 Act on the gaps

Use the gaps to improve your CV before applying:
1. Add missing keywords to your highlights where they truthfully apply.
2. Create a tailored profile (Scenario 7) with overlays that emphasize the matched terms.
3. Re-run `match` to verify improved coverage.

---

## Scenario 7: Create a Tailored Profile

This is where cvloom shines. You will create a job-specific profile that:
- Filters entries by tags
- Overrides headline and summary
- Cherry-picks specific highlights
- Reorders sections
- Filters skill categories

### 7.1 Create the profile

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

### 7.2 Build the tailored profile

```bash
uv run cvloom build --profile backend-role
```

Open `dist/backend-role-cv.html` and compare it to your general CV. Notice:
- The headline and summary are customized
- Only tagged entries appear
- Work highlights are cherry-picked
- Skills show only 3 categories
- Sections are reordered (skills first)

### 7.3 Overlay reference

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

For the full overlay reference, see [Profiles and Overlays](../reference/profiles-and-overlays.md).

---

## Scenario 8: Compare Profiles

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

## Scenario 9: Export Formats

Four export formats are available: JSON Resume, Markdown, LinkedIn plain text, and DOCX.

### 9.1 JSON Resume

Export to the [JSON Resume](https://jsonresume.org) standard for job boards and tools:

```bash
uv run cvloom export --format json-resume
uv run cvloom export --profile backend-role --format json-resume --output resume.json
```

Output: `dist/<profile>.resume.json`

### 9.2 Markdown

Export as a clean Markdown document (useful for pasting into READMEs or markdown-based job sites):

```bash
uv run cvloom export --format markdown
```

Output: `dist/<profile>.resume.md`

Sections are ordered by your profile's `section_order`. Sections with `show: false` are omitted.

### 9.3 LinkedIn plain text

Generate copy-paste-ready plain text structured for LinkedIn sections (About, Experience, Skills):

```bash
uv run cvloom export --format linkedin
```

Output: `dist/<profile>.linkedin.txt`

If your summary exceeds LinkedIn's 2600-character About limit, a warning is printed:

```
✓ LinkedIn → dist/general.linkedin.txt
⚠  About section is 2743 chars (LinkedIn limit: 2600)
```

Paste the file into LinkedIn's About, Experience, and Skills sections individually.

### 9.4 DOCX (Word document)

Export as a `.docx` file using Word styles (Heading 1/2, List Bullet, Body Text):

```bash
# Install the optional dependency first
uv pip install python-docx
# or if you have the docx extra:
uv sync --extra docx

uv run cvloom export --format docx
```

Output: `dist/<profile>.resume.docx`

Open in Word or LibreOffice to verify heading styles and adjust formatting as needed.

---

## Scenario 10: Cover Letters

cvloom can generate cover letters using the same data pipeline.

### 10.1 Create a cover letter profile

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

### 10.2 Build the cover letter

```bash
uv run cvloom build --profile datastream-letter
```

Open `dist/datastream-cover-letter.html` to review. The cover letter template uses your contact info and the `job_context` fields to produce a formatted letter.

Available cover letter templates:
- `cover-letter/standard` — full formal cover letter
- `cover-letter/brief` — compact, one-paragraph format

---

## Scenario 11: MCP Server

> **Optional** — requires an MCP-compatible client (Claude Desktop, Claude Code).

cvloom ships an MCP server that lets AI assistants build CVs, create profiles, validate data, and more — all through a structured tool interface.

### 11.1 Install the MCP extra

```bash
uv sync --extra mcp
```

### 11.2 Connect to a client

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

The MCP server exposes 16 tools: 12 core tools (`list_profiles`, `list_projects`, `get_section`, `build_cv`, `create_profile`, `upsert_project`, `validate_data`, `export_json_resume`, `check_cv`, `trim_report`, `diff_profiles`, `match_jd`) plus 4 AI tools (`ai_review_cv`, `ai_generate_cover`, `ai_suggest_improvements`, `ai_align_to_jd`) that require `--extra ai`.

For the full tool reference and example workflows, see [MCP Server](../reference/mcp-server.md).

---

## Scenario 12: PII Safety and GitHub Pages

### 12.1 How PII is protected

Your real contact info lives in `private/contact.yaml`, which is gitignored. The pre-commit hook (installed by `cvloom init`) scans staged files for email addresses and phone numbers. If it finds a match outside `private/`, the commit is blocked.

Two build modes keep your data safe:

| Flag | Contact data | Use case |
|------|-------------|----------|
| *(default)* | `private/contact.yaml` — full contact info | Local builds for applications |
| `--public` | Real data with `email` and `phone` removed | CI, GitHub Pages, sharing |

In `--public` mode all other fields (name, location, website, linkedin, github) are shown as-is. If you want a different display name for public artifacts, add an optional `public_name` field to `private/contact.yaml` — it will replace `name` in public builds only.

### 12.2 GitHub Pages deployment

You can publish a public CV (with placeholder contact) automatically:

1. Go to **Settings > Pages > Source** and select **GitHub Actions**.
2. The workflow at `.github/workflows/build.yml` runs `cvloom build --public` on push to `main`.
3. Your CV is available at `https://<username>.github.io/<repo>/`.

For full setup instructions, see [GitHub Pages Setup](github-pages-setup.md) and [PII Safety](pii-safety.md).

---

## Scenario 13: AI-Powered Analysis

> **Optional** — requires installing the `ai` extra and configuring an AI provider.

cvloom includes four AI-powered commands that go beyond the rules-based tools: section scoring, cover letter generation, content improvement suggestions, and qualitative JD alignment.

### 13.1 Install and configure

```bash
uv sync --extra ai
```

Set your provider environment variables — only `CVLOOM_AI_BASE_URL` is required:

```bash
# Local model via Ollama (free, no internet required for inference)
export CVLOOM_AI_BASE_URL=http://localhost:11434/v1
export CVLOOM_AI_API_KEY=ollama
export CVLOOM_AI_MODEL=gemma3:27b

# Or OpenAI
export CVLOOM_AI_BASE_URL=https://api.openai.com/v1
export CVLOOM_AI_API_KEY=sk-...
export CVLOOM_AI_MODEL=gpt-4o
```

Verify your setup:

```bash
uv run cvloom ai config
```

### 13.2 Score your CV sections

```bash
uv run cvloom ai review --profile general
```

Each visible section gets a 1–10 score with specific strengths, weaknesses, and improvement suggestions. The overall score and top-3 highest-impact priorities are shown at the end.

### 13.3 Get improvement suggestions

```bash
uv run cvloom ai suggest --profile backend-role --role "Senior Platform Engineer"
```

Returns specific bullets to add, skills to include, and rewordings to consider for the target role. Suggestions are ideas — apply them manually to your YAML files.

### 13.4 Generate a cover letter

```bash
uv run cvloom ai cover --profile backend-role --jd jd-backend.txt --output cover.md
```

Generates a tailored cover letter using your CV content and the job description. If `job_context` is set in the profile (company, role, hiring_manager), the letter is personalised automatically.

### 13.5 Analyse JD alignment

```bash
uv run cvloom ai align --profile backend-role --jd jd-backend.txt
```

Goes beyond keyword coverage to assess how your CV is *positioned* for the role — tone, framing, and narrative gaps. Shows strengths, tone gaps, and concrete repositioning actions.

For full backend setup (Ollama, LiteLLM, OpenAI), configuration options, and detailed command output examples, see [AI Features](ai-features.md).

---

## Upgrading cvloom

When a new version of cvloom is released, your project data files are never touched — they live in `data/`, `profiles/`, and `private/`, which the tool only writes when they do not already exist. The upgrade process is two steps:

### Step 1 — Update the package

```bash
# If installed globally with uv tool:
uv tool upgrade cvloom

# If it is a dependency in your own pyproject.toml:
uv lock --upgrade-package cvloom && uv sync
```

### Step 2 — Refresh the pre-commit hook

The pre-commit hook is the only file that `cvloom init` always rewrites. Run `init` from your project directory to pick up any changes to it:

```bash
cd my-cv
cvloom init
```

All existing files are skipped:

```
  data/basics.yaml already exists, skipping
  data/work.yaml already exists, skipping
  ...
  private/contact.yaml already exists, skipping
✓ Pre-commit hook installed
```

### What is safe and what to check

| What | Safe to ignore | When to act |
|------|---------------|-------------|
| `data/`, `profiles/`, `private/` | Always — init skips them | Never |
| Pre-commit hook | Refresh with `cvloom init` | Every upgrade |
| YAML schema changes | Check [CHANGELOG](../../CHANGELOG.md) | Only if `[breaking]` tag appears |

If the CHANGELOG lists a breaking schema change (e.g. a field was renamed), update the affected files in `data/` or `profiles/` manually before running a build.

---

## Next Steps

You have now used every major feature of cvloom. Here are some things to explore next:

- **Create more profiles** for different roles — each one takes minutes once your base data is complete.
- **Add more projects** in `data/projects/` — one YAML file per project.
- **Customize templates** — put custom Jinja2 templates in `templates/` at your project root. See [Custom Templates](../dev/custom-templates.md).
- **Automate with CI** — use `--public --skip-pdf` for fast HTML-only builds in GitHub Actions.

### Reference Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](cli-reference.md) | Every command, flag, and option |
| [User Guide](user-guide.md) | Complete config and features manual |
| [Profiles and Overlays](../reference/profiles-and-overlays.md) | Deep dive into the profile and overlay system |
| [Writing Lint Rules](../reference/ats-linter-rules.md) | Full rule reference with categories and examples |
| [ATS-readiness model](../reference/ats-readiness.md) | The three honest axes; why there is no single "ATS score" |
| [MCP Server](../reference/mcp-server.md) | MCP tool reference and workflow examples |
| [AI Features](ai-features.md) | Full AI command and backend guide |
| [PII Safety](pii-safety.md) | How contact data is protected |
| [GitHub Pages Setup](github-pages-setup.md) | Automated public CV deployment |
