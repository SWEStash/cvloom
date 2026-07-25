# User Guide

[Back to README](../../README.md)

This guide covers everything you need to know to use cvloom effectively: data file schemas, all profile keys, templates, export formats, and environment configuration. Use it as a reference alongside the [Getting Started tutorial](getting-started.md).

---

## Table of Contents

1. [Data Files](#data-files)
   - [basics.yaml](#basicyaml)
   - [work.yaml](#workyaml)
   - [education.yaml](#educationyaml)
   - [skills.yaml](#skillsyaml)
   - [projects/*.yaml](#projectsyaml)
   - [publications.yaml](#publicationsyaml)
   - [certifications.yaml](#certificationsyaml)
   - [awards.yaml](#awardsyaml)
   - [languages.yaml](#languagesyaml)
   - [private/contact.yaml](#privatecontactyaml)
2. [Profile Keys Reference](#profile-keys-reference)
3. [Templates](#templates)
4. [Export Formats](#export-formats)
5. [Build Modes](#build-modes)
6. [ATS Scoring](#ats-scoring)
7. [Environment Variables](#environment-variables)

---

## Data Files

All content files live in `data/` (committed to git, no PII). Private contact info lives in `private/contact.yaml` (gitignored).

`basics.yaml`, `work.yaml`, `education.yaml`, `skills.yaml` and `projects/` are the core
set. `publications.yaml`, `certifications.yaml`, `awards.yaml` and `languages.yaml` are
**opt-in** — omit the file entirely and the section simply doesn't render, with no warning.

Every list section supports `tags` for [profile filtering](../reference/profiles-and-overlays.md).

### basics.yaml

Controls your headline, summary, and public links.

```yaml
headline: "Senior Backend Engineer"       # required
summary: >                                 # optional, 20–80 words recommended
  Backend engineer with 7+ years ...

public_links:                              # optional, shown in CV header
  - label: GitHub
    url: https://github.com/username
  - label: Website
    url: https://username.dev
```

| Field | Required | Description |
|---|---|---|
| `headline` | Yes | Your professional title |
| `summary` | No | 1–3 sentence professional summary |
| `public_links` | No | Links shown in the CV header (label + url pairs) |

---

### work.yaml

A list of work experience entries.

```yaml
- company: Acme Corp                       # required
  title: Senior Backend Engineer           # required
  location: Remote                         # optional
  start_date: "2021-03"                    # required (YYYY-MM or YYYY)
  end_date: Present                        # optional; omit or "Present" for current role
  highlights:                              # optional list of bullets
    - id: kafka-pipeline                   # optional ID for overlay targeting
      text: "Built real-time pipeline..."
    - "Plain string bullet — no ID"
  tags: [python, kafka, aws]              # optional; used for profile filtering
```

| Field | Required | Description |
|---|---|---|
| `company` | Yes | Company name |
| `title` | Yes | Job title |
| `location` | No | Office location or "Remote" |
| `start_date` | Yes | `YYYY-MM` or `YYYY` |
| `end_date` | No | `YYYY-MM`, `YYYY`, or `"Present"` |
| `highlights` | No | Bullet points; plain strings or `{id, text}` objects |
| `tags` | No | Used for profile `include_tags` filtering |

**Highlight IDs** — give highlights an `id` if you want to target them in overlay `pick`, `exclude`, or `replace` operations. Plain strings work but cannot be individually addressed.

Work entries without `tags` are always included regardless of profile filtering.

---

### education.yaml

A list of education entries.

```yaml
- institution: State University            # required
  degree: "Bachelor of Science"            # required
  field: Computer Science                  # optional
  location: "Anytown, USA"                # optional
  start_date: "2014"                       # required
  end_date: "2018"                         # optional
  highlights:                              # optional
    - "GPA 3.8/4.0"
  tags: [research]                         # optional
```

| Field | Required | Description |
|---|---|---|
| `institution` | Yes | University or school name |
| `degree` | Yes | Degree type |
| `field` | No | Field of study |
| `location` | No | City or country |
| `start_date` | Yes | `YYYY-MM` or `YYYY` |
| `end_date` | No | `YYYY-MM`, `YYYY`, or `"Present"` |
| `grade` | No | GPA or classification |
| `highlights` | No | Notable achievements, GPA, awards |
| `tags` | No | Used for profile filtering (untagged entries are always included) |

If your education section has grown a long tail of certifications and short
courses, put those in [`certifications.yaml`](#certificationsyaml) instead — they
render compactly as their own section rather than competing with your degrees.
The `wl-018` lint rule flags this once the section passes 6 entries.

---

### skills.yaml

A list of skill categories, each with a list of items.

```yaml
- category: Languages                      # required
  items:                                   # required
    - name: Python                         # string or {name, level} object
      level: expert
    - Go                                   # plain string — no level
```

| Field | Required | Description |
|---|---|---|
| `category` | Yes | Category name (e.g. "Languages", "Cloud") |
| `items` | Yes | List of skill names (strings) or `{name, level}` objects |

**Skill levels** — valid values for `level`: `beginner`, `intermediate`, `advanced`, `expert`. Templates that support skill bars (e.g. `cv/modern-single`) render these as visual indicators.

---

### projects/*.yaml

Each project is a separate YAML file under `data/projects/`.

```yaml
name: portfolio-api                        # required
description: >                             # required
  Open-source REST API framework...
url: https://github.com/user/repo          # optional
start_date: "2023-06"                      # optional
end_date: Present                          # optional
highlights:                                # optional
  - id: stars
    text: "800+ GitHub stars..."
  - "Automated release pipeline..."
tags: [python, fastapi, open-source]       # required
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Project name |
| `description` | Yes | Short description (shown in CV) |
| `tags` | Yes | Used for profile filtering |
| `url` | No | Project URL |
| `start_date` | No | `YYYY-MM` or `YYYY` |
| `end_date` | No | `YYYY-MM`, `YYYY`, or `"Present"` |
| `highlights` | No | Key achievements or features |

---

### publications.yaml

Optional — omit the file entirely if you have no publications. A single list of
papers, articles, or talks, rendered as a **Publications** section by every CV
template.

```yaml
- name: "A model of distributed consensus under churn"   # required
  publisher: "Journal of Systems Research"                              # optional — journal, conference, or publisher
  release_date: "2018"                                  # optional — YYYY or YYYY-MM
  identifier: "ISBN 978-0-0000-0000-1"                  # optional — ISBN, DOI, or arXiv ID
  url: "https://example.com/paper"                      # optional
  summary: "A short summary of the paper." # optional (Markdown supported)
  tags: [research, modeling]                            # optional — used for profile filtering
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Publication title |
| `publisher` | No | Journal, conference, or publisher |
| `release_date` | No | `YYYY` or `YYYY-MM` |
| `identifier` | No | ISBN, DOI, or arXiv ID |
| `url` | No | Link to the publication |
| `summary` | No | Short description (Markdown supported) |
| `tags` | No | Used for profile filtering |

Tag filtering follows `work.yaml` semantics rather than `projects/`: an entry
with **no** `tags` is always included, so `include_tags` never silently drops
untagged publications.

Hide the section for a given profile with `sections: { publications: false }`,
or place it explicitly with `section_order`.

On export to JSON Resume, entries map to the standard `publications` array.
JSON Resume has no ISBN/DOI field, so `identifier` is appended to `summary`
rather than dropped — which means it does not survive a round-trip back into
`identifier` on import.

---

### certifications.yaml

Optional — omit the file entirely if you have none. Certifications, licences,
and short courses, rendered as a compact **Certifications** section by every CV
template — a title row plus one meta line, with no bullet list, unlike the fuller
treatment education entries get.

```yaml
- name: "AWS Certified Solutions Architect – Associate"  # required
  issuer: "Amazon Web Services"                          # optional
  date: "2023-04"                                        # optional — YYYY or YYYY-MM
  expiry_date: "2026-04"                                 # optional
  identifier: "AWS-PSA-12345"                            # optional — credential/licence ID
  url: "https://example.com/verify/12345"                # optional
  tags: [cloud, aws]                                     # optional — profile filtering
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Credential title |
| `issuer` | No | Issuing organisation |
| `date` | No | Date earned — `YYYY` or `YYYY-MM` |
| `expiry_date` | No | Expiry date, if the credential expires |
| `identifier` | No | Credential or licence ID |
| `url` | No | Verification link |
| `tags` | No | Used for profile filtering (untagged entries are always included) |

Exports to JSON Resume's native `certificates` array. That object is only
`{name, date, issuer, url}`, so `expiry_date` and `identifier` are carried as
[namespaced extensions](#json-resume-conformance-and-extensions) — they survive
a cvloom round-trip and are ignored by other JSON Resume tools.

---

### awards.yaml

Optional. Prizes, honours, and recognitions.

```yaml
- title: "Best Paper Award"                  # required
  awarder: "ACM SIGPLAN"                     # optional
  date: "2019"                               # optional — YYYY or YYYY-MM
  summary: "For work on type inference."     # optional (Markdown supported)
  tags: [research]                           # optional — profile filtering
```

| Field | Required | Description |
|---|---|---|
| `title` | Yes | Award name |
| `awarder` | No | Organisation that granted it |
| `date` | No | `YYYY` or `YYYY-MM` |
| `summary` | No | Short description (Markdown supported) |
| `tags` | No | Used for profile filtering (untagged entries are always included) |

Maps to JSON Resume's `awards` array field-for-field.

---

### languages.yaml

Optional. Rendered as a single inline run (`Spanish (Native speaker) · English (C1)`)
rather than a stack of entries, since two short fields per language don't warrant the
vertical space.

```yaml
- language: Spanish                          # required
  fluency: Native speaker                    # optional
- language: English
  fluency: C1                                # a CEFR level reads well here
- language: Portuguese                       # fluency may be omitted entirely
```

| Field | Required | Description |
|---|---|---|
| `language` | Yes | Language name |
| `fluency` | No | Free text — a CEFR level (`C1`) or a description (`Native speaker`) |
| `tags` | No | Used for profile filtering (untagged entries are always included) |

Maps to JSON Resume's `languages` array field-for-field.

---

### private/contact.yaml

Your personal contact info. This file is gitignored and never committed.

```yaml
name: "Jane Smith"                         # required
email: "jane@example.com"                  # optional
phone: "+1 (555) 123-4567"               # optional
location: "San Francisco, CA"             # optional
website: "https://janesmith.dev"          # optional
linkedin: "janesmith"                     # optional handle or full URL
github: "janesmith"                       # optional handle or full URL
public_name: "Jane S."                    # optional — replaces name in --public builds
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Full name shown in CV header |
| `email` | No | Contact email |
| `phone` | No | Contact phone |
| `location` | No | City/region |
| `website` | No | Personal website URL |
| `linkedin` | No | LinkedIn handle or full URL |
| `github` | No | GitHub handle or full URL |
| `public_name` | No | Alternative name for `--public` builds |

---

## Profile Keys Reference

Profiles live in `profiles/*.yaml`. All keys except `template` are optional.

| Key | Default | Description |
|---|---|---|
| `template` | *(required)* | Template path, e.g. `cv/ats-single` |
| `output_filename` | Profile name | Base name for output files (without extension) |
| `pdf_filename_format` | `{first}_{last}_Resume.pdf` | PDF filename override; `{first}` and `{last}` come from contact name |
| `sections` | All `true` | Map of `section_name: true/false` to show or hide sections |
| `include_tags` | `[]` (all) | Only include data entries whose `tags` overlap with this list |
| `include_entries` | — | Force-include specific entries excluded by tag filtering |
| `section_order` | `[skills, work, education, projects, publications, certifications, awards, languages]` | Override the rendering order of sections |
| `job_context` | — | Metadata for cover letter templates and AI commands (`company`, `role`, `hiring_manager`, `notes`) |
| `overlays` | — | Per-job data patches; see [Profiles and Overlays](../reference/profiles-and-overlays.md) |

---

## Templates

### CV templates

| Template | Description |
|---|---|
| `cv/ats-single` | ATS-optimised single-column. No web fonts. Best for maximum ATS compatibility. |
| `cv/modern-single` | Single-column with accent color, skill level bars, and Inter font. |
| `cv/timeline-clean` | Timeline-style work history with Roboto font. |
| `cv/executive-dark` | Bold typographic hierarchy with dark headings. Good for senior roles. |
| `cv/sidebar-compact` | Two-column with sidebar. Compact — fits more on one page. |
| `cv/academic` | Education-first layout. Serif font. Orders publications directly after education and labels projects "Research & Projects". No page-count limit warning. |

### Cover letter templates

| Template | Description |
|---|---|
| `cover-letter/standard` | Professional formal cover letter. Uses `job_context` (company, role, hiring_manager, notes). |
| `cover-letter/brief` | Compact one-paragraph format. Omits boilerplate sign-off. |

### Project summary template

| Template | Description |
|---|---|
| `project-summary/card` | Single-page project summary card. |

### Custom templates

Place custom Jinja2 templates in `templates/` at your project root — cvloom will find them automatically. See [Custom Templates](../dev/custom-templates.md) for how to write them.

---

## Export Formats

| Format | Command | Output path | Use case |
|---|---|---|---|
| `json-resume` | `cvloom export --format json-resume` | `dist/<profile>.resume.json` | Job boards, JSON Resume ecosystem |
| `markdown` | `cvloom export --format markdown` | `dist/<profile>.resume.md` | Markdown-based sites, pasting into docs |
| `linkedin` | `cvloom export --format linkedin` | `dist/<profile>.linkedin.txt` | Copy-paste into LinkedIn About/Experience/Skills |
| `docx` | `cvloom export --format docx` | `dist/<profile>.resume.docx` | Word/LibreOffice, when a `.docx` is required |

The `docx` format requires the optional `python-docx` dependency:

```bash
uv pip install python-docx
# or
uv sync --extra docx
```

The `linkedin` format warns if your About section exceeds LinkedIn's 2600-character limit.

### JSON Resume conformance and extensions

Exported documents are validated against the official JSON Resume schema in CI, so
`json-resume` output is guaranteed to conform. Two consequences worth knowing:

- **Dates must be ISO 8601** (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`). cvloom allows free
  text — most importantly `end_date: Present`. JSON Resume has no such sentinel: a
  current role is expressed by *omitting* `endDate`. Any date that isn't ISO 8601 is
  omitted from the export rather than emitted invalid, so check `wl-012` findings if
  you expect dates to appear.
- **Empty fields are omitted**, not exported as `""`. A `--public` build strips your
  email, and an empty string fails the schema's `email` format.

cvloom carries a few fields JSON Resume has no home for. Rather than drop them, they
are exported under an `x-cvloom-*` namespace, which the schema permits and other tools
ignore. These survive an `export` → `import` round-trip:

| cvloom field | Exported as |
|---|---|
| `tags` on work / education / publications / certifications / awards / languages | `x-cvloom-tags` |
| `expiry_date` on certifications | `x-cvloom-expiry_date` |
| `identifier` on certifications | `x-cvloom-identifier` |
| per-item skill `level` | `x-cvloom-levels` on the skill group |

Project `tags` are *not* namespaced — they map to the spec's own `keywords` field.
Publication `identifier` is folded into `summary`, since a citation reads naturally
that way; it does not split back out on import.

Without this, a round-trip would silently strip the tag taxonomy that
[profile filtering](../reference/profiles-and-overlays.md) depends on — you would get
your content back and quietly lose every profile.

---

## Build Modes

| Flag | Contact data used | When to use |
|---|---|---|
| *(default)* | `private/contact.yaml` — all fields | Local builds for job applications |
| `--public` | All fields except `email` and `phone` | CI, GitHub Pages, sharing links |

In `--public` mode, `email` and `phone` are omitted. All other fields (`name`, `location`, `website`, `linkedin`, `github`) appear as-is. Set `public_name` in `private/contact.yaml` to show a different name in public builds.

---

## ATS Scoring

Two flags integrate ATS scoring into the build:

| Flag | Effect |
|---|---|
| `--check` | Runs all 17 lint rules after build and prints a per-axis breakdown |
| `--strict N` | Same as `--check`, plus exits with code 1 if score < N |

The score is calculated as: `100 - (warnings × 5) - (suggestions × 2)`, floored at 0.

Use `--strict 70` in CI to enforce a minimum quality threshold before deploying.

---

## Environment Variables

AI commands use three environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `CVLOOM_AI_BASE_URL` | Yes | — | Base URL of the OpenAI-compatible API endpoint |
| `CVLOOM_AI_API_KEY` | No | `"not-set"` | API key for the provider |
| `CVLOOM_AI_MODEL` | No | `"gpt-4o"` | Model identifier |

See [AI Features](ai-features.md) for provider-specific setup (Ollama, LiteLLM, OpenAI).
