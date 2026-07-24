# Writing Lint Rules Reference

[Back to README](../../README.md) · See also: [ATS-readiness model](ats-readiness.md)

## Overview

The `cvloom check` command runs 17 deterministic, rule-based checks against a resolved
profile to catch common CV writing issues. The linter inspects highlights (bullet points) in
the work, education, and projects sections, as well as skill items, contact info, and basics.

```bash
uv run cvloom check --profile NAME
```

Each finding includes:

- **Rule ID** — a stable identifier (e.g. `wl-001`)
- **Category** — one of `writing`, `structure`, or `ats-parse` (see below)
- **Section** — which CV section triggered the finding
- **Entry** — the company, institution, or project name
- **Message** — what was detected
- **Fix hint** — actionable suggestion for resolving the issue

The command exits with code **1** if any issues are found, and **0** if the profile is clean.
Hidden sections (`show_sections: false`) are skipped — the linter only checks content that
would appear in the rendered CV.

### On categories, and why there is no single "ATS score"

These rules are grouped into the three **honest, measurable axes** of ATS-readiness. cvloom
deliberately does **not** emit a single "ATS score 0–100": no ATS publishes such a number, the
one signal that is actually predictive (keyword overlap) only exists relative to a specific job
description, and there is no public ground-truth to calibrate against. See the
[ATS-readiness model](ats-readiness.md) for the full reasoning.

| Category | What it measures | Honest claim |
|---|---|---|
| `writing` | Writing quality — voice, verbs, quantification, tense, buzzwords, readability | Correlates with recruiter/human preference |
| `structure` | Document structure & completeness — counts, lengths, links, page budget | Helps both humans and parsers scan the CV |
| `ats-parse` | Signals that specifically affect ATS parsing / keyword pickup | Reduces the most common ATS failure modes |

Parseability of the *rendered PDF* (tagged text, single-column, standard headings) is a
**rendering** concern and is tracked separately — see the ATS-readiness doc.

## Quick Reference

| Rule ID  | Name                    | Category   | Severity   | Sections Checked           | What It Flags |
|----------|-------------------------|------------|:----------:|----------------------------|---------------|
| `wl-001` | passive-voice           | writing    | warning    | work, education, projects  | Passive voice constructions in highlights |
| `wl-002` | missing-quantification  | writing    | warning    | work, projects             | Highlights with no numbers |
| `wl-003` | noise-skills            | writing    | warning    | skills                     | Low-value commodity skills |
| `wl-004` | weak-action-verbs       | writing    | warning    | work, education, projects  | Highlights starting with weak verbs/phrases |
| `wl-005` | highlight-length        | writing    | warning    | work, education, projects  | Highlights shorter than 8 or longer than 25 words |
| `wl-006` | bullet-count            | structure  | warning    | work                       | Fewer than 3 or more than 8 highlights per role |
| `wl-007` | first-person            | writing    | warning    | work, projects, basics     | First-person pronouns (I/my/me/mine/myself) |
| `wl-008` | vague-buzzwords         | writing    | warning    | work, projects, basics     | Overused vague terms (e.g. "motivated", "proactive") |
| `wl-009` | skill-count             | structure  | warning    | skills                     | Fewer than 8 or more than 25 total skills |
| `wl-010` | profile-links           | structure  | warning    | contact                    | No LinkedIn or GitHub link present |
| `wl-011` | page-count              | structure  | warning    | (whole CV)                 | Estimated page count exceeds 2 |
| `wl-012` | date-format-consistency | ats-parse  | warning    | work, education            | Mixed YYYY-MM / YYYY date formats |
| `wl-013` | tense-consistency       | writing    | warning    | work                       | Past tense in current role or present tense in past role |
| `wl-014` | summary-length          | structure  | warning    | basics                     | Summary shorter than 20 or longer than 80 words |
| `wl-015` | action-result           | writing    | suggestion | work, projects             | Metric present but no result-framing phrase |
| `wl-016` | readability             | writing    | suggestion | work, projects             | Flesch-Kincaid grade outside target range 6–12 |
| `wl-017` | tech-mentions-in-work   | ats-parse  | suggestion | work                       | Work entry highlights mention no skill item |
| `wl-018` | education-size          | structure  | warning    | education                  | More than 6 education entries — degrees and short courses rendering with equal weight |

---

## Rule Details

### wl-001: passive-voice

**Category:** writing | **Sections checked:** work, education, projects | **Severity:** warning

Detects passive voice constructions using the pattern:
`(was|were|been|being|is|are) [also] <past-participle>` where past participles are words
ending in `-ed`, `-en`, `-wn`, `-lt`, `-ht`, `-pt`, or `-nt`. The match is case-insensitive.

**Basis:** active voice is the near-universal recommendation of resume-writing guidance;
recruiters read active bullets as ownership of impact.

**Bad:**
- "Was responsible for designing the API"
- "The system was built using Python"

**Good:**
- "Designed the API serving 2M requests/day"
- "Built the system using Python"

**Fix hint:** Rewrite using an active verb (e.g. 'Designed', 'Built', 'Led').

---

### wl-002: missing-quantification

**Category:** writing | **Sections checked:** work, projects | **Severity:** warning

Flags any highlight that contains no digits at all. Numbers provide concrete evidence of
impact and are strongly preferred by hiring managers.

**Basis:** quantified achievements are consistently rated more credible than unquantified
claims in recruiter-preference studies and style guides.

**Bad:**
- "Improved application performance significantly"

**Good:**
- "Improved application performance by 40%, reducing p99 latency from 800ms to 120ms"

**Fix hint:** Add metrics: percentages, counts, dollar amounts, or time saved.

---

### wl-003: noise-skills

**Category:** writing | **Sections checked:** skills | **Severity:** warning

Flags skills that appear in a built-in noise list. These are commodity office-suite tools
that add no signal to a technical CV:

- Microsoft Office, Microsoft Word, Microsoft Excel, Microsoft PowerPoint
- Google Docs, Google Sheets, Google Slides
- MS Office, MS Word

**Basis:** commodity office tools are assumed baseline for knowledge work; listing them
dilutes the signal of specialised skills.

**Fix hint:** Remove it or replace with a more specific/valuable skill.

---

### wl-004: weak-action-verbs

**Category:** writing | **Sections checked:** work, education, projects | **Severity:** warning

Flags highlights that begin with one of these weak openers:

- helped, assisted, worked on, was responsible for, participated in, was involved in, contributed to

**Basis:** weak openers describe involvement rather than ownership; strong action verbs read
as accountability for the outcome.

**Bad:** "Helped the team implement the new API"

**Good:** "Implemented the new API, reducing integration time by 30%"

**Fix hint:** Start with a strong action verb: 'Designed', 'Implemented', 'Reduced', 'Delivered', 'Architected'.

---

### wl-005: highlight-length

**Category:** writing | **Sections checked:** work, education, projects | **Severity:** warning

- **Too short:** fewer than 8 words — lacks context, impact, or specificity.
- **Too long:** more than 25 words — hard to scan; split or tighten.

**Basis:** the 8–25 word band keeps bullets skimmable while carrying enough context; extreme
lengths reduce readability either way.

---

### wl-006: bullet-count

**Category:** structure | **Sections checked:** work | **Severity:** warning

- **Too few:** fewer than 3 highlights per work entry — insufficient detail for the role.
- **Too many:** more than 8 highlights — dilutes focus; cut the weakest bullets.

**Basis:** structural convention that keeps each role substantiated without overwhelming the
reader (and keeps the document a scannable length).

---

### wl-007: first-person

**Category:** writing | **Sections checked:** work highlights, projects highlights, basics summary | **Severity:** warning

Flags uses of: `I`, `my`, `me`, `mine`, `myself` (case-insensitive).

**Basis:** the implied-first-person resume convention — bullets omit the subject pronoun.

**Bad:** "I led a team of 5 engineers to deliver the API."

**Good:** "Led a team of 5 engineers to deliver the API."

---

### wl-008: vague-buzzwords

**Category:** writing | **Sections checked:** work highlights, projects highlights, basics summary | **Severity:** warning

Flags overused, low-signal terms: motivated, detail-oriented, team player, hardworking,
passionate, dynamic, results-driven, go-getter, synergy, proactive, self-starter, innovative.

**Basis:** these adjectives assert traits without evidence; concrete accomplishments are more
persuasive and are routinely flagged by resume guides.

**Fix hint:** Replace with a specific example or accomplishment that demonstrates the trait.

---

### wl-009: skill-count

**Category:** structure | **Sections checked:** skills (all categories combined) | **Severity:** warning

- **Too few:** fewer than 8 total skills — sparse; add relevant tools and technologies.
- **Too many:** more than 25 total skills — overwhelming; keep only job-relevant items.

**Basis:** a completeness heuristic — too few looks thin, too many reads as unfocused keyword
stuffing.

---

### wl-010: profile-links

**Category:** structure | **Sections checked:** contact | **Severity:** warning

Warns when neither a LinkedIn URL/handle nor a GitHub URL/handle is present in the contact
data or `public_links`.

**Basis:** recruiters expect at least one professional profile link; its absence is a
completeness gap.

**Fix hint:** Add `linkedin:` and/or `github:` to `private/contact.yaml`.

---

### wl-011: page-count

**Category:** structure | **Sections checked:** whole CV (word estimate) | **Severity:** warning

Estimates page count as total words ÷ 500. Warns if estimated pages > 2. Skipped for
`cv/academic` template (academic CVs may be longer).

**Basis:** the 1–2 page convention for non-academic CVs; a longer document risks not being
read in full.

**Fix hint:** Remove the least impactful highlights or shorten descriptions.

---

### wl-012: date-format-consistency

**Category:** ats-parse | **Sections checked:** work, education | **Severity:** warning

Flags mixing of `YYYY-MM` (e.g. `2021-03`) and `YYYY` (e.g. `2021`) date formats within
the same section. Pick one format and use it throughout.

**Basis (ATS-parse):** ATS date parsers are brittle; inconsistent formats within a section
are a common cause of mis-parsed employment timelines.

---

### wl-013: tense-consistency

**Category:** writing | **Sections checked:** work | **Severity:** warning

- **Current role** (end_date = "Present" or missing): highlights should use **present tense**.
- **Past role** (end_date is a year/date): highlights should use **past tense**.

The check looks at the first word of each highlight.

**Basis:** consistent tense is a standard editing convention; mixed tense reads as careless.

**Bad:** "Built new features" in a current role (past tense).

**Good:** "Build new features and ship weekly" in a current role.

---

### wl-014: summary-length

**Category:** structure | **Sections checked:** basics summary | **Severity:** warning

- **Too short:** fewer than 20 words — insufficient to convey value proposition.
- **Too long:** more than 80 words — too dense; recruiters skim summaries.

**Basis:** the 20–80 word band matches how recruiters skim a summary block.

---

### wl-015: action-result

**Category:** writing | **Sections checked:** work, projects | **Severity:** suggestion

Flags highlights that contain a metric (%, $, ×, k/m/b suffix) but lack a result-framing
phrase such as "enabling", "resulting in", "saving", "driving", "reducing", "improving".

**Basis:** the "action → result" bullet structure links effort to business impact, which
resume guidance consistently recommends.

**Bad:** "Refactored the codebase, reducing lines by 40%."

**Good:** "Refactored the codebase, reducing lines by 40% and enabling 3× faster deploys."

---

### wl-016: readability

**Category:** writing | **Sections checked:** work, projects | **Severity:** suggestion

Calculates the Flesch-Kincaid Grade Level for each highlight (treated as a single sentence).
Flags highlights outside the target range of grade 6–12.

- **Grade > 12:** sentence is too complex — too many polysyllabic words or the highlight is
  too long. Simplify vocabulary or split into two bullets.
- **Grade < 6:** sentence is too simple — too short or uses only monosyllabic words.
  Add a metric, scope, or result to increase substance.

**Basis:** Flesch-Kincaid is a well-established readability metric; the 6–12 band keeps bullets
accessible without being simplistic.

**Fix hint (too complex):** Break into shorter phrases or replace multi-syllable words with simpler alternatives.

**Fix hint (too simple):** Expand the highlight with a result, metric, or scope to increase substance.

---

### wl-017: tech-mentions-in-work

**Category:** ats-parse | **Sections checked:** work | **Severity:** suggestion

Cross-references each work entry's highlights against all skill item names. Fires when a
work entry has highlights but none of them mention any skill (case-insensitive substring match).

Skipped when the skills section is empty.

**Basis (ATS-parse):** ATS keyword matching favours skills that appear *in context* within
role descriptions, not only in a skills list; a role that names no technologies is weaker for
keyword retrieval.

**Bad:** A "Senior Python Engineer" role whose highlights mention no technologies at all.

**Good:** At least one highlight references a tool, language, or framework from the skills section.

**Fix hint:** Reference at least one tool, language, or framework from your skills section.

### wl-018: education-size

**Category:** structure | **Sections checked:** education | **Severity:** warning

Fires when the education section has more than 6 entries. Skipped when the education
section is hidden for the profile.

**Basis (structure):** an education list that long is almost always a couple of real degrees
plus a tail of certifications and short courses. Every CV template renders education entries
with equal weight, so the tail visually competes with the degrees and pushes them down the page.

**Bad:** 2 degrees and 21 vendor certifications in one flat `education.yaml`.

**Good:** degrees in `education.yaml`; certifications and short courses in
`certifications.yaml`, which renders as a compact one-line-per-entry section.

**Fix hint:** Move certifications and short courses to `data/certifications.yaml`. Alternatively
tag the tail (e.g. `tags: [certification]`) and filter it out per profile with `include_tags`.
