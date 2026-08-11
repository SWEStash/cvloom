# Writing Lint Rules Reference

[Back to README](../../README.md) · See also: [ATS-readiness model](ats-readiness.md)

## Overview

The `cvloom check` command runs 25 deterministic, rule-based checks against a resolved
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

| Rule ID  | Name                    | Category   | Severity   | Locales   | Sections Checked           | What It Flags |
|----------|-------------------------|------------|:----------:|:---------:|----------------------------|---------------|
| `wl-001` | passive-voice           | writing    | warning    | all     | work, education, projects  | Passive voice constructions in highlights |
| `wl-002` | missing-quantification  | writing    | warning    | all     | work, projects             | Entries whose highlights carry no numbers at all |
| `wl-003` | noise-skills            | writing    | warning    | all     | skills                     | Low-value commodity skills |
| `wl-004` | weak-action-verbs       | writing    | warning    | all     | work, education, projects  | Highlights starting with weak verbs/phrases |
| `wl-005` | highlight-length        | writing    | warning    | all     | work, education, projects  | Highlights shorter than 8 or longer than 25 words (`en`; see Locales) |
| `wl-006` | bullet-count            | structure  | warning    | all     | work                       | Fewer than 3 or more than 8 highlights per role |
| `wl-007` | first-person            | writing    | warning    | `en` `es` | work, projects, basics     | Explicit first-person pronouns — the set differs per language |
| `wl-008` | vague-buzzwords         | writing    | warning    | all     | work, projects, basics     | Overused vague terms (e.g. "motivated", "proactive") |
| `wl-009` | skill-count             | structure  | warning    | all     | skills                     | Fewer than 8 or more than 25 total skills |
| `wl-010` | profile-links           | structure  | warning    | all     | contact                    | No LinkedIn or GitHub link present |
| `wl-011` | page-count              | structure  | warning    | all     | (whole CV)                 | Estimated page count exceeds 3 |
| `wl-012` | date-format-consistency | ats-parse  | warning    | all     | work, education            | Mixed YYYY-MM / YYYY date formats |
| `wl-013` | tense-consistency       | writing    | warning    | `en` `es` | work                       | `en`: wrong tense for the role. `es`: bullet styles mixed within a role |
| `wl-014` | summary-length          | structure  | warning    | all     | basics                     | Summary shorter than 20 or longer than 80 words (`en`; see Locales) |
| `wl-015` | action-result           | writing    | suggestion | all     | work, projects             | Metric present but no result-framing phrase |
| `wl-016` | readability             | writing    | suggestion | `en`    | work, projects             | Flesch-Kincaid grade outside target range 6–12 |
| `wl-017` | tech-mentions-in-work   | ats-parse  | suggestion | all     | work                       | Work entry highlights mention no skill item |
| `wl-018` | education-size          | structure  | warning    | all     | education                  | More than 6 education entries — degrees and short courses rendering with equal weight |
| `wl-019` | chronological-order     | structure  | warning    | all     | all dated sections         | A section not ordered newest-first |
| `wl-020` | date-sanity             | ats-parse  | warning    | all     | all dated sections         | End before start, dates in the future, expired credentials |
| `wl-021` | unfilled-placeholders   | structure  | warning    | all     | basics, all entry sections | Scaffold placeholders (e.g. `[Company Name]`) left in the content |
| `wl-022` | duplicate-links         | structure  | warning    | all     | basics                     | Two `links` entries pointing at the same place |
| `wl-023` | non-ascii-dashes        | ats-parse  | info       | all     | all entry sections         | En/em dashes in content, where cvloom emits ASCII |
| `wl-024` | fused-connector         | structure  | warning    | all     | education                  | A `connector` that renders degree and field fused together |
| `wl-025` | missing-diacritics      | writing    | warning    | `es`    | work, education, projects, basics | High-frequency CV terms written without their accent |

---

## Locales

A project declares its language once, in `cvloom.yaml` (see [Locales](locales.md)).
That governs the linter as well as
the document: a CV written in Spanish is graded by Spanish rules, not by English
heuristics applied to Spanish text.

The **Locales** column above says which languages a rule has an implementation
for. `all` means the rule's logic carries no language — dates, counts, ordering,
duplicate links — and it runs everywhere unchanged. The rest fall into three
groups:

**Ported.** Same logic, different data. `wl-003`, `wl-004`, `wl-008` and `wl-015`
carry a lexicon per language; `wl-005`, `wl-011` and `wl-014` carry thresholds.
The word counts in the table above are the `en` values. Spanish uses 10/30 for
highlights and 24/95 for the summary, scaled by a ratio measured from matched
English and Spanish renders of the same CV through the same template — the same
measurement puts about 22% *more* words on a Spanish page, since the expansion
arrives as more short function words rather than as more page.

**Redesigned.** Three rules needed more than a word list, because translating the
English one would produce confident nonsense. `wl-007` and `wl-013` have a
separate implementation per language; `wl-001` keeps one implementation but takes
its constructions from the locale, since the difference there is which shapes to
look for rather than how to judge them.

- `wl-007` **inverts** in Spanish. Spanish is pro-drop, so the subject lives in
  the conjugation and `Lideré la migración` is correct CV style. Only an explicit
  `yo / mi / mis / mí` is a flaw, and the clitic `me` (`me encargué de`) is
  excluded — carrying English's `me` across would flag most well-formed Spanish
  bullets in a document.
- `wl-001` adds the *pasiva refleja* (`se implementó`), which is more common in
  Spanish professional prose than the periphrastic `fue implementado` and has no
  English shape.
- `wl-013` becomes **style consistency** in Spanish. Infinitive bullets and
  first-person preterite bullets are both conventional; mixing them within one
  role is the defect. English's present-vs-past distinction does not transfer,
  because the tense of a Spanish bullet is not tied to whether the role is
  current.

**Language-specific.** `wl-016` runs only in English: Fernández Huerta and INFLESZ
are *ease* scores on a different scale, so the Flesch-Kincaid 6–12 grade band has
no meaning in Spanish and picking a Spanish band is a separate calibration
question. `wl-025` runs only in Spanish.

Coverage is reported rather than assumed. `cvloom check` ends with a line naming
what ran and what did not, so a clean result never quietly means fewer rules:

```
24 of 25 rules ran · 1 skipped (no es support: wl-016 readability)
```

The lexicons themselves live in `cvloom/linter_locales/`, in Python rather than in
a file you edit. They are the tool's editorial judgement, not your configuration —
`section_titles` in the locale pack is content you own, a weak-verb list is not.

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

Flags an **entry** whose highlights contain no digits anywhere — one finding per role or
project, not one per bullet.

**Basis:** quantified achievements are consistently rated more credible than unquantified
claims in recruiter-preference studies and style guides. That evidence supports *the role
showing measurable impact*; it does not support requiring a number in every individual
bullet. Reporting per bullet also buried every other rule under duplicates on exactly the
CVs that needed those rules most. A single quantified highlight satisfies the rule.

**Bad:** a role whose every bullet describes responsibilities — "Managed IT solution
delivery", "Gathered requirements", "Administered databases" — with no outcome anywhere.

**Good:** the same role with at least one bullet reading "Cut operating costs by 30%".

**Fix hint:** Add a metric to at least one bullet: percentages, counts, dollar amounts, or
time saved. Not every bullet needs one.

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

- helped, assisted, worked on, was responsible for, participated in, was involved in

**Basis:** two independent lines of evidence, and they do not cover the list evenly.

University career offices name these phrases directly. Purdue's Business career service
tells students to "avoid starting with 'responsible for,' 'assisted with,' or 'helped
with' as these phrases are a weak representation of your accomplishments". Columbia's
career education guidance names "participated" and "received" among the passive verbs to
replace, and elsewhere lists "Assisted" and "Worked" among openers that describe duties
instead of value added. Yale's advice is the general form: go beyond what you were
responsible for and say what you accomplished, improved or changed. That covers *helped*,
*assisted*, *worked on*, *was responsible for* and *participated in*.

The organisational-psychology literature reaches the same phrases from a different
direction. Madera, Hebl & Martin (2009, *Journal of Applied Psychology* 94, 1591–1599)
found that communal descriptions — "helpful", "kind" — predicted **lower** hireability
ratings than agentic ones, and that the effect held when evaluators did not know the
applicant's gender. Schmader, Whitehead & Wysocki (2007, *Sex Roles*) classify
`responsib*` as a "grindstone" term, the category that co-occurs with *fewer* standout
and ability terms. A 2024 study in the *Journal of Business and Psychology* took this to
résumés specifically, coding more than 2,500 of them from a job board, and found communal
language associated with lower perceived leadership ability and hireability.

**That literature describes a bias, not a merit.** Its central finding is that communal
language is penalised, and that women write more of it — so the effect it documents is
about how applications are *read*, not about how good the work was. cvloom flags these
openers because they cost the user something in a process the user does not control. It is
worth being explicit that this is the reason, rather than implying the flagged phrasing is
inferior writing.

**Not evenly sourced, and deliberately recorded that way.** *was involved in* has no
direct source in either line of evidence; it is kept as the passive-involvement archetype
that *participated in* and *worked on* are attested forms of, at low cost — the fix is
always available and never changes a claim's truth. Anything asserting a specific
percentage lift from action verbs was excluded: that figure circulates widely on
resume-advice sites with no primary study behind it.

**`contributed to` was removed** (and `colaboré en` / `contribuí a` with it). No career
office in the sources above names it, and it is the *accurate* description of genuine team
work. Flagging it told users their truthful framing was a defect, and the only way to
clear the finding was to claim more sole credit than they had — which contradicts
cvloom's own grounding position that a weak but true CV beats a strong invented one, and
which behavioural interviewing is designed to expose anyway. Where the rule and the
honesty contract conflicted, the rule was wrong.

**Bad:** "Helped the team implement the new API"

**Good:** "Implemented the new API, reducing integration time by 30%"

**Fix hint:** Open with the action you took and what it produced, not your involvement in it.

The hint names no verbs, unlike `wl-001`'s. It is rendered into the AI layer's context on
every finding, so a list of five suggested verbs here would be five verbs pushed at every
user of every cvloom project — and the University of Colorado Boulder's career service
reports that exactly this has already happened to the most-recommended ones: recruiters
"often see the same action words on a resume — led, responsible for, managed. And quite
frankly, they have lost their meaning." Naming the shape leaves the vocabulary to the
writer.

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

**In Spanish**, the rule is inverted rather than translated. Spanish is pro-drop,
so `Lideré un equipo de 5 ingenieros` is correct — the subject is in the verb.
Only an explicit `yo / mi / mis / mí` fires, and the clitic `me` never does:
`Me encargué de la plataforma` is idiomatic and clean.

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

**Category:** structure | **Sections checked:** basics | **Severity:** warning

Warns when no entry in `basics.links` points at LinkedIn or GitHub. Networks are recognised
by host, so `linkedin.com/in/jane`, `https://www.linkedin.com/in/jane/`, and anything on a
`linkedin.com` subdomain all satisfy the rule.

**Basis:** recruiters expect at least one professional profile link; its absence is a
completeness gap.

**Fix hint:** Add a LinkedIn or GitHub entry to `links` in `data/basics.yaml`.

---

### wl-011: page-count

**Category:** structure | **Sections checked:** whole CV (word estimate) | **Severity:** warning

Estimates page count as total words ÷ 500. Warns if estimated pages > 3. Skipped for
`cv/academic` template (academic CVs may be longer).

**Basis:** ResumeGo's simulation with 482 recruiters over 7,712 resume choices found
two-page resumes preferred 2.3x over one-page overall, and 2.9x at managerial level — so
the ceiling is set where length starts to cost attention rather than at the folk
one-page rule. `cvloom build` warns at the same threshold.

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

**In Spanish**, `wl-013` is a different rule under the same id: **style
consistency**. A Spanish CV may use infinitive bullets (`Diseñar y mantener la
plataforma`) or first-person preterite ones (`Diseñé y mantuve la plataforma`) —
both are conventional, and neither is a defect. Mixing them within one role is.
Present-vs-past does not transfer, because the tense of a Spanish bullet is not
tied to whether the role is current.

**Bad:** `Diseñar la plataforma de datos.` + `Reduje la latencia un 40%.`

**Good:** `Diseñé la plataforma de datos.` + `Reduje la latencia un 40%.`

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

**English only.** Spanish readability is measured by Fernández Huerta or INFLESZ,
which are *ease* scores on a different scale — the 6–12 grade band does not
translate, and choosing a band for Spanish CV prose is a calibration question of
its own. `check` reports the rule as skipped rather than running it anyway.

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
tag the tail (e.g. `tags: [certification]`) and narrow the section per profile with `select`.

### wl-019: chronological-order

**Category:** structure | **Sections checked:** every section with dates | **Severity:** warning

Fires when a section's entries are not ordered newest-first. Ranking uses the section's own
date fields: `end_date` (falling back to `start_date`) for work, education and projects,
`date` for certifications and awards, and `release_date` for publications. An explicit
`Present` outranks every real date. Entries with no parseable date are ignored, and
`languages` — which has no chronology — is skipped entirely.

**Basis (structure):** cvloom renders entries in the order it loads them and never sorts by
date, so ordering is entirely the author's. Reverse-chronological is the convention readers
scan against: the top of a section is where a recruiter looks for your current role. A
timeline that jumps around also breaks any downstream consumer that infers recency from
position rather than re-reading the dates.

**Note on `projects/`:** projects load from `data/projects/*.yaml` in **filename** order, which
has no relationship to their dates. To order them chronologically, name the files so the
newest sorts first.

**Bad:** work running 2016 → 2009 → 2002 → 2023, with the most recent role fourth.

**Good:** every section strictly newest-first.

**Fix hint:** Reorder the entries newest-first (or rename the files, for `projects/`).

### wl-020: date-sanity

**Category:** ats-parse | **Sections checked:** every section with dates | **Severity:** warning

Flags three impossible or misleading date conditions:

1. **End before start** — an entry whose `end_date` precedes its `start_date`.
2. **Future dates** — any date later than the current month.
3. **Expired credentials** — a certification whose `expiry_date` has passed.

A bare `YYYY` resolves to December when it closes a range and January when it opens one, so
`2020` – `2020-05` is not misread as ending before it starts. `Present` is never a violation.

**Basis (ats-parse):** parsers compute tenure from these fields; a negative range can cause an
entry to be dropped or its dates mis-assigned. Expired credentials are a separate,
human-facing problem — many vendor certifications lapse (AWS certifications, for instance, are
valid for three years), and presenting a lapsed one as current is a credibility risk under
scrutiny.

**Bad:** `AWS Certified Solutions Architect`, `date: "2017"`, no `expiry_date`, presented
alongside current credentials.

**Good:** renew it, remove it, or set `expiry_date` and let the rule tell you when it lapses.

**Fix hint:** Correct the dates; renew, remove, or label lapsed credentials.

### wl-021: unfilled-placeholders

**Category:** structure | **Sections checked:** basics + every entry section | **Severity:** warning

Fires when bracketed placeholder text survives into the rendered CV — `[Company Name]`,
`[N]`, `[X]%`, `[handle]`. Profile link URLs are scanned too, so a scaffolded
`https://github.com/[handle]` is caught before it reaches a PDF. Markdown links are exempt:
`[label](url)` is a link, not a placeholder.

**Basis (structure):** `cvloom init` scaffolds placeholder content by design, and tailoring a
CV per application means repeatedly half-filling entries. Nothing else in the pipeline stops a
placeholder reaching the PDF you attach to an application — schema validation only checks
types, and every other rule reads placeholder text as ordinary prose.

**Bad:** a generated PDF whose first role reads "VP Consulting Services — [Company Name]".

**Good:** every bracket either filled with real content or deleted along with its clause.

**Fix hint:** Replace it with real content, or delete the clause.

---

### wl-022: duplicate-links

**Category:** structure | **Sections checked:** basics | **Severity:** warning

Fires when two `basics.links` entries resolve to the same destination. URLs are compared
after normalising away scheme, `www.`, host case, and a trailing slash, so
`https://www.github.com/jane/` and `github.com/jane` are caught as the one link they are.

**Basis (structure):** a header that lists the same profile twice reads as carelessness, and
the duplicate costs header space that a second real link could use.

**Bad:** a contact line reading `github.com/jane · github.com/jane`.

**Good:** one entry per destination.

**Fix hint:** Remove one of the two entries from `links` in `data/basics.yaml`.

---

### wl-023: non-ascii-dashes

**Category:** ats-parse | **Sections checked:** all entry sections | **Severity:** info

Fires when an entry's text contains an en dash (U+2013), em dash (U+2014) or minus sign
(U+2212).

**Basis (ats-parse):** cvloom renders every date range and separator it controls as an ASCII
hyphen, in every output format — HTML, PDF, DOCX, Markdown. A document that still mixes dash
characters is mixing them because the *content* does. A parser splitting `IEEE - CACIDI` on
the separator has one character to handle; three is three chances to get it wrong. U+2013 also
depends on the embedded font subset carrying the glyph.

**Bad:** `publisher: IEEE – CACIDI`

**Good:** `publisher: IEEE - CACIDI`

**Fix hint:** Replace with `-` so every dash in the document matches.

### wl-024: fused-connector

**Category:** structure | **Sections checked:** education | **Severity:** warning

Fires when an education entry sets `connector`, has both a `degree` and a `field`, and the
connector is padded on neither side.

**Basis (structure):** cvloom supplies no connecting word between degree and field — the
right one is per entry, not per language (`Licenciatura en Informática`, but
`Ingeniero Informático`). The entry's `connector` is therefore written **verbatim**, spacing
included, which makes unquoted YAML a silent trap: `connector: in` loses its spaces and
renders `BScinComputer Science`. Only a connector with no space on either side fuses both
words, so punctuation such as `", "` — correct as `MSc, Computer Science` — does not fire.

**Bad:** `connector: in` → `BScinComputer Science`

**Good:** `connector: " in "` → `BSc in Computer Science`
**Good:** `connector: ", "` → `MSc, Computer Science`

**Fix hint:** Quote it with the spacing you want. Punctuation connectors need only the
trailing space.

---

### wl-025: missing-diacritics

**Category:** writing | **Sections checked:** work, education, projects highlights, basics summary | **Severity:** warning | **Locale:** `es` only

Flags a high-frequency CV term written without its accent — `gestion` for
`gestión`, `analisis` for `análisis`, `tecnico` for `técnico`. The list is closed
and every entry on it is a spelling that is not a Spanish word, so a match is a
typo rather than a judgement call.

Ambiguous pairs are deliberately absent: `publico` is a valid verb form (*yo
publico*) and `ano` is a real word, so flagging either would cost more trust than
the rule earns.

**Basis (writing):** an unaccented `gestion` renders into the PDF exactly as
typed, and reads to a Spanish recruiter the way `managment` reads to an English
one. It is also the cheapest finding in the set to act on.

**Bad:** "Lideré la migracion del sistema de gestion de pagos."

**Good:** "Lideré la migración del sistema de gestión de pagos."

**Fix hint:** Write the accent. It renders into the PDF exactly as typed.
