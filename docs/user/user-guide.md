# User Guide

[Back to README](../../README.md)

This guide covers everything you need to know to use cvloom effectively: data file schemas, all profile keys, templates, export formats, and environment configuration. Use it as a reference alongside the [Getting Started tutorial](getting-started.md).

---

## Table of Contents

1. [Data Files](#data-files)
   - [basics.yaml](#basicsyaml)
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
6. [Lint Integration](#lint-integration)
7. [Environment Variables](#environment-variables)

---

## Data Files

All content files live in `data/` (committed to git, no PII). Private contact info lives in `private/contact.yaml` (gitignored).

`basics.yaml`, `work.yaml`, `education.yaml`, `skills.yaml` and `projects/` are the core
set. `publications.yaml`, `certifications.yaml`, `awards.yaml` and `languages.yaml` are
**opt-in** — omit the file entirely and the section simply doesn't render, with no warning.

Every list section supports `tags` for [profile filtering](../reference/profiles-and-overlays.md).

### basics.yaml

Controls your headline, summary, and profile links.

```yaml
headline: "Senior Backend Engineer"       # required
summary: >                                 # optional, 20–80 words recommended
  Backend engineer with 7+ years ...

links:                                     # optional, shown in CV header
  - label: LinkedIn
    url: https://linkedin.com/in/username
  - label: GitHub
    url: https://github.com/username
  - label: Website
    url: https://username.dev
```

| Field | Required | Description |
|---|---|---|
| `headline` | Yes | Your professional title |
| `summary` | No | 1–3 sentence professional summary |
| `links` | No | Profile links shown in the CV header (label + full URL pairs) |

Links live here, not in `private/contact.yaml`, because a LinkedIn or GitHub URL
is public by definition. Keeping them in committed `data/` means they render
identically in private and `--public` builds. Write the full URL — cvloom
recognises LinkedIn and GitHub by their host, so no handle field is needed.

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
and short courses, rendered compactly by every CV template — a title row plus
one meta line, with no bullet list, unlike the fuller treatment education
entries get.

```yaml
- name: "AWS Certified Solutions Architect – Associate"  # required
  issuer: "Amazon Web Services"                          # optional
  type: certification                                    # optional — see below
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
| `type` | No | `certification`, `license`, `course`, or `micro-credential`. Defaults to `certification` |
| `date` | No | Date earned — `YYYY` or `YYYY-MM` |
| `expiry_date` | No | Expiry date, if the credential expires |
| `identifier` | No | Credential or licence ID |
| `url` | No | Verification link |
| `tags` | No | Used for profile filtering (untagged entries are always included) |

#### Credentials vs coursework

`type` decides which heading an entry renders under. Exam-backed credentials
(`certification`, `license`) group under **Certifications**; completion records
(`course`, `micro-credential`) group under **Professional Development**.
Credentials render first, and a group with no entries is omitted entirely — so
a file of nothing but courses gets an accurate heading rather than one claiming
they are certifications.

Omitting `type` means `certification`, so files written before the field
existed render exactly as they did.

The vocabulary follows [Open Badges 3.0](https://www.imsglobal.org/spec/ob/v3p0)'s
`achievementType`, and the credential/coursework split is the same line LinkedIn
draws between its *Licenses & Certifications* and *Courses* sections — which is
what lets an export route each entry to the right one.

Exports to JSON Resume's native `certificates` array. That object is only
`{name, date, issuer, url}`, so `type`, `expiry_date` and `identifier` are
carried as [namespaced extensions](#json-resume-conformance-and-extensions) —
they survive a cvloom round-trip and are ignored by other JSON Resume tools.

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
public_name: "Jane S."                    # optional — replaces name in --public builds
```

This file holds identity and reachability only. Profile links (LinkedIn, GitHub,
your website) go in [`data/basics.yaml`](#basicsyaml) under `links`.

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Full name shown in CV header |
| `email` | No | Contact email |
| `phone` | No | Contact phone |
| `location` | No | City/region |
| `public_name` | No | Alternative name for `--public` builds |

---

## Profile Keys Reference

Profiles live in `profiles/*.yaml`. All keys except `template` are optional.

| Key | Default | Description |
|---|---|---|
| `template` | *(required)* | Template path, e.g. `cv/ats-single` |
| `output_filename` | Profile name | Base name for output files (without extension) |
| `pdf_filename_format` | `{first}_{last}_Resume_{profile}.pdf` | PDF filename override. `{first}`/`{last}`/`{name}` come from contact name; `{profile}` is the profile name |
| `sections` | All `true` | Map of `section_name: true/false` to show or hide sections |
| `include_tags` | `[]` (all) | Only include data entries whose `tags` overlap with this list |
| `include_entries` | — | Force-include specific entries excluded by tag filtering |
| `section_order` | `[skills, work, education, projects, publications, certifications, awards, languages]` | Override the rendering order of sections |
| `job_context` | — | Metadata for cover letter templates and AI commands (`company`, `role`, `hiring_manager`, `notes`) |
| `overlays` | — | Per-job data patches; see [Profiles and Overlays](../reference/profiles-and-overlays.md) |

---

## Templates

### CV templates

| Template | Layout | Parse safety | Description |
|---|---|:--:|---|
| `cv/ats-single` | single-column | ✅ safest | ATS-optimised single-column. No web fonts. Best for maximum ATS compatibility. |
| `cv/modern-single` | single-column | ✅ safe | Single-column with accent color, skill level bars, and Inter font. |
| `cv/executive-dark` | single-column | ✅ safe | Bold typographic hierarchy with dark headings. Good for senior roles. |
| `cv/academic` | single-column | ✅ safe | Education-first layout. Serif font. Orders publications directly after education and labels projects "Research & Projects". No page-count limit warning. |
| `cv/timeline-clean` | two-column grid | ⚠️ check | Timeline-style work history with Roboto font. |
| `cv/sidebar-compact` | sidebar + main | ⚠️ check | Two-column with sidebar. Compact — fits more on one page. |

#### On the parse-safety column

Multi-column layouts are the one formatting choice with a well-supported effect on résumé
parsing: parsers walk the document in source order, not visual order, so content laid out
side by side can be interleaved or attributed to the wrong section. The two ⚠️ templates
place content in CSS grid columns; the ✅ templates keep one column throughout.

This is a *risk* flag, not a prohibition — parser behaviour varies, and a two-column CV is
perfectly reasonable when a human is the primary reader (a referral, a portfolio site, a
conference handout). If you are applying through an unknown ATS, prefer a ✅ template, or
build both and send the single-column one.

What cvloom does **not** do in any template, because these break parsing much harder than
columns: `<table>` layout, text in headers/footers, or text baked into images.

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

## Lint Integration

Two flags run the writing lint as part of the build:

| Flag | Effect |
|---|---|
| `--check` | Runs all 22 lint rules after build and prints a per-axis breakdown |
| `--strict N` | Same as `--check`, plus exits with code 1 if there are more than N findings |

cvloom deliberately prints no single "ATS score" — the breakdown is per axis
(`writing` / `structure` / `ats-parse`). See
[the ATS-readiness model](../reference/ats-readiness.md) for why.

`--strict N` is a **findings budget**, not a quality threshold: `--strict 0` fails the
build on any finding at all, and `--strict 10` tolerates up to ten. Use it in CI to stop
a regression from shipping.

---

## Environment Variables

AI commands use three environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `CVLOOM_AI_BASE_URL` | Yes | — | Base URL of the OpenAI-compatible API endpoint |
| `CVLOOM_AI_API_KEY` | No | `"not-set"` | API key for the provider |
| `CVLOOM_AI_MODEL` | No | `"gpt-4o"` | Model identifier |

See [AI Features](ai-features.md) for provider-specific setup (Ollama, LiteLLM, OpenAI).
