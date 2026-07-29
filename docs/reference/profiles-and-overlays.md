# Profiles and Overlays

[Back to README](../../README.md)

cvloom uses **profiles** to produce multiple tailored versions of your CV from a single
set of base data. Each profile controls which sections appear, which entries are selected,
and how content is customized for a particular role. **Overlays** are the mechanism profiles
use to patch data at build time without modifying your source YAML files.

This guide starts with simple profiles and progressively introduces the overlay system.

---

## Table of Contents

1. [When to Use Profiles](#when-to-use-profiles)
2. [Profile Basics](#profile-basics)
3. [Selecting Content](#selecting-content)
   - [The rules](#the-rules)
   - [Untagged entries do not match](#untagged-entries-do-not-match)
   - [Why tags have no exclusion, but categories do](#why-tags-have-no-exclusion-but-categories-do)
4. [Section Ordering](#section-ordering)
5. [Job Context](#job-context)
6. [Overlays](#overlays)
   - [Basics Overlay](#basics-overlay)
   - [Array Section Overlays](#array-section-overlays-work-education-projects)
   - [Skills Overlay](#skills-overlay)
7. [One Dataset, N Applications — A Worked Example](#one-dataset-n-applications--a-worked-example)
8. [Full Annotated Example](#full-annotated-example)

---

## When to Use Profiles

A single general-purpose CV rarely works for every application. Profiles let you:

- Emphasize different skills and experience for different roles.
- Swap your headline and summary to match the job description.
- Cherry-pick the most relevant highlights from each position.
- Remove irrelevant sections or entries entirely.
- Produce both a "general" CV and multiple job-specific variants from one data set.

Every build targets exactly one profile. The default is `general`.

```bash
uv run cvloom build                        # builds profiles/general.yaml
uv run cvloom build --profile example-job   # builds profiles/example-job.yaml
```

---

## Profile Basics

Profiles live in `profiles/*.yaml`. The only required key is `template`.

```yaml
# profiles/general.yaml — the simplest useful profile
template: cv/ats-single
output_filename: cv
sections:
  work: true
  education: true
  skills: true
  projects: true
  publications: true
  certifications: true
  awards: true
  languages: true
```

### Profile Keys Reference

| Key                 | Required | Default                                 | Description                                                           |
|---------------------|----------|-----------------------------------------|-----------------------------------------------------------------------|
| `template`          | Yes      | —                                       | Template path (e.g. `cv/ats-single`)                                  |
| `output_filename`   | No       | Profile name                            | Base name for output files (`.html`, `.pdf`)                          |
| `pdf_filename_format` | No     | `{first}_{last}_Resume_{profile}.pdf`   | Override the PDF filename. `{first}`/`{last}`/`{name}` come from the contact name; `{profile}` is the profile name |
| `sections`          | No       | All `true`                              | Toggle sections on or off                                             |
| `select`            | No       | —                                       | Per-section content selection (see below)                             |
| `section_order`     | No       | `[skills, work, education, projects, publications, certifications, awards, languages]` | Override the rendering order of sections |
| `job_context`       | No       | —                                       | Metadata passed to cover letter templates and AI commands             |
| `overlays`          | No       | —                                       | Per-job data patches (see below)                                      |

---

## Selecting Content

Entries in your `data/` YAML files can carry a `tags` list. A profile's `select`
block narrows individual sections by tag:

```yaml
# profiles/backend-focused.yaml
template: cv/ats-single
select:
  work:
    tags: [python, kafka, aws, microservices]
  projects:
    tags: [python]
  skills:
    exclude_categories: [Design]
```

**Selection is per-section and opt-in.** A section you do not name is untouched —
in the example above, `education`, `publications`, `certifications`, `awards` and
`languages` all keep every entry. This is what lets you narrow one section without
disturbing the rest.

### The rules

For an entry section:

1. `tags` is set → keep only entries carrying at least one of those tags
2. otherwise → keep every entry

For `skills`, which is keyed on `category` rather than `tags`:

1. category is in `exclude_categories` → drop it
2. otherwise, if `categories` is set → keep only the listed categories
3. otherwise → keep every category

### Untagged entries do not match

**An entry with no tags does not match a `tags` list.** An include list is a query,
and untagged content answers no query — the same way filtering issues by label
does not surface unlabelled ones. This holds uniformly for every section.

The trap is adding a new entry and forgetting to tag it: it disappears from every
profile that filters that section. cvloom warns when this happens:

```
Warning: select.work: dropped 1 entry that carries no tags.
         Tag them to keep them in this profile.
```

Take that warning seriously — it usually means your newest role is missing from
the CV you are about to send.

### Why tags have no exclusion, but categories do

Tags work best as a **one-dimensional classification** — one axis, such as
practice area (`backend`, `data`, `academic`). Keep them to that axis and an
allow-list expresses everything you need. Mixing in a second dimension
(seniority, employer, career phase) is what makes filtering awkward, because no
single list then cuts cleanly.

Skill categories are different: they are a *closed*, enumerable set declared in
`data/skills.yaml`. Excluding three of fifteen is both equally expressive and far
shorter than listing the other twelve, so `exclude_categories` exists there.

---

## Section Ordering

The default rendering order is
`[skills, work, education, projects, publications, certifications, awards, languages]`
(`cv/academic` instead leads with `[education, publications, ...]`).
Override it per-profile:

```yaml
section_order: [work, skills, projects, education]
```

Only sections that are enabled in `sections` (or left at their default of `true`) are
actually rendered, regardless of their position in `section_order`.

---

## Job Context

The `job_context` key provides metadata that cover letter templates and AI commands can
reference. It has no effect on CV templates but is available in the Jinja2 render context
as `job_context`.

```yaml
job_context:
  company: "Target Corp"
  role: "Senior Engineer"
  hiring_manager: "Jane Smith"
  notes: |
    Cover letter body text or notes about the role.
```

---

## Overlays

Overlays are the core customization mechanism. They patch your base data at build time,
letting you tailor content for a specific job without duplicating YAML files. Overlays
are applied after selection, but before rendering — so they only ever see the entries
that survived `select`.

All overlays live under the `overlays` key in a profile:

```yaml
overlays:
  basics: { ... }
  work: [ ... ]
  education: [ ... ]
  projects: [ ... ]
  skills: { ... }
```

### Basics Overlay

A shallow merge onto `data["basics"]`. Any key you specify overwrites the corresponding
value from `data/basics.yaml`.

```yaml
overlays:
  basics:
    headline: "Backend Engineer — Python & Distributed Systems"
    summary: >
      Tailored summary emphasizing backend and systems experience
      for this specific role.
```

Keys you do not mention are left unchanged. This is the simplest overlay type.

### Array Section Overlays (work, education, projects)

Array overlays are lists of match-and-patch operations. Each item must have a `match`
object that identifies the target entry.

The match key varies by section:

| Section     | Typical match key |
|-------------|-------------------|
| `work`      | `company`         |
| `education` | `institution`     |
| `projects`  | `name`            |

You can match on any field present on the entry, and you can match on multiple fields
at once.

#### Overriding fields

```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}
      title: "Senior Backend Engineer"    # override the job title
```

Currently `title` is the supported field override.

#### Excluding an entry

```yaml
overlays:
  work:
    - match: {company: "Old Corp"}
      exclude: true                       # removes this entry entirely
```

#### Highlight operations

Highlights in your data files can be plain strings or `{id, text}` dicts. Using IDs
gives overlays stable handles to address individual bullet points:

```yaml
# In data/work.yaml
highlights:
  - id: kafka-pipeline
    text: "Built real-time data pipeline processing 2M events/sec with Kafka."
  - id: api-redesign
    text: "Redesigned REST API, reducing latency by 35%."
  - "Plain string highlights also work (but cannot be targeted by ID)."
```

The overlay `highlights` block supports these options:

| Key       | Type           | Description                                           |
|-----------|----------------|-------------------------------------------------------|
| `mode`    | `pick` / `exclude` / `all` | Which highlights to keep (default: `all`) |
| `items`   | list of IDs    | Highlight IDs to pick or exclude                      |
| `replace` | map of ID to text | Replace the text of specific highlights by ID      |
| `append`  | list of strings | Add new highlights to the end                        |

**Mode: `pick`** — keep only highlights whose `id` is in `items`:

```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}
      highlights:
        mode: pick
        items: [kafka-pipeline, api-redesign]
```

**Mode: `exclude`** — remove highlights whose `id` is in `items`, keep the rest:

```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}
      highlights:
        mode: exclude
        items: [legacy-migration]
```

**Mode: `all`** (default) — keep every highlight. Useful when you only want to
`replace` or `append`:

```yaml
overlays:
  work:
    - match: {company: "Acme Corp"}
      highlights:
        replace:
          kafka-pipeline: "Improved Kafka pipeline throughput by 40% through partition rebalancing."
        append:
          - "Led migration to event-driven architecture."
```

All three sub-operations (`mode` filtering, `replace`, `append`) can be combined
in a single overlay block. They are applied in that order: filter first, then replace
text, then append new items.

### Skills Overlay

The skills overlay removes individual items within a category. Choosing *which
categories appear* is selection, not patching — that lives in
[`select.skills`](#selecting-content).

Use `category_overrides` to remove specific items while keeping the category:

```yaml
select:
  skills:
    categories: [Languages, Cloud]

overlays:
  skills:
    category_overrides:
      Languages:
        exclude_items: [Go, Rust]
```

Skill items can be plain strings or `{name, level}` dicts. The `exclude_items` list
matches against the item name in either case.

---

## One Dataset, N Applications — A Worked Example

This is the idea cvloom is built around: **write each fact about your career once, then
produce any number of tailored CVs from it — deterministically, and diffable.** No
copy-pasted `resume_backend_final_v2.docx` files drifting out of sync.

### The single source of truth

You maintain one work entry. Each highlight has a stable `id` so overlays can address it:

```yaml
# data/work.yaml  (the ONLY place these facts live)
- company: DataCo
  title: Software Engineer
  location: Remote
  start_date: "2021-01"
  end_date: Present
  highlights:
    - id: api
      text: "Built a FastAPI service handling 20k req/s for the billing platform."
    - id: kafka
      text: "Designed a Kafka pipeline ingesting 2M events/day into the warehouse."
    - id: dbt
      text: "Modeled 40+ dbt marts powering exec dashboards, cutting report latency 60%."
    - id: mentoring
      text: "Mentored 3 engineers and ran the team's code-review guild."
  tags: [python, fastapi, kafka, dbt, sql]
```

```yaml
# data/skills.yaml
- category: Languages
  items: [Python, SQL, Go]
- category: Backend
  items: [FastAPI, PostgreSQL, Redis]
- category: Data
  items: [Kafka, dbt, Snowflake, Airflow]
```

### Two applications, two profiles — same data

**Application A — a backend role.** Emphasize the API and streaming work; show backend skills:

```yaml
# profiles/backend-role.yaml
template: cv/ats-single
output_filename: backend-cv
job_context: { company: Acme, role: Senior Backend Engineer }
select:
  skills:
    categories: [Languages, Backend]
overlays:
  basics:
    headline: "Senior Backend Engineer — Python & APIs"
  work:
    - match: { company: DataCo }
      title: "Senior Backend Engineer"
      highlights:
        mode: pick
        items: [api, kafka, mentoring]   # the 'dbt' bullet is dropped
```

**Application B — an analytics-engineering role.** Emphasize the warehouse and dbt work;
show data skills — *from the exact same base data*:

```yaml
# profiles/data-role.yaml
template: cv/ats-single
output_filename: data-cv
job_context: { company: Globex, role: Analytics Engineer }
select:
  skills:
    categories: [Languages, Data]
overlays:
  basics:
    headline: "Analytics Engineer — dbt & Warehousing"
  work:
    - match: { company: DataCo }
      title: "Analytics Engineer"
      highlights:
        mode: pick
        items: [dbt, kafka, mentoring]   # the 'api' bullet is dropped
```

The `kafka` and `mentoring` bullets appear in both; `api` is backend-only; `dbt` is
data-only. Neither profile copies a single line of your base data. (The example shows only
the files that change — you also need your usual `data/basics.yaml` and
`data/education.yaml`.)

### Build both

```bash
uv run cvloom build --profile backend-role --public --skip-pdf
uv run cvloom build --profile data-role --public --skip-pdf
```

The two CVs now carry different work bullets from the same source:

| Bullet | `backend-cv` | `data-cv` |
|---|:---:|:---:|
| `api` — FastAPI billing service | ✓ | — |
| `kafka` — streaming pipeline | ✓ | ✓ |
| `dbt` — warehouse marts | — | ✓ |
| `mentoring` — code-review guild | ✓ | ✓ |

### The tailoring is reviewable and diffable

Because tailoring is *declarative config*, not hand-editing, it is reviewable two ways.
First, the profiles themselves diff cleanly in git — a reviewer sees exactly which bullets
and skill categories each application selected. Second, `cvloom diff` gives a quick
content-size comparison of the two resolved profiles:

```bash
uv run cvloom diff backend-role data-role
```

```
Words: 81 vs 80 (-1)
Highlights: 4 vs 4
```

(Both variants keep the same DataCo entry and the same sections, so they are the same size;
the *difference is which bullets and skills each one selected* — visible in the table above
and in the rendered output.)

### Why this matters

Update a fact **once** — say the Kafka pipeline now handles 5M events/day — in
`data/work.yaml`, and **every** profile that includes that bullet updates on the next build.
There is no find-and-replace across a folder of Word documents, and no risk that your
"backend" CV quietly disagrees with your "data" CV about what you actually did. One dataset,
N applications, always consistent.

---

## Full Annotated Example

Below is a complete profile combining most features. It targets a senior infrastructure
role at Stripe.

```yaml
# profiles/stripe-infra.yaml

# ── Template & output ──────────────────────────────────────────────
template: cv/ats-single
output_filename: stripe-infra-cv

# ── Section visibility ─────────────────────────────────────────────
sections:
  work: true
  education: true
  skills: true
  projects: true

# ── Section ordering ───────────────────────────────────────────────
# Lead with skills for an infra role, then work experience.
section_order: [skills, work, projects, education]

# ── Content selection ──────────────────────────────────────────────
# Narrow only the sections named here; education keeps every entry.
# Remember: an entry with no tags does not match a `tags` list.
select:
  work:
    tags: [python, kafka, aws, microservices, infrastructure]
  projects:
    tags: [python, infrastructure]
  skills:
    categories: [Languages, "Data & Messaging", "Infrastructure & Cloud"]

# ── Job context (for cover letter templates and AI commands) ───────
job_context:
  company: Stripe
  role: Senior Infrastructure Engineer
  hiring_manager: Pat Johnson
  notes: |
    Stripe's infrastructure team focuses on reliability and developer
    experience. Emphasize distributed systems and observability work.

# ── Overlays ───────────────────────────────────────────────────────
overlays:

  # Swap headline and summary for this role.
  basics:
    headline: "Senior Infrastructure Engineer"
    summary: >
      Infrastructure engineer with 8+ years building high-throughput
      distributed systems. Deep Kafka and AWS experience at scale,
      with a focus on reliability and developer productivity.

  # Customize work entries.
  work:
    # Cherry-pick the most relevant highlights from Acme Corp.
    - match: {company: "Acme Corp"}
      title: "Senior Infrastructure Engineer"
      highlights:
        mode: pick
        items: [kafka-pipeline, microservices-migration, observability]
        replace:
          kafka-pipeline: "Architected Kafka-based event bus handling 2M events/sec across 200 nodes."
        append:
          - "Designed zero-downtime deployment pipeline for 200-node Kafka cluster."

    # Remove an irrelevant early-career position.
    - match: {company: "Old Startup Inc"}
      exclude: true

  # Drop a niche item. Which categories appear is set in `select` above.
  skills:
    category_overrides:
      Languages:
        exclude_items: [PHP]
```

Build this profile with:

```bash
uv run cvloom build --profile stripe-infra
```

That uses your real contact data from `private/contact.yaml`. To build a public
version with placeholder contact data instead:

```bash
uv run cvloom build --profile stripe-infra --public --skip-pdf
```
