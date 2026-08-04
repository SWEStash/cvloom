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
text layer pulled back out — the step every ATS runs first — with **five** extractors that work
differently:

- **construction** reads the page content stream in paint order, applying no layout analysis at
  all. This is what Apache Tika and PDFBox do by default (`sortByPosition=false`), and it is the
  harshest reader in the set.
- **poppler** (`pdftotext`) rebuilds columns from glyph geometry. It is what most Linux PDF
  viewers use for copy/paste and what a great many ingestion pipelines shell out to.
- **pypdf** walks the content stream and re-joins runs by position. Pure Python, common in
  Python document pipelines.
- **pdfminer.six** re-lays out characters itself. Pure Python, and the engine behind a lot of
  Python resume tooling.
- **structure** follows the `/StructTreeRoot` tag tree — the reading order the PDF standard
  actually defines, and the one accessibility tooling uses.

None of them *is* an ATS. Agreement between engines that read the document by different means
is evidence the text layer is unambiguous; it is not a certificate. You can produce these files
for your own CV with `cvloom build --extract-text`, which writes one per engine.

Using one is not enough, and that is the most useful thing this exercise produced. They
disagree, and they disagree destructively: a `float: right` date inside an `overflow: hidden`
header reads perfectly under pdftotext and comes back under pypdf with the title fused to the
date as one unsplittable token. Every template shipped that construct, and the templates rated
safe on pdftotext evidence alone were the ones carrying it. **Only what survives all five is
rated safe.**

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

**Right-aligned dates were removed. The date runs inline on the entry's meta line.**

An entry now reads:

```
Senior Platform Engineer
Acme Corp · 2019-04 - 2023-08 · Berlin, Germany
• Led [N] cloud migrations as a certified AWS and Azure specialist.
```

The reason is not the alignment itself but what it leaves behind. A date at the right margin
puts an **empty vertical band down the page**, and poppler and pdfminer read a band like that
as a column boundary and lift the dates out of their entries. Whether the band exists depends
on how long the user's bullets are:

| Bullet length | construction | poppler | pypdf | pdfminer | structure |
|---|---|---|---|---|---|
| ~30 chars | 0 | 1 | 0 | **14** | 0 |
| ~60 chars | 0 | 1 | 0 | **14** | 0 |
| ~95 chars (cross the band) | 0 | 0 | 0 | 0 | 0 |

Long bullets reach far enough right to break the band up; short ones leave it clean. That makes
it a property of what the user writes, not of the template — a CV that parses today starts
failing when its author tightens a bullet. No CSS setting fixes it: capping the header width
fails too, because the gap grows back whenever a job title is short.

Three things were measured and ruled out along the way:

- **The producer is irrelevant.** WeasyPrint, headless Chrome and a hand-written PDF give
  identical results.
- **Text-run structure is irrelevant.** Emitting the title and date as one `TJ` run with an
  internal offset — what a Word tab stop does — extracts exactly like two separate text
  objects, given the same glyph positions.
- **Tagging does not help these engines.** cvloom emits tagged PDFs (see below) and poppler and
  pdfminer ignore the structure tree entirely.

The one construct that does work is filling the band with glyphs — a dot leader scores 0 under
every engine in a hand-built PDF. It is not used because no CSS implementation reproduces it:
floating or flexing the date to the margin puts it in a separate paint pass, which fixes
poppler and pdfminer and breaks construction order and pypdf instead.

`cv/sidebar-compact` still right-aligns its dates. It is rated caution for a separate reason
and is not intended for a portal.

**cvloom emits tagged PDFs.** `pdf_tags=True` gives the document a `/StructTreeRoot`, so its
logical reading order is stated rather than inferred: headings arrive as `/H1`, `/H2` and
`/H3`, bullet lists as `/L`, `/LI`, `/Lbl`, `/LBody`. Word and Chrome have always done this and
cvloom did not, which was a real gap. It buys nothing with poppler or pdfminer, which ignore
tags; it is what makes the document correct for tag-aware consumers and for accessibility.

Two constraints are enforced by tests:

- Every section title and entry title is a real heading element, not a styled `div`. A
  `div.section-title` looks identical on the page and reaches the structure tree as an
  anonymous `/Div`.
- Every date reads back inside its own entry, under all five engines, on multi-page documents,
  with short bullets — the worst case.

Ratings are derived, not judged. Each template is built and read back with every
installed engine, and the rating follows from how many of them find a defect:

- **✅ safe** — no engine finds one.
- **⚠️ caution** — some do and some do not. Readable by most of the market, scrambled by
  part of it. Minor flags such as alignment artefacts land here.
- **❌ unsafe** — every engine finds one. Nothing reads it correctly.

`tests/test_ats_ratings.py` re-derives every rating on each run and fails if a declared
rating and the measured one disagree, in either direction.

## Template-by-template parseability

| Template | Layout | Extraction verdict |
|---|---|---|
| `cv/ats-clean` | Single column, system fonts | Clean under all five engines. Fetches nothing at build time. Use this for ATS portals. |
| `cv/academic` | Single column, serif, system fonts | Clean under all five engines. Fetches nothing at build time. |
| `cv/modern-single` | Single column | Clean under all five engines. |
| `cv/timeline-clean` | Single column + timeline rule | Clean under all five engines. The timeline rule is a CSS border, so it adds no text. |
| `cv/executive-dark` | Single column, dark header band | Clean under all five engines. The band prints as a filled rectangle, not an image. |
| `cv/sidebar-compact` | **Two column** | **Interleaves under pdftotext**, and its dates read outside their entry there. Clean under the other four, which is exactly why one extractor is not enough. |

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

## Contact icons

Four of the design-led templates put a small mark beside each contact field — envelope,
smartphone, globe, and the LinkedIn/GitHub/website marks. The mark is derived from the URL,
not authored in `basics.yaml`: `links.network_of()` already answers which network a URL
belongs to, and a hand-written `icon:` field would be a second answer nothing could validate
against the first. An unrecognised host gets the generic web mark.

They are inline SVG, and that is the only form that works. An emoji or an icon-font glyph is
a character, so an extractor reads it as part of the address next to it, and an icon font's
Private Use Area codepoints come back as garbage — it would also drag a network dependency
into templates that currently need none. An SVG path is geometry and puts nothing in the
text layer at all.

**What they cost is grouping.** Each mark opens about 1.25em of blank space inside the
contact line, and pdfminer and poppler read a gap that size as a box boundary — the same
effect the right-aligned dates had. The contact line therefore comes back out of the PDF as
several boxes rather than one, sometimes ordered differently than it was written. Every
address, the email and the phone still extract as one uninterrupted token, which is what a
keyword search matches on, so the trade is grouping for legibility. Painting the mark as a
CSS background rather than an inline element fragments identically, so it is the gap and not
the element that does it, and no markup buys it back.

**Two templates are excluded, for different reasons.** `cv/ats-clean` stays text-only
because conservatism is its whole purpose. `cv/academic` centres its contact line, and the
centring turns the fragmentation into something worse: six stacked boxes with symmetric side
gaps trip poppler's column detector outright, and the template measures `caution` instead of
`safe`. Shrinking the mark does not help, because the gap exists at any size. A template
whose rating an ornament would cost does not get the ornament.

**`cv/executive-dark` carries one caveat.** With marks present, poppler emits one contact
field after the first work entry rather than in the header. The value is intact and
parseable, it is simply displaced. Removing the flex layout from its header does not fix
this — it only changes which field moves — so this too is the gap rather than the layout.

**The fields are `white-space: nowrap`, and the separator is deliberately exempt.** A mark
left at the end of a line with its address on the next reads as a rendering bug, and a URL
wrapped mid-token comes back out of the text layer as two tokens. But Jinja leaves no
whitespace between the field spans, so the separator's pseudo-element carries every soft
wrap opportunity on the line: without the exemption the whole contact line becomes one
unbreakable box, the last field renders off the right edge of the page, and poppler drops it
entirely. The visible cost is that a wrapped contact line opens with the separator. Gluing
the separator to the preceding field with a non-breaking space costs the trailing space its
break opportunity in WeasyPrint and puts the overflow back.

`cv/sidebar-compact` is the exception to the `nowrap`: its values carry
`word-break: break-all` for a 190px column, which is the opposite instruction and wins.

## Separators in the conservative templates

`cv/ats-clean` and `cv/academic` use an ASCII `|` between contact fields where the
design-led templates use a middot. Every separator extracts cleanly from a WeasyPrint PDF,
so this is not about extraction — a non-ASCII glyph depends on the embedded font subset
carrying it, and these are the two templates whose purpose is to hold under conditions
nobody measured. `tests/test_renderer.py` enforces it.

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
