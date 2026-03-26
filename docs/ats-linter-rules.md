# ATS Linter Rules Reference

[Back to README](../README.md)

## Overview

The `cvloom check` command runs 5 built-in rules against a resolved profile to catch
common CV quality issues. The linter inspects highlights (bullet points) in the work,
education, and projects sections, as well as skill items.

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

You can also filter to specific rules by passing rule IDs to the `lint()` function
programmatically.

## Quick Reference

| Rule ID   | Name                    | Sections Checked           | What It Flags                                 |
|-----------|-------------------------|----------------------------|-----------------------------------------------|
| `ats-001` | passive-voice           | work, education, projects  | Passive voice constructions in highlights      |
| `ats-002` | missing-quantification  | work, projects             | Highlights with no numbers at all              |
| `ats-003` | noise-skills            | skills                     | Low-value commodity skills                     |
| `ats-004` | weak-action-verbs       | work, education, projects  | Highlights starting with weak verbs/phrases    |
| `ats-005` | highlight-length        | work, education, projects  | Highlights shorter than 8 or longer than 25 words |

All findings have severity `warning`.

---

## Rule Details

### ats-001: passive-voice

**Sections checked:** work, education, projects

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

**Sections checked:** work, projects (not education)

Flags any highlight that contains no digits at all. Numbers provide concrete evidence of
impact and are strongly preferred by hiring managers and ATS systems.

**Bad:**
- "Improved application performance significantly"

**Good:**
- "Improved application performance by 40%, reducing p99 latency from 800ms to 120ms"

**Fix hint:** Add metrics: percentages, counts, dollar amounts, or time saved.

---

### ats-003: noise-skills

**Sections checked:** skills

Flags skills that appear in a built-in noise list. These are commodity office-suite tools
that add no signal to a technical CV:

- Microsoft Office, Microsoft Word, Microsoft Excel, Microsoft PowerPoint
- Google Docs, Google Sheets, Google Slides
- MS Office, MS Word

The match is case-insensitive.

**Bad:**
- Listing "Microsoft Word" as a skill

**Good:**
- Remove it, or replace with a domain-specific tool

**Fix hint:** Remove it or replace with a more specific/valuable skill.

---

### ats-004: weak-action-verbs

**Sections checked:** work, education, projects

Flags highlights that begin with one of these weak openers (case-insensitive, ignoring
leading dashes/spaces):

- helped
- assisted
- worked on
- was responsible for
- participated in
- was involved in
- contributed to

These phrases dilute ownership and impact. Replace them with strong, specific action verbs.

**Bad:**
- "Helped the team implement the new API"

**Good:**
- "Implemented the new API, reducing integration time by 30%"

**Fix hint:** Start with a strong action verb: 'Designed', 'Implemented', 'Reduced',
'Delivered', 'Architected'.

---

### ats-005: highlight-length

**Sections checked:** work, education, projects

Flags highlights based on word count:

- **Too short:** fewer than 8 words. These lack context, impact, or specificity.
- **Too long:** more than 25 words. These are hard to scan and should be split or tightened.

**Too short -- bad:**
- "Built an API." (3 words)

**Too short -- good:**
- "Built a REST API serving 2M daily active users with sub-100ms latency."

**Too long -- bad:**
- A 30+ word run-on bullet that tries to cover multiple accomplishments in a single highlight and becomes difficult for a reviewer to parse quickly.

**Too long -- good:**
- Split into two focused bullets, each describing one accomplishment with clear metrics.

**Fix hints:**
- Short: "Add context, impact, or metrics to make this bullet more substantial."
- Long: "Split into two bullets or tighten the language."
