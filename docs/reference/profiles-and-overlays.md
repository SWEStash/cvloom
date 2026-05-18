# Profiles and Overlays

[Back to README](../../README.md)

cvloom uses **profiles** to produce multiple tailored versions of your CV from a single
set of base data. Each profile controls which sections appear, which entries are included,
and how content is customized for a particular role. **Overlays** are the mechanism profiles
use to patch data at build time without modifying your source YAML files.

This guide starts with simple profiles and progressively introduces the overlay system.

---

## Table of Contents

1. [When to Use Profiles](#when-to-use-profiles)
2. [Profile Basics](#profile-basics)
3. [Tag-Based Filtering](#tag-based-filtering)
4. [Force-Including Entries](#force-including-entries)
5. [Section Ordering](#section-ordering)
6. [Job Context](#job-context)
7. [Overlays](#overlays)
   - [Basics Overlay](#basics-overlay)
   - [Array Section Overlays](#array-section-overlays-work-education-projects)
   - [Skills Overlay](#skills-overlay)
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
```

### Profile Keys Reference

| Key                 | Required | Default                                 | Description                                                           |
|---------------------|----------|-----------------------------------------|-----------------------------------------------------------------------|
| `template`          | Yes      | —                                       | Template path (e.g. `cv/ats-single`)                                  |
| `output_filename`   | No       | Profile name                            | Base name for output files (`.html`, `.pdf`)                          |
| `pdf_filename_format` | No     | `{first}_{last}_Resume.pdf`             | Override the PDF filename; `{first}` and `{last}` are derived from contact name |
| `sections`          | No       | All `true`                              | Toggle sections on or off                                             |
| `include_tags`      | No       | `[]` (include all)                      | Only include entries with at least one matching tag                   |
| `include_entries`   | No       | —                                       | Force-include entries excluded by tag filtering                       |
| `section_order`     | No       | `[skills, work, education, projects]`   | Override the rendering order of sections                              |
| `job_context`       | No       | —                                       | Metadata passed to cover letter templates and AI commands             |
| `overlays`          | No       | —                                       | Per-job data patches (see below)                                      |

---

## Tag-Based Filtering

Entries in your `data/` YAML files can carry a `tags` list. When a profile sets
`include_tags`, only entries whose tags overlap with that list are included.

```yaml
# profiles/backend-focused.yaml
template: cv/ats-single
include_tags: [python, kafka, aws, microservices]
```

This filters both `work` and `projects` sections. Work entries that have no `tags` field
at all are always included (they are treated as universally relevant). Projects without
matching tags are excluded.

---

## Force-Including Entries

Sometimes tag filtering removes an entry you still want. Use `include_entries` to
force-include specific entries by matching on a field value:

```yaml
include_tags: [python, aws]

include_entries:
  work:
    - match: {company: "Acme Corp"}
  projects:
    - match: {name: "open-source-tool"}
```

The `match` object can use any field present on the entry. If the entry was already
included by tag filtering, the force-include is a no-op.

Under the hood, cvloom performs a second unfiltered data load to retrieve the
excluded entries, then merges the matched ones back in.

---

## Section Ordering

The default rendering order is `[skills, work, education, projects]`. Override it
per-profile:

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
are applied after tag filtering and force-includes, but before rendering.

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

The skills overlay filters entire categories or removes individual items within a
category.

#### Filtering categories

`include_categories` and `exclude_categories` are mutually exclusive. If both are
set, only `include_categories` takes effect (a validation warning is emitted).

```yaml
overlays:
  skills:
    include_categories: [Languages, "Data & Messaging", "Infrastructure & Cloud"]
```

```yaml
overlays:
  skills:
    exclude_categories: ["Frameworks & Tools"]
```

#### Removing individual items

Use `category_overrides` to remove specific items from a category while keeping
the category itself:

```yaml
overlays:
  skills:
    include_categories: [Languages, Cloud]
    category_overrides:
      Languages:
        exclude_items: [Go, Rust]
```

Skill items can be plain strings or `{name, level}` dicts. The `exclude_items` list
matches against the item name in either case.

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

# ── Tag filtering ──────────────────────────────────────────────────
# Only include entries tagged with at least one of these.
include_tags: [python, kafka, aws, microservices, infrastructure]

# ── Force-includes ─────────────────────────────────────────────────
# Keep the "Acme Corp" work entry even if its tags don't overlap.
include_entries:
  work:
    - match: {company: "Acme Corp"}

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

  # Keep only relevant skill categories, drop a niche item.
  skills:
    include_categories: [Languages, "Data & Messaging", "Infrastructure & Cloud"]
    category_overrides:
      Languages:
        exclude_items: [PHP]
```

Build this profile with:

```bash
uv run cvloom build --profile stripe-infra --private
```

Or build a public version with placeholder contact data:

```bash
uv run cvloom build --profile stripe-infra --public --skip-pdf
```
