# CLI Command Reference

[Back to README](../../README.md)

This document covers every `cvloom` command, its options, and realistic usage examples.

All commands assume you are in a cvloom project directory (one created by `cvloom init` or following the expected [directory structure](../../README.md#directory-structure)).

---

## Table of Contents

- [build](#build)
- [check](#check)
- [trim](#trim)
- [diff](#diff)
- [match](#match)
- [export](#export)
- [import](#import)
- [init](#init)
- [sync](#sync)
- [list-projects](#list-projects)
- [list-profiles](#list-profiles)
- [ai](#ai)

---

## `build`

Resolve a profile, render HTML, and optionally generate a PDF.

```bash
cvloom build [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--profile` | `-p` | `general` | Profile name (without `.yaml` extension) |
| `--template` | `-t` | *(from profile)* | Override the template (e.g. `cv/modern-single`) |
| `--output-dir` | `-o` | `dist` | Output directory for generated files |
| `--public` | | off | Use placeholder contact data (safe for CI / GitHub Pages) |
| `--skip-pdf` | | off | Skip PDF generation; produce HTML only |
| `--check` | | off | Run the writing lint after build and print a per-axis breakdown |
| `--strict N` | | off | Exit non-zero if more than N lint findings (implies `--check`) |

### Examples

```bash
# Build the default "general" profile with real contact data
cvloom build

# Build a tailored profile for a specific role
cvloom build --profile backend-role

# Build for GitHub Pages (placeholder contact, no PDF)
cvloom build --public --skip-pdf

# Override the template at build time
cvloom build --profile backend-role --template cv/modern-single

# Write output to a custom directory
cvloom build --profile backend-role --output-dir out/

# Build and show the writing-lint breakdown inline
cvloom build --profile backend-role --check

# Build and fail CI if there are more than 10 lint findings
cvloom build --profile backend-role --strict 10
```

### Sample Output

```
Profile:   backend-role
Template:  cv/ats-single
HTML:      dist/backend-role.html
PDF:       dist/backend-role.pdf
Words:     482
Pages:     ~1
Sections:  work (3 entries), education (2), skills (4 categories), projects (2)
```

If the estimated page count exceeds 2 on a non-academic template, a warning is printed:

```
WARNING: Estimated 3 pages — consider trimming (run `cvloom trim`).
```

---

## `check`

Run the writing lint against a resolved profile and report issues, grouped into three
honest axes (`writing`, `structure`, `ats-parse`). No single "ATS score" — see the
[ATS-readiness model](../reference/ats-readiness.md).

```bash
cvloom check [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--profile` | `-p` | `general` | Profile name (without `.yaml` extension) |

### Lint Rules

17 built-in rules (see [ats-linter-rules.md](../reference/ats-linter-rules.md) for full details):

| Rule | Severity | What it catches |
|---|---|---|
| `wl-001` | warning | Passive voice in highlights |
| `wl-002` | warning | Missing quantification (no numbers/metrics) |
| `wl-003` | warning | Noise skills (commodity office tools) |
| `wl-004` | warning | Weak action verbs |
| `wl-005` | warning | Highlight length outside 8-25 word range |
| `wl-006` | warning | Too few or too many highlights per work entry |
| `wl-007` | warning | First-person pronouns (I/my/me) |
| `wl-008` | warning | Vague buzzwords (motivated, proactive, …) |
| `wl-009` | warning | Fewer than 8 or more than 25 total skills |
| `wl-010` | warning | No LinkedIn or GitHub link present |
| `wl-011` | warning | Estimated page count exceeds 2 |
| `wl-012` | warning | Mixed YYYY-MM / YYYY date formats |
| `wl-013` | warning | Wrong tense for current vs past roles |
| `wl-014` | warning | Summary shorter than 20 or longer than 80 words |
| `wl-015` | suggestion | Metric present but no result-framing phrase |
| `wl-016` | suggestion | Flesch-Kincaid grade level outside 6–12 |
| `wl-017` | suggestion | Work entry mentions no skill item in highlights |

### Examples

```bash
# Lint the default profile
cvloom check

# Lint a specific profile
cvloom check --profile backend-role
```

### Sample Output

```
Rule     Section   Entry          Message                        Fix
───────  ────────  ─────────────  ─────────────────────────────  ──────────────────────────
wl-001  work      Acme Corp      "Was responsible for..."       Use active voice
wl-002  work      Acme Corp      "Improved performance"         Add a metric (%, $, time)
wl-004  work      Initech        "Helped build the platform"    Replace with strong verb
wl-005  work      Initech        Highlight is 4 words (min 8)   Expand with details

4 issues found.
```

Exit code is `1` if any issues are found, `0` if clean.

---

## `trim`

Analyse word counts per section and recommend cuts to hit a page target.

```bash
cvloom trim [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--profile` | `-p` | `general` | Profile name (without `.yaml` extension) |
| `--target-pages` | | `1` | Target page count |

### Examples

```bash
# Analyse the default profile (targeting 1 page)
cvloom trim

# Target 2 pages for an academic CV
cvloom trim --profile academic --target-pages 2
```

### Sample Output

```
Section      Words   Entries
───────────  ──────  ───────
work           312        3
education       87        2
skills          45        4
projects        68        2
───────────  ──────  ───────
Total          512
Estimated    ~1.2 pages
Target       1 page
To cut       ~90 words

Recommendations:
  - work / Acme Corp: 142 words (largest entry — trim first)
  - work / Initech: 18 words/bullet avg (consider tightening)
  - skills: 4 categories — consider dropping lowest-relevance category
```

---

## `diff`

Compare two profiles side by side.

```bash
cvloom diff PROFILE_A PROFILE_B
```

Both arguments are positional profile names (without `.yaml`).

### Examples

```bash
# Compare your general profile against a tailored one
cvloom diff general backend-role
```

### Sample Output

```
                general          backend-role
Template:       cv/ats-single    cv/modern-single
Words:          512              387 (-125)

Sections only in general:
  - certifications

Sections only in backend-role:
  (none)

Entries only in general:
  - projects / Personal Blog

Entries only in backend-role:
  - projects / Kafka Pipeline

Highlight counts:
  work:       12 → 9 (-3)
  projects:    4 → 5 (+1)
```

---

## `match`

Compare CV keywords against a plain-text job description to identify gaps.

```bash
cvloom match --jd job-description.txt
cvloom match --jd jd.txt --profile backend-role
```

### Options

| Option | Default | Description |
|---|---|---|
| `--jd PATH` | *(required)* | Path to a plain-text job description file |
| `--profile`, `-p` | `general` | Build profile to resolve before matching |

### Output

- **Coverage percentage** — ratio of JD keywords found in the CV
- **Top JD Keywords table** — most frequent keywords with CV presence and sections
- **Gaps list** — keywords from the JD not found anywhere in the CV
- **Reorder suggestions** — recommends moving the most JD-relevant work entry to the top

### Example

```
$ cvloom match --jd stripe-infra.txt --profile backend-role
Coverage: 72% (18 of 25 JD keywords found)
JD keyword count: 84

  Top JD Keywords
  ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┓
  ┃ Keyword        ┃ JD Freq ┃ In CV ┃ CV Sections   ┃
  ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━┩
  │ python         │       5 │   ✓   │ skills, work  │
  │ infrastructure │       3 │   ✓   │ work          │
  │ kubernetes     │       3 │   ✗   │               │
  │ distributed    │       2 │   ✓   │ work          │
  └────────────────┴─────────┴───────┴───────────────┘

Gaps (7):
  ✗ kubernetes  → add to skills
  ✗ terraform   → add to skills
  ✗ grafana     → add to work

Reorder Suggestions
  ↕  Work: move 'SRE at Stripe' before 'Engineer at Initech' (5 vs 1 JD keyword matches)
```

### How it works

1. The profile is resolved (same pipeline as `build`)
2. The JD file is tokenised into keywords (stop words removed)
3. CV content from all visible sections is tokenised
4. Keywords are classified as matched (in CV) or gap (missing)
5. Results are sorted by JD frequency — most important gaps first
6. Reorder suggestions compare work entry keyword overlap and recommend moving the most JD-relevant role to the top

---

## `export`

Export a resolved profile to an external schema.

```bash
cvloom export [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--profile` | `-p` | `general` | Profile name (without `.yaml` extension) |
| `--format` | | *(required)* | Export format: `json-resume`, `markdown`, `linkedin`, `docx` |
| `--output` | `-o` | *(inferred)* | Output file path (inferred from profile and format if omitted) |

### Default output paths

| Format | Default path |
|---|---|
| `json-resume` | `dist/<profile>.resume.json` |
| `markdown` | `dist/<profile>.resume.md` |
| `linkedin` | `dist/<profile>.linkedin.txt` |
| `docx` | `dist/<profile>.resume.docx` |

### Examples

```bash
# Export default profile to JSON Resume
cvloom export --format json-resume

# Export as Markdown
cvloom export --format markdown

# Export LinkedIn-pasteable plain text (warns if About > 2600 chars)
cvloom export --format linkedin

# Export as Word document (requires python-docx: uv pip install python-docx)
cvloom export --format docx

# Specific profile to a custom path
cvloom export --profile backend-role --format markdown --output resume.md
```

---

## `import`

Import an external resume into cvloom's `data/` + `private/` layout. The inverse of
`export` — it lets users of the [JSON Resume](https://jsonresume.org/) standard migrate in
one command.

```bash
cvloom import [OPTIONS] SOURCE
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--format` | `json-resume` | Source format (currently only `json-resume`) |
| `--dry-run` | *(off)* | Print the files that would be written, without writing anything |
| `--force` | *(off)* | Overwrite existing `data/`/`private/` files (refuses otherwise) |

### PII split

Contact details are **never** written to `data/`. `import` routes them to
`private/contact.yaml` (gitignored), matching cvloom's PII compartmentalization:

| JSON Resume field | Written to |
|---|---|
| `basics.name` / `email` / `phone` / `url` / `location` | `private/contact.yaml` |
| `basics.profiles` (LinkedIn, GitHub) | `private/contact.yaml` |
| `basics.label` → `headline`, `basics.summary` | `data/basics.yaml` |
| `work`, `education`, `skills` | `data/*.yaml` |
| `projects[]` | `data/projects/<slug>.yaml` |

The imported data is schema-validated before anything is written; a malformed source or one
that produces invalid data exits non-zero with the errors listed.

### Examples

```bash
# Preview what would be written
cvloom import resume.json --dry-run

# Import (refuses if data/ or private/ files already exist)
cvloom import resume.json

# Overwrite existing files
cvloom import resume.json --force
```

---

## `init`

Scaffold a new cvloom project in the current directory.

```bash
cvloom init [OPTIONS]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--force` | off | Overwrite existing files if they already exist |

### What it creates

```
.
├── .gitignore
├── data/
│   ├── basics.yaml
│   ├── work.yaml
│   ├── education.yaml
│   ├── skills.yaml
│   └── projects/
│       └── example-project.yaml
├── profiles/
│   ├── general.yaml
│   └── cover-letter.yaml
├── private/
│   └── contact.yaml
└── .github/
    └── workflows/
        └── publish-cv.yml
```

It also installs the pre-commit PII hook (see [PII Safety](pii-safety.md)) and scaffolds the
GitHub Pages [publish workflow](github-pages-setup.md). Both are *managed files* — refresh them
after a tool upgrade with [`cvloom sync`](#sync).

### Examples

```bash
# Scaffold a fresh project
mkdir my-cv && cd my-cv
cvloom init

# Re-scaffold, overwriting existing files
cvloom init --force
```

---

## `sync`

Refresh cvloom-managed scaffold files (the pre-commit hook and the Pages publish workflow) to the
versions shipped in the installed package. Run it after `uv tool upgrade cvloom`. See
[Keeping your instance updated](keeping-updated.md).

```bash
cvloom sync [OPTIONS]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--force` | off | Overwrite out-of-date / missing managed files (otherwise only reports status) |

### Behaviour

Without `--force`, `sync` byte-compares each managed file against the packaged version and reports
`up to date` / `out of date` / `missing`, writing nothing. With `--force` it overwrites the
out-of-date and missing ones. Review the result with `git diff` after a forced sync.

```bash
cvloom sync            # report status only
cvloom sync --force    # apply updates
```

---

## `list-projects`

List all projects found in `data/projects/`.

```bash
cvloom list-projects [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--tag` | `-t` | *(all)* | Filter by tag (can be specified multiple times) |

### Examples

```bash
# List all projects
cvloom list-projects

# Filter by one or more tags
cvloom list-projects --tag python
cvloom list-projects --tag python --tag aws
```

### Sample Output

```
Name               Tags                Description
─────────────────  ──────────────────  ──────────────────────────────────────
Kafka Pipeline     python, kafka, aws  Real-time event processing pipeline...
Personal Blog      typescript, react   Portfolio site built with Next.js a...
CLI Tool           python, click       Developer productivity tool for man...
```

---

## `list-profiles`

List all profiles found in `profiles/`.

```bash
cvloom list-profiles
```

This command takes no options.

### Sample Output

```
Profile         Template                Output              Tags               Job Context
──────────────  ──────────────────────  ──────────────────  ─────────────────  ──────────────────
general         cv/ats-single           cv                  —                  —
backend-role    cv/ats-single           jane-smith-backend  python, kafka      Acme Corp / Staff Engineer
academic        cv/academic             academic-cv         research           —
cover-letter    cover-letter/standard   cover-letter        —                  Acme Corp / Staff Engineer
```

---

## `ai`

AI-powered analysis commands. Require `uv sync --extra ai` and `CVLOOM_AI_BASE_URL` to be set.

```bash
cvloom ai config                                              # check provider status
cvloom ai review --profile NAME                              # score CV sections
cvloom ai cover --profile NAME --jd FILE [--output FILE]     # generate cover letter
cvloom ai suggest --profile NAME [--role "Role Title"]       # improvement suggestions
cvloom ai align --profile NAME --jd FILE                     # qualitative JD alignment
```

See [AI Features](ai-features.md) for setup, backends, and command details.
