# CLI Command Reference

[Back to README](../README.md)

This document covers every `cvloom` command, its options, and realistic usage examples.

All commands assume you are in a cvloom project directory (one created by `cvloom init` or following the expected [directory structure](../README.md#directory-structure)).

---

## Table of Contents

- [build](#build)
- [check](#check)
- [trim](#trim)
- [diff](#diff)
- [match](#match)
- [export](#export)
- [init](#init)
- [list-projects](#list-projects)
- [list-profiles](#list-profiles)

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

Run the ATS linter against a resolved profile and report issues.

```bash
cvloom check [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--profile` | `-p` | `general` | Profile name (without `.yaml` extension) |

### ATS Rules

| Rule | What it catches |
|---|---|
| `ats-001` | Passive voice in highlights |
| `ats-002` | Missing quantification (no numbers/metrics) |
| `ats-003` | Noise skills (too vague to be useful) |
| `ats-004` | Weak action verbs |
| `ats-005` | Highlight length outside 8-25 word range |

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
ats-001  work      Acme Corp      "Was responsible for..."       Use active voice
ats-002  work      Acme Corp      "Improved performance"         Add a metric (%, $, time)
ats-004  work      Initech        "Helped build the platform"    Replace with strong verb
ats-005  work      Initech        Highlight is 4 words (min 8)   Expand with details

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
  ✗ kubernetes
  ✗ terraform
  ✗ grafana
```

### How it works

1. The profile is resolved (same pipeline as `build`)
2. The JD file is tokenised into keywords (stop words removed)
3. CV content from all visible sections is tokenised
4. Keywords are classified as matched (in CV) or gap (missing)
5. Results are sorted by JD frequency — most important gaps first

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
| `--format` | | *(required)* | Export format (currently: `json-resume`) |
| `--output` | `-o` | `dist/<profile>.resume.json` | Output file path |

### Examples

```bash
# Export default profile to JSON Resume
cvloom export --format json-resume

# Export a specific profile to a custom path
cvloom export --profile backend-role --format json-resume --output resume.json
```

### Sample Output

```
Exported backend-role → dist/backend-role.resume.json (JSON Resume v1.0.0)
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
└── private/
    └── contact.yaml
```

It also installs the pre-commit PII hook (see [PII Safety](pii-safety.md)).

### Examples

```bash
# Scaffold a fresh project
mkdir my-cv && cd my-cv
cvloom init

# Re-scaffold, overwriting existing files
cvloom init --force
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

### Example

```bash
cvloom list-profiles
```

### Sample Output

```
Profile         Template                Output              Tags               Job Context
──────────────  ──────────────────────  ──────────────────  ─────────────────  ──────────────────
general         cv/ats-single           cv                  —                  —
backend-role    cv/ats-single           jane-smith-backend  python, kafka      Acme Corp / Staff Engineer
academic        cv/academic             academic-cv         research           —
cover-letter    cover-letter/standard   cover-letter        —                  Acme Corp / Staff Engineer
```
