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

## How to use this in practice

- Run `cvloom check` to fix **writing** and **structure** issues — these help every reader.
- Run `cvloom match --jd <job.txt>` per application to close **keyword-coverage** gaps against
  the specific role.
- Keep the layout simple (the default single-column templates) for **parseability**; avoid
  text-in-images and multi-column tricks.

No single number replaces doing these three things.
