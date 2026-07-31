# ATS-readiness: the honest model

[Back to README](../../README.md) · See also: [Writing lint rules](ats-linter-rules.md)

cvloom takes ATS (Applicant Tracking System) compatibility seriously — which is exactly why
it does **not** print a single "ATS score 0–100". This page explains what an ATS actually
does, why a universal score would be dishonest, and the three measurable axes cvloom reports
instead.

## What an ATS actually does

An ATS (Workday, Greenhouse, Lever, Taleo, iCIMS, …) does three things:

1. **Parses** your resume file into structured fields (name, contact, work history, education,
   skills). Parsing quality depends on the *document*: a real text layer (not a scanned image),
   a single-column layout, standard section headings, standard date formats.
2. **Indexes and stores** the parsed data.
3. Lets a recruiter **search, filter, and rank** candidates — usually by keyword overlap
   against a specific job requisition.

No ATS emits a "score". The "ATS score" that some tools display is *their own invented
heuristic* — typically a job-description keyword-match percentage plus a few formatting checks.
It is a proxy marketed as a measurement.

## Why a single universal score would be dishonest

1. **No ground truth.** ATS platforms are closed and recruiter-configured. There is no public
   dataset of "resume → passed/failed screening at company X", so a predictive score cannot be
   calibrated or validated. (Even commercial tools' scores are unvalidated against real
   outcomes.)
2. **It's job-relative, not absolute.** The single most predictive real signal — keyword and
   skill overlap — only exists *relative to a specific job description*. A number computed
   without a JD is meaningless by construction.
3. **Behaviour varies per vendor.** What breaks one ATS's parser doesn't break another's. A
   tool-agnostic number averages away the only thing that matters.

So cvloom reports the parts that *are* deterministic and defensible, labelled honestly, and
leaves the rest to the human.

## The three axes cvloom reports

| Axis | What it is | Where cvloom provides it |
|---|---|---|
| **Writing quality** | Deterministic content heuristics (voice, verbs, quantification, tense, readability, buzzwords). Correlates with recruiter preference, not ATS parsing. | `cvloom check` — rules tagged `writing`. See [writing lint rules](ats-linter-rules.md). |
| **JD keyword coverage** | Deterministic *given a job description*: how many of the JD's keywords/skills your CV contains. | `cvloom match --jd FILE` |
| **Parseability** | The real ATS failure mode: is the rendered PDF machine-readable, single-column, standard-headed, consistently dated? | Partly `cvloom check` rules tagged `ats-parse` (dates, in-context keywords); the rest is a *rendering* concern — see the limitation below. |

The `cvloom check` output and the `check_cv` MCP tool tag every finding with its axis
(`writing` / `structure` / `ats-parse`), and print a per-axis breakdown instead of a score.

## The parseability limitation (stated plainly)

The strongest parseability signal is the structure of the **rendered PDF** itself. cvloom
currently renders HTML → PDF via WeasyPrint, which produces a real text layer and a
single-column, standard-headed layout, but **not** a fully tagged PDF/A the way a Typst-based
pipeline (e.g. RenderCV) does. In practice cvloom's output parses well in mainstream ATSes, but
we don't claim tagged-PDF/A compliance. A Typst/tagged-PDF export backend is on the roadmap;
until then, this axis is reported honestly rather than overstated.

## What the templates actually do (measured)

The claims above are checkable, so they are checked. Each template is rendered to PDF and the
text layer pulled back out — the step every ATS runs first — with **two** extractors that work
differently:

- **poppler** (`pdftotext`) rebuilds columns from glyph geometry. It is what most Linux PDF
  viewers use for copy/paste and what a great many ingestion pipelines shell out to, and it is
  the strictest of the three about column layout.
- **pypdf** follows the PDF content stream in paint order. Pure Python, common in Python
  document pipelines.
- **pdfminer.six** re-lays out characters itself. Pure Python, and the engine behind a lot of
  Python resume tooling.

None of them *is* an ATS. Agreement between engines that read the document by different means
is evidence the text layer is unambiguous; it is not a certificate. You can produce these files
for your own CV with `cvloom build --extract-text`, which writes one per engine.

Using one is not enough, and that is the most useful thing this exercise produced. The two
disagree, and they disagree destructively: a `float: right` date inside an `overflow: hidden`
header reads perfectly under pdftotext and comes back under pypdf with the title fused to the
date as one unsplittable token. Every template shipped that construct, and the templates rated
safe on pdftotext evidence alone were the ones carrying it. **Only what survives both is rated
safe.**

Three things showed up that no amount of clean HTML prevents.

**Kerning puts spaces inside words.** The subtlest of the lot. WeasyPrint emits a kerned
pair as two positioned runs, and an extractor reads a large enough jump as a word break:
`PAYPAL` extracts as `P AYP AL`, `AVATAR` as `A V ATAR`, `WAVE` as `WA VE`. The page is
perfect and the word a recruiter searches for is not in the document. Any employer or
skill containing PA, AV, AW, Ta, Wa or Vo was exposed. `font-kerning: none` on `body`.

**Small vertical gaps merge two lines.** pypdf infers a line break from the vertical delta
between text runs; below roughly 0.3em of the heading's size it emits none. The 2px under
the name welded it to the headline with no break between them — the worst field on
the page to corrupt. Every heading gap is now expressed in `em` so it scales with the
template's type size instead of clearing the threshold at one size and missing at another.

**Wide letter-spacing destroys headings.** WeasyPrint writes CSS `letter-spacing` as real
inter-glyph advance in the PDF. Past roughly `.08em` at heading sizes, extractors read the gaps
as word breaks: `EDUCATION` comes back as `E D U C AT I O N`. Section headings are the anchors a
parser segments the document on, so a tracked heading costs its section its label. Every
template now caps heading tracking at `.06em`, and `tests/test_renderer.py` fails the build
above `.08em`.

**Right-aligned dates cannot be made safe. No template uses them.**

A date pushed to the right margin is a separate text column however it is built, and poppler
flushes a column when the **page** ends rather than when the entry does. The last entry on
every page therefore had its date emitted after its own bullets and welded to whatever came
next:

```
• Worked across PHP, Python, Java, JavaScript, and front-end frameworks.
2002-06 - 2008-12Customer Facing Engineer
```

Six constructs were measured — `float`, clearfix, `flow-root`, absolute positioning, CSS table
cells, flexbox — and all six fail the same way. Leader dots are the only construct that works,
because they make the line one continuous run, and they are disqualified on other grounds:
filling that gap needs hidden or near-invisible text, which is what ATS vendors flag as keyword
stuffing.

So the date sits inline next to the title. The right-hand scan column recruiters use is a real
loss, and it was never real in the first place — it did not survive being read.

## Template-by-template parseability

| Template | Layout | Extraction verdict |
|---|---|---|
| `cv/ats-clean` | Single column, system fonts | Clean in both. Fetches nothing at build time. Use this for ATS portals. |
| `cv/academic` | Single column, serif, system fonts | Clean in both. Fetches nothing at build time. |
| `cv/modern-single` | Single column | Clean in both. |
| `cv/timeline-clean` | Single column + timeline rule | Clean in both. The timeline rule is a CSS border, so it adds no text. |
| `cv/executive-dark` | Single column, dark header band | Clean in both. The band prints as a filled rectangle, not an image. |
| `cv/sidebar-compact` | **Two column** | **Interleaves under pdftotext** — see below. Clean under pypdf, which is exactly why one extractor is not enough. |

Audited over a tagged corpus: 8 work entries with 0–4 bullets, 15 skill categories with
labels from 3 to 28 characters, 3 education entries, titles short enough to leave a wide
gutter and long enough to fill the row, across page breaks. Every token is checked for
presence, ownership, and order.

These ratings are not just prose: they live in `cvloom/templates_meta.py`, `cvloom
list-templates` prints them, and `build` and `check` both print the caveat for any
template not rated safe. That matters because the failure is invisible from the
artefact the user is looking at — the PDF renders beautifully, and it is the copy
the ATS makes of it that is scrambled.

## Aligned skills columns

A skills section reads fastest when the values line up in a column, and the three
design-led templates align them. This looked like an unavoidable trade at first — the
whitespace doing the aligning is what an extractor reads as a column boundary, so a short
label comes back on its own line ahead of its values. That much is cosmetic: the order is
preserved and nothing is lost.

The real defect was next to it and easy to miss. The gutter is CSS padding, so when a
label fills its cell there is no character at all between it and the first value, and
pypdf emitted `CloudOpsAWS` — category and skill fused into one token that no keyword
search will ever match. The fix is a colon after every label: it costs nothing visually,
it is what a labelled list conventionally looks like, and it guarantees a separator every
tokeniser splits on regardless of how wide the label is.

`cv/ats-clean` and `cv/academic` still run `Category: items` inline rather than in a
column. Not because alignment is unsafe any more, but because those two are the templates
whose whole purpose is to hold under content shapes nobody measured.

## Multi-page behaviour

All six templates are single-*column*, not single-*page*. Measured on a 17-page
render, `base.html.j2` now carries the pagination rules that make page two look
deliberate: `break-after: avoid` on every heading, `break-inside: avoid` on every
entry and list item, and `orphans`/`widows` of 2. Verified across four templates
at 17 pages each: no section heading is stranded at the foot of a page, and no
job is split from its own bullets.

## The two-column caveat

`cv/sidebar-compact` extracts with sidebar and main content interleaved line by line: a job
title, then a contact label, then the employer, then a skill tag. Contact details and skills
land in the middle of the work-history block. This is the documented failure mode for
two-column resumes generally — it is not a bug in this template so much as what two columns
*are* once the layout is flattened back to text.

It is kept because it is genuinely the best-looking option for a personal site, a PDF attached
to a direct email, or a portfolio link, where a human opens the file and no parser ever touches
it. **Do not upload it to an ATS portal.** Use `cv/ats-clean` there.

## Build-time font fetch

`modern-single` and `sidebar-compact` pull Lato, `timeline-clean` pulls Inter, and
`executive-dark` pulls Source Sans 3, all from Google Fonts at render time. The fonts do embed as subsets in the PDF, so extraction is
unaffected — but the build needs network access, it silently falls back to Arial offline (which
changes pagination), and it discloses the build to a third party. `ats-clean` and `academic`
use system fonts only and are unaffected.


## How to use this in practice

- Run `cvloom check` to fix **writing** and **structure** issues — these help every reader.
- Run `cvloom match --jd <job.txt>` per application to close **keyword-coverage** gaps against
  the specific role.
- Keep the layout simple (the default single-column templates) for **parseability**; avoid
  text-in-images and multi-column tricks.

No single number replaces doing these three things.
