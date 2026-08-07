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
5. [Project Settings (`cvloom.yaml`)](#project-settings-cvloomyaml)
   - [Where section headings come from](#where-section-headings-come-from)
6. [Build Modes](#build-modes)
7. [Lint Integration](#lint-integration)
8. [Environment Variables](#environment-variables)

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
  # end_date                               # optional; omit for a current role
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
| `end_date` | No | `YYYY-MM` or `YYYY`. Omit for a current role — cvloom supplies your [locale](../reference/locales.md)'s word (`Present` in `en`) |
| `highlights` | No | Bullet points; plain strings or `{id, text}` objects |
| `tags` | No | Used for profile `select` filtering; never rendered |

**Highlight IDs** — give highlights an `id` if you want to target them in overlay `pick`, `exclude`, or `replace` operations. Plain strings work but cannot be individually addressed.

A work entry with no `tags` does not match a `select.work` include list, so it is dropped from profiles that narrow this section. Profiles that do not name `work` under `select` keep every entry.

---

### education.yaml

A list of education entries.

```yaml
- institution: State University            # required
  degree: "Bachelor of Science"            # required
  field: Computer Science                  # optional
  connector: " in "                        # optional — note the quotes and spaces
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
| `connector` | No | Written between `degree` and `field`, verbatim (see below) |
| `location` | No | City or country |
| `start_date` | Yes | `YYYY-MM` or `YYYY` |
| `end_date` | No | `YYYY-MM` or `YYYY`. Omit for a current role — cvloom supplies your [locale](../reference/locales.md)'s word (`Present` in `en`) |
| `grade` | No | GPA or classification |
| `highlights` | No | Notable achievements, GPA, awards |
| `tags` | No | Used for profile `select` filtering; never rendered |

**Joining degree and field.** cvloom supplies no connecting word of its own — the
right one belongs to the entry, not to the tool. Without `connector`, degree and
field join with a single space (`Bachelor of Science Computer Science`). Set it to
whatever the entry needs, and note that it is written **verbatim**, so it carries
its own spacing:

```yaml
connector: " in "     # Bachelor of Science in Computer Science
connector: ", "       # Bachelor of Science, Computer Science
connector: " en "     # Licenciatura en Informática
```

Quote it. Unquoted YAML strips the spaces, so `connector: in` renders
`Bachelor of ScienceinComputer Science` — the `wl-024` lint rule catches exactly that.

`connector` has no equivalent in JSON Resume (which has only `studyType` and
`area`), so it does not survive an `export` → `import` round trip; a reimported
entry falls back to the single space.

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
# end_date                                 # optional; omit for a current role
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
| `end_date` | No | `YYYY-MM` or `YYYY`. Omit for a current role — cvloom supplies your [locale](../reference/locales.md)'s word (`Present` in `en`) |
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
| `tags` | No | Used for profile `select` filtering; never rendered |

Selection is per-section: publications are only narrowed if a profile names
them under `select`. When it does, an entry with **no** `tags` does not match —
cvloom warns when that drops something.

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
| `tags` | No | Used for profile `select` filtering; never rendered |

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
`achievementType`. The credential/coursework split decides which of the two headings
an entry renders under — *Certifications* or *Professional Development*.

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
| `tags` | No | Used for profile `select` filtering; never rendered |

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
| `tags` | No | Used for profile `select` filtering; never rendered |

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
| `template` | *(required)* | Template path, e.g. `cv/ats-clean` |
| `output_filename` | Profile name | Base name for output files (without extension) |
| `pdf_filename_format` | `{first}_{last}_Resume_{profile}.pdf` | PDF filename override. `{first}`/`{last}`/`{name}` come from contact name; `{profile}` is the profile name |
| `sections` | All `true` | Map of `section_name: true/false` to show or hide sections |
| `select` | — | Per-section content selection; see [Selecting Content](../reference/profiles-and-overlays.md#selecting-content) |
| `section_order` | `[work, skills, education, projects, publications, certifications, awards, languages]` | Override the rendering order of sections |
| `section_titles` | The project locale's wording | Rename section headings — text only, styling stays in the template. See [Where section headings come from](#where-section-headings-come-from) |
| `job_context` | — | Metadata for cover letter templates and AI commands (`company`, `role`, `hiring_manager`, `notes`) |
| `overlays` | — | Per-job data patches; see [Profiles and Overlays](../reference/profiles-and-overlays.md) |

---

## Templates

### CV templates

| Template | Layout | Parses | Font | Description |
|---|---|:--:|---|---|
| `cv/ats-clean` | single column | ✅ safe | Arial (system) | No web fonts, nothing fetched at build time. The one to upload to a portal. |
| `cv/academic` | single column | ✅ safe | Georgia (system) | Education-first. Orders publications directly after education and labels projects "Research & Projects". No page-count warning. |
| `cv/modern-single` | single column | ✅ safe | Lato | Slate rule system, aligned skills column. |
| `cv/timeline-clean` | single column | ✅ safe | Inter | Swiss minimal, timeline rule down the experience section. |
| `cv/executive-dark` | single column | ✅ safe | Source Sans 3 | Carbon header band, steel accent, title-first entries. |
| `cv/sidebar-compact` | sidebar + main | ⚠️ caution | Lato | Two-column coloured sidebar. Best-looking of the set for a human; pdftotext interleaves it, the other four engines do not. |

Run `cvloom list-templates` for this table plus the caveat behind each ⚠️ and ❌. `build`
and `check` print the caveat for whichever template you are actually using.

#### On the parses column

These ratings come from rendering each template to PDF and pulling the text layer back
out — the step every ATS runs before it parses anything. They are not estimates, and
they are measured with **five** extractors that work differently, from raw content-stream
order (what Apache Tika and PDFBox do by default) through geometric reconstruction to the
PDF structure tree. They disagree, and only what survives all five is rated safe.

Ratings are derived, not judged. Each template is built and read back with every
installed engine, and the rating follows from how many of them find a defect:

- **✅ safe** — no engine finds one.
- **⚠️ caution** — some do and some do not. Readable by most of the market, scrambled by
  part of it. Minor flags such as alignment artefacts land here.
- **❌ unsafe** — every engine finds one. Nothing reads it correctly.

`tests/test_ats_ratings.py` re-derives every rating on each run and fails if a declared
rating and the measured one disagree, in either direction.

Five of the six are safe. Four constructs were doing the damage and none of them was
visible on the page:

- a right-aligned date, which leaves an empty band down the page that extractors read as a
  column, so entries had their dates read out of order;
- kerning, which WeasyPrint emits as two positioned runs, so extractors put a space
  *inside* words (`PAYPAL` → `P AYP AL`);
- a 2px gap under the name, below the delta at which pypdf infers a line break, welding
  the name to the headline;
- a skills label column whose gutter is CSS padding, which puts no character in the text
  stream, so a full-width label ran into its first value.

All four are fixed, and `tests/test_extraction_fidelity.py` builds real PDFs and reads
them back through every installed engine so they stay fixed.

`cvloom check` grades what you *wrote* and cannot see any of this — whether a layout
survives extraction is a property of the template, and no amount of editing a bullet
changes it. That is why it is reported by `list-templates` and warned about on `build`.

What cvloom does **not** do in any template, because these break parsing much harder than
columns: `<table>` layout for content, text in headers/footers, or text baked into images.

Dates run **inline on each entry's meta line** — `company · date · location` — in every
template but `cv/sidebar-compact`. A date at the right margin leaves an empty band down
the page, and the two most common extractors read a band like that as a column and lift
the dates out of their entries. How wide the band gets depends on how long your bullets
are, so it is not something a template can control. See [ATS-readiness](../reference/ats-readiness.md).

You can check any of this yourself:

```bash
cvloom build --profile general --extract-text
```

That writes the PDF's text layer next to it, once per installed engine, so you can read
exactly what a parser gets.

The remaining difference between the safe templates is not parsing, it is the build:
`cv/ats-clean` and `cv/academic` use system fonts and fetch nothing, while the other
three pull a web font at render time. Offline they fall back to Arial, which changes
pagination but not extraction.

#### On field separators

`cv/ats-clean` and `cv/academic` join fields with ASCII only — `|` between contact-line
fields and between the parts of an entry's meta line (`Acme Corp | Remote`). The four
design-led templates use a middot (`·`).

This is **not** because a middot fails to extract. Every separator — middot, pipe, comma,
em dash, bullet — survives PDF text extraction intact; claims that an ATS "cannot read"
a middot are folklore. The reason is narrower: `·` is U+00B7, so it depends on the embedded
font subset carrying that glyph, and a custom font could omit it. ASCII has no such failure
mode. On the two templates whose entire purpose is conservatism, that trade is worth making;
on the design-led ones it is not.

The same two templates also use a hyphen in date ranges (`2021-03 - Present`), so their
extracted text is pure ASCII apart from the bullet glyph WeasyPrint renders for list
markers. Date ranges are one of the few things an ATS genuinely tries to parse, which is
why they follow the same rule. The design-led templates keep the en dash, which is correct
typography for a range.

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
| `text` | `cvloom export --format text` | `dist/<profile>.resume.txt` | Pasting into web forms, ATS fields, plain-text email |
| `docx` | `cvloom export --format docx` | `dist/<profile>.resume.docx` | Word/LibreOffice, when a `.docx` is required |

The `docx` format requires the optional `python-docx` dependency:

```bash
uv tool install 'cvloom[docx]'   # `uv tool install cvloom` global install
uv sync --extra docx                     # dev checkout (git clone)
```

The `docx` is the **ATS-upload artifact**, not a Word rendering of your template. It
carries the content, the reading order, real Word styles (`Title`, `Heading 1`,
`List Bullet`, one typeface) and your `section_titles` — but not a template's design.
The sidebar band of `cv/sidebar-compact` and the rule-and-dot of `cv/timeline-clean` are
page-layout devices, and the only way to express them in Word is with text boxes and
tables, which are the constructs that make a document parse badly. Send the PDF when a
human reads it and the DOCX when a parser does.

The `text` format carries the same content as the `markdown` one — the header, your summary
and every section your profile shows — with the markup dropped and headings set in caps over
a rule. It honours `section_order`, `show: false` and `section_titles` like the others do.

### JSON Resume conformance and extensions

Exported documents are validated against the official JSON Resume schema in CI, so
`json-resume` output is guaranteed to conform. Two consequences worth knowing:

- **Dates must be ISO 8601** (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`). cvloom allows free
  text — most importantly the open-ended end date (`Present` in `en`, `Actualidad` in
  `es`). JSON Resume has no such sentinel: a current role is expressed by *omitting*
  `endDate`, which is what cvloom emits for one. Any date that isn't ISO 8601 is
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

## Project Settings (`cvloom.yaml`)

`cvloom.yaml` sits at the project root and holds the settings that belong to the
project as a whole rather than to one build profile. A profile says how one output
variant is rendered; this says what the project *is*. The file is committed, and it
is optional — a project without one behaves exactly as it did before the file
existed.

Two keys:

```yaml
locale: es

ai:
  base_url: http://localhost:11434/v1
  model: gemma3:27b
```

`locale` is the language the project operates in. It sets the document's `lang`
attribute (which drives PDF hyphenation and the `/Lang` metadata ATS language
detection reads), the default section headings, the word used for an open-ended end
date, and the `--public` placeholder contact. It also selects the rules
`cvloom check` grades by, so a Spanish CV is graded by Spanish heuristics rather
than English ones applied to Spanish text.

The terminal stays in English by design — `check` reports Spanish findings about
Spanish prose in English.

`cvloom init --locale es` writes the file for you; `cvloom list-locales` shows what
is available and how completely each language is supported. One project operates in
one language: a CV in a second language is a second project directory. See
[Locales](../reference/locales.md) for the full reference.

`ai` records which backend and model this project is analysed with — a property of
the project rather than of whichever shell you happen to run `cvloom ai` from.
`CVLOOM_AI_BASE_URL` and `CVLOOM_AI_MODEL` override it, so a machine can point at
its own endpoint without editing a tracked file.

> **`ai.api_key` does not exist, deliberately.** This file is committed, so a key
> here is a key in your history. cvloom refuses to load a config containing one,
> and the scaffolded pre-commit hook blocks it at the commit. Use
> `CVLOOM_AI_API_KEY`. Run `cvloom ai config` to see which layer each value came
> from.

### Where section headings come from

Three sources decide a heading, narrowest winning:

| Source | Set by | Applied |
|---|---|---|
| **`section_titles` in the profile** | You, per output variant | Always wins. The only way to customise a heading |
| **The locale pack** | `locale:` in `cvloom.yaml` | The default, in the project's language |
| **A template suggestion** | The template's designer | *Never automatically* — `cvloom list-templates` prints it for you to paste |

So `cv/executive-dark` renders "Summary" out of the box even though the design reads
better with "Executive Summary". Running `cvloom list-templates` prints that wording
as a `section_titles:` block; pasting it into a profile is what applies it. The
mechanism is deliberately singular — one place to change a heading, not three.

```yaml
# profiles/executive.yaml
template: cv/executive-dark
section_titles:
  summary: Executive Summary
  skills: Core Competencies
```

Headings follow the content out of the HTML and PDF into the Markdown, plain-text
and DOCX exports, so all four agree. They do not reach the JSON Resume export, whose
section names are fixed by that schema.

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
| `--check` | Runs all 25 lint rules after build and prints a per-axis breakdown |
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
| `CVLOOM_AI_BASE_URL` | Yes, unless `ai.base_url` is set | — | Base URL of the OpenAI-compatible API endpoint |
| `CVLOOM_AI_API_KEY` | No | `"not-set"` | API key for the provider. **The only place a key may live** |
| `CVLOOM_AI_MODEL` | No | `ai.model`, else `"gpt-4o"` | Model identifier |

The endpoint and model can also be recorded per project under `ai:` in
`cvloom.yaml`; these variables override that block. The API key cannot — that file
is committed. `cvloom ai config` reports which layer each value came from.

See [AI Features](ai-features.md) for provider-specific setup (Ollama, LiteLLM, OpenAI).

The MCP server reads one more:

| Variable | Required | Default | Description |
|---|---|---|---|
| `CVLOOM_PROJECT_ROOT` | No | The server's cwd | Project the MCP server operates on when a tool call names none. Overridden by a call's own `project_root` and by `cvloom-mcp --project-root`. See [MCP Server](../reference/mcp-server.md#which-project-the-server-operates-on) |

It has no effect on the `cvloom` CLI, which always operates on the current directory.
