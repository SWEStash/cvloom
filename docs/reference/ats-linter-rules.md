# ATS Linter Rules Reference

[Back to README](../../README.md)

## Overview

The `cvloom check` command runs 17 built-in rules against a resolved profile to catch
common CV quality issues. The linter inspects highlights (bullet points) in the work,
education, and projects sections, as well as skill items, contact info, and basics.

```bash
uv run cvloom check --profile NAME
```

Each finding includes:

- **Rule ID** -- a stable identifier (e.g. `ats-001`)
- **Section** -- which CV section triggered the finding
- **Entry** -- the company, institution, or project name
- **Message** -- what was detected
- **Fix hint** -- actionable suggestion for resolving the issue

The command exits with code **1** if any issues are found, and **0** if the profile is clean.

Sections that are hidden (`show_sections: false` in the profile) are skipped entirely --
the linter only checks content that would appear in the rendered CV.

## Quick Reference

| Rule ID   | Name                      | Severity   | Sections Checked           | What It Flags |
|-----------|---------------------------|:----------:|----------------------------|---------------|
| `ats-001` | passive-voice             | warning    | work, education, projects  | Passive voice constructions in highlights |
| `ats-002` | missing-quantification    | warning    | work, projects             | Highlights with no numbers |
| `ats-003` | noise-skills              | warning    | skills                     | Low-value commodity skills |
| `ats-004` | weak-action-verbs         | warning    | work, education, projects  | Highlights starting with weak verbs/phrases |
| `ats-005` | highlight-length          | warning    | work, education, projects  | Highlights shorter than 8 or longer than 25 words |
| `ats-006` | bullet-count              | warning    | work                       | Fewer than 3 or more than 8 highlights per role |
| `ats-007` | first-person              | warning    | work, projects, basics     | First-person pronouns (I/my/me/mine/myself) |
| `ats-008` | vague-buzzwords           | warning    | work, projects, basics     | Overused vague terms (e.g. "motivated", "proactive") |
| `ats-009` | skill-count               | warning    | skills                     | Fewer than 8 or more than 25 total skills |
| `ats-010` | profile-links             | warning    | contact                    | No LinkedIn or GitHub link present |
| `ats-011` | page-count                | warning    | (whole CV)                 | Estimated page count exceeds 2 |
| `ats-012` | date-format-consistency   | warning    | work, education            | Mixed YYYY-MM / YYYY date formats |
| `ats-013` | tense-consistency         | warning    | work                       | Past tense in current role or present tense in past role |
| `ats-014` | summary-length            | warning    | basics                     | Summary shorter than 20 or longer than 80 words |
| `ats-015` | action-result             | suggestion | work, projects             | Metric present but no result-framing phrase |
| `ats-016` | readability               | suggestion | work, projects             | Flesch-Kincaid grade outside target range 6–12 |
| `ats-017` | tech-mentions-in-work     | suggestion | work                       | Work entry highlights mention no skill item |

---

## Rule Details

### ats-001: passive-voice

**Sections checked:** work, education, projects | **Severity:** warning

Detects passive voice constructions using the pattern:
`(was|were|been|being|is|are) [also] <past-participle>` where past participles are words
ending in `-ed`, `-en`, `-wn`, `-lt`, `-ht`, `-pt`, or `-nt`. The match is case-insensitive.

**Bad:**
- "Was responsible for designing the API"
- "The system was built using Python"

**Good:**
- "Designed the API serving 2M requests/day"
- "Built the system using Python"

**Fix hint:** Rewrite using an active verb (e.g. 'Designed', 'Built', 'Led').

---

### ats-002: missing-quantification

**Sections checked:** work, projects | **Severity:** warning

Flags any highlight that contains no digits at all. Numbers provide concrete evidence of
impact and are strongly preferred by hiring managers and ATS systems.

**Bad:**
- "Improved application performance significantly"

**Good:**
- "Improved application performance by 40%, reducing p99 latency from 800ms to 120ms"

**Fix hint:** Add metrics: percentages, counts, dollar amounts, or time saved.

---

### ats-003: noise-skills

**Sections checked:** skills | **Severity:** warning

Flags skills that appear in a built-in noise list. These are commodity office-suite tools
that add no signal to a technical CV:

- Microsoft Office, Microsoft Word, Microsoft Excel, Microsoft PowerPoint
- Google Docs, Google Sheets, Google Slides
- MS Office, MS Word

**Fix hint:** Remove it or replace with a more specific/valuable skill.

---

### ats-004: weak-action-verbs

**Sections checked:** work, education, projects | **Severity:** warning

Flags highlights that begin with one of these weak openers:

- helped, assisted, worked on, was responsible for, participated in, was involved in, contributed to

**Bad:** "Helped the team implement the new API"

**Good:** "Implemented the new API, reducing integration time by 30%"

**Fix hint:** Start with a strong action verb: 'Designed', 'Implemented', 'Reduced', 'Delivered', 'Architected'.

---

### ats-005: highlight-length

**Sections checked:** work, education, projects | **Severity:** warning

- **Too short:** fewer than 8 words — lacks context, impact, or specificity.
- **Too long:** more than 25 words — hard to scan; split or tighten.

---

### ats-006: bullet-count

**Sections checked:** work | **Severity:** warning

- **Too few:** fewer than 3 highlights per work entry — insufficient detail for the role.
- **Too many:** more than 8 highlights — dilutes focus; cut the weakest bullets.

---

### ats-007: first-person

**Sections checked:** work highlights, projects highlights, basics summary | **Severity:** warning

Flags uses of: `I`, `my`, `me`, `mine`, `myself` (case-insensitive).

**Bad:** "I led a team of 5 engineers to deliver the API."

**Good:** "Led a team of 5 engineers to deliver the API."

---

### ats-008: vague-buzzwords

**Sections checked:** work highlights, projects highlights, basics summary | **Severity:** warning

Flags overused, low-signal terms: motivated, detail-oriented, team player, hardworking,
passionate, dynamic, results-driven, go-getter, synergy, proactive, self-starter, innovative.

**Fix hint:** Replace with a specific example or accomplishment that demonstrates the trait.

---

### ats-009: skill-count

**Sections checked:** skills (all categories combined) | **Severity:** warning

- **Too few:** fewer than 8 total skills — sparse; add relevant tools and technologies.
- **Too many:** more than 25 total skills — overwhelming; keep only job-relevant items.

---

### ats-010: profile-links

**Sections checked:** contact | **Severity:** warning

Warns when neither a LinkedIn URL/handle nor a GitHub URL/handle is present in the contact
data or `public_links`.

**Fix hint:** Add `linkedin:` and/or `github:` to `private/contact.yaml`.

---

### ats-011: page-count

**Sections checked:** whole CV (word estimate) | **Severity:** warning

Estimates page count as total words ÷ 500. Warns if estimated pages > 2. Skipped for
`cv/academic` template (academic CVs may be longer).

**Fix hint:** Remove the least impactful highlights or shorten descriptions.

---

### ats-012: date-format-consistency

**Sections checked:** work, education | **Severity:** warning

Flags mixing of `YYYY-MM` (e.g. `2021-03`) and `YYYY` (e.g. `2021`) date formats within
the same section. Pick one format and use it throughout.

---

### ats-013: tense-consistency

**Sections checked:** work | **Severity:** warning

- **Current role** (end_date = "Present" or missing): highlights should use **present tense**.
- **Past role** (end_date is a year/date): highlights should use **past tense**.

The check looks at the first word of each highlight.

**Bad:** "Built new features" in a current role (past tense).

**Good:** "Build new features and ship weekly" in a current role.

---

### ats-014: summary-length

**Sections checked:** basics summary | **Severity:** warning

- **Too short:** fewer than 20 words — insufficient to convey value proposition.
- **Too long:** more than 80 words — too dense; recruiters skim summaries.

---

### ats-015: action-result

**Sections checked:** work, projects | **Severity:** suggestion

Flags highlights that contain a metric (%, $, ×, k/m/b suffix) but lack a result-framing
phrase such as "enabling", "resulting in", "saving", "driving", "reducing", "improving".

**Bad:** "Refactored the codebase, reducing lines by 40%."

**Good:** "Refactored the codebase, reducing lines by 40% and enabling 3× faster deploys."

---

### ats-016: readability

**Sections checked:** work, projects | **Severity:** suggestion

Calculates the Flesch-Kincaid Grade Level for each highlight (treated as a single sentence).
Flags highlights outside the target range of grade 6–12.

- **Grade > 12:** sentence is too complex — too many polysyllabic words or the highlight is
  too long. Simplify vocabulary or split into two bullets.
- **Grade < 6:** sentence is too simple — too short or uses only monosyllabic words.
  Add a metric, scope, or result to increase substance.

**Fix hint (too complex):** Break into shorter phrases or replace multi-syllable words with simpler alternatives.

**Fix hint (too simple):** Expand the highlight with a result, metric, or scope to increase substance.

---

### ats-017: tech-mentions-in-work

**Sections checked:** work | **Severity:** suggestion

Cross-references each work entry's highlights against all skill item names. Fires when a
work entry has highlights but none of them mention any skill (case-insensitive substring match).

Skipped when the skills section is empty.

**Bad:** A "Senior Python Engineer" role whose highlights mention no technologies at all.

**Good:** At least one highlight references a tool, language, or framework from the skills section.

**Fix hint:** Reference at least one tool, language, or framework from your skills section.
