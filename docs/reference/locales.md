# Locales

[Back to README](../../README.md) · See also: [Writing Lint Rules](ats-linter-rules.md) · [Profiles and Overlays](profiles-and-overlays.md)

A cvloom project is **installed in one language and operates in it**. You write
`data/` in your own language, and cvloom stops injecting English into the
document and stops grading it with English-only rules.

```yaml
# cvloom.yaml, at the project root
locale: es
```

That is the whole configuration. `cvloom init --locale es` writes it for you, and
`cvloom list-locales` shows what each locale covers.

## One project, one language

cvloom does **not** maintain a multilingual single source of truth. There are no
translation files, no `{en: …, es: …}` maps inside your data, and no machine
translation. Two languages means **two project directories**, each with its own
`cvloom.yaml`.

This is a deliberate boundary, not a missing feature. The requirement is to
*operate in* a language, not to translate between them, and every translation
mechanism charges permanent complexity to the schema, the linter, the exporters
and the keyword matcher to serve a need most users do not have. The repo ships
both sides of the pattern as runnable proof: [`examples/`](../../examples/) is an
English project and [`examples-es/`](../../examples-es/) is the Spanish one, and
the only structural difference between them is that file.

## What a locale changes — and what it does not

A locale governs **the rendered document**. The CLI and its terminal output stay
in English by design: `cvloom check` reports Spanish findings about Spanish prose,
but it reports them in English.

Two independent axes, resolved separately:

| Axis | Lives in | Governs |
|---|---|---|
| **Document pack** | `cvloom/locales/<code>.yaml` | The rendered document — `lang` attribute, section headings, the open-ended date word, the `--public` placeholder contact, and a cover letter's greeting, sign-off and date |
| **Linter data** | `cvloom/linter_locales/<code>.py` | How `cvloom check` and `cvloom match` grade the writing — lexicons, thresholds, stop words |

They are keyed by the same locale code but looked up independently, so a language
can have one without the other. A locale with a document pack and no linter module
produces a correctly-written document that is then graded by **English** heuristics.
`cvloom list-locales` reports that as `en fallback`, because the alternative — a
table that implies parity — would promise coverage the tool does not have.

## The document pack

Eight keys, all required in `en` and all optional elsewhere. This is the whole
surface; there is nothing else a pack can set.

| Key | What it is |
|---|---|
| `html_lang` | The `<html lang>` attribute. Drives WeasyPrint hyphenation and the PDF `/Lang` metadata that ATS language detection reads |
| `section_titles` | One default heading per renameable section |
| `ongoing` | The open-ended end date, in both directions: `render` is written into the document, `accepts` is the list parsed back out |
| `duration` | How a tenure is written, e.g. `(2 years 3 months)`. Used only by profiles that set `show_durations` |
| `placeholder_contact` | The stand-in identity for `--public` builds and for a project with no `private/contact.yaml` |
| `cover_letter` | `greeting`, `fallback_salutee` and `closing` — everything a letter says that you did not write |
| `months` | The twelve month names, January first |
| `date_format` | How this language orders a date: a template over `{day}`, `{month}` and `{year}` |

### `ongoing` is bidirectional

This is the key most worth understanding, because it is read as well as written.
`render` is the word that appears in the document. `accepts` is what the
chronology lint rule and the JSON Resume export recognise as "still ongoing" when
they read your data back. `es` renders `Actualidad` but accepts `Actualidad`,
`Presente` and `Actual`, matched case-insensitively.

The practical consequence: **omit `end_date` for a current role** rather than
typing the word yourself.

```yaml
- company: Acme Corp
  title: Senior Backend Engineer
  start_date: "2021-03"
  # no end_date — cvloom fills in this locale's word
```

Writing `end_date: Present` is fine in an `en` project and is still supported. It
is wrong in an `es` one: `es` does not accept `Present`, so it renders as the
literal English word and the chronology rule stops seeing the role as current.
Omitting the field is right in every language, which is why the scaffolded sample
does it that way.

### `duration` is four words and two pieces of punctuation

Read only when a profile turns
[`show_durations`](profiles-and-overlays.md#role-durations) on, which is off by
default — a pack that never fills this in costs a document nothing until then.

```yaml
duration:
  year: año
  years: años
  month: mes
  months: meses
  join: " "
  format: "({value})"
```

Singular and plural are separate keys because the count picks between them:
`(1 año 1 mes)` and `(2 años 3 meses)` come from the same block. The schema
requires all four together, for the same reason it requires both halves of
`ongoing` — a pack with plurals only would write `1 años`.

`join` sits between the years part and the months part, and `format` wraps the
result; both are punctuation rather than words, so a language that prefers
`2 años y 3 meses` or square brackets changes them without any code knowing which
locale it is serving. `format` must contain `{value}`, and the schema rejects a
pack where it does not.

This shape assumes regular pluralisation, which covers `en` and `es`. A language
with real plural *categories* — Polish, Arabic — needs more than two forms and
would need the key to grow; nothing is lost by waiting until such a pack exists.

## Section headings: three sources, narrowest wins

A heading is decided by, in order:

1. **`section_titles` in the profile** — yours, per output variant. The only way
   to customise a heading.
2. **The locale pack** — one flat default per key, in the project's language.
3. **A template suggestion** — wording a particular design reads better with,
   such as `cv/executive-dark`'s "Core Competencies". These are *not* applied
   automatically; `cvloom list-templates` prints each as a pasteable
   `section_titles:` block.

The renameable keys are `work`, `skills`, `education`, `projects`,
`publications`, `certifications`, `awards`, `languages`, `summary`,
`professional_development`, `contact`. See
[Profiles and Overlays → Section Headings](profiles-and-overlays.md#section-headings)
for the profile side and
[Custom Templates → Section Headings](../dev/custom-templates.md#section-headings)
for the template side.

## Cover-letter furniture: two sources, narrowest wins

A letter is mostly your own prose. The rest — the greeting, the name you address
when you have none, the sign-off, the date — comes from the pack, so a Spanish
project does not build a letter that declares `lang="es"` and then says
`Dear Hiring Manager`.

The greeting and the closing take a **profile override**, because they are facts
about the application rather than about the language:

```yaml
# profiles/cover-letter.yaml
template: cover-letter/standard
job_context:
  company: Acme Corp
  hiring_manager: Dana Reyes
  greeting: Estimada        # the pack's default is `Estimado`
  closing: Un cordial saludo,
```

Spanish salutations agree with the addressee — `Estimado`, `Estimada`,
`Estimados` — and no pack can know which one your letter needs. `fallback_salutee`
has no override on purpose: it is only reached when `hiring_manager` is unset, and
setting `hiring_manager` is the way to say who you are writing to.

The date needs nothing from you. `strftime` would read the machine's C locale,
which is English whatever your project says, so cvloom writes the date from the
pack's own `months` and `date_format`.

## Resolution and fallback

The project's locale is read from `cvloom.yaml`; an absent file means `en`.

Within a pack, a **missing top-level key falls back to `en` and emits a warning**
naming the key and the pack. A key missing from `en` itself is an error — `en` is
the completeness contract, and a test asserts that every value the code looks up
has an `en` default.

One gap has no warning: `section_titles` falls back as a whole key, not per
heading. A pack that defines `section_titles` but omits `education` does not
inherit the English "Education" — `section_title` falls through to the raw key and
heads the section `education`. `cvloom list-locales` reports those as unnamed
headings, which is the only place they surface.

## What "partial support" means

`cvloom list-locales` gives two coverage figures per locale:

```
Locale  Document  Lint rules               Lint data
en      complete  24 of 25 · skips wl-025  native
es      complete  24 of 25 · skips wl-016  native
```

- **Document** — whether the pack supplies every key and every heading in its own
  words, or leans on `en` for some of them.
- **Lint rules** — how many of the writing-lint rules have an implementation for
  this language. Counts come from the rule registry, never from a literal.
- **Lint data** — whether the grader has a lexicon for this language (`native`) or
  is applying English heuristics (`en fallback`).

Both shipped locales are complete on both axes. The rule skips are not gaps in the
locale but properties of the rules: `wl-016` (readability) is English-only because
Fernández Huerta and INFLESZ are ease scores on a different scale, and `wl-025`
(missing diacritics) is Spanish-only because English has none.
[Writing Lint Rules → Locales](ats-linter-rules.md#locales) has the full per-rule
breakdown: which rules are language-neutral, which are ported with a lexicon,
which were redesigned, and why.

`cvloom check` ends with the same coverage line, so a clean result never quietly
means fewer rules ran.

## Adding a locale

Two files, and the second is optional.

**1. The document pack — required.** Copy `cvloom/locales/en.yaml` to
`cvloom/locales/<code>.yaml` and translate the values. It is validated against
`cvloom/schemas/locale.json` at load, so a malformed pack fails with its own path
rather than at render time. Two things to get right:

- Give `ongoing` both `render` and `accepts`. The schema requires them together,
  because a pack with only the rendered form would stop recognising its own
  output when the chronology rule and the JSON Resume export read it back.
- Give `duration` all four words plus `join` and `format`. Same reason: the count
  picks between singular and plural, so a pack with one of each pair would write
  `1 años`. Keep `{value}` in `format`.
- Cover **every** key in `section_titles`. A missing one heads the section with
  its raw key, silently.
- Translate **all twelve** `months`. The schema requires exactly twelve, so a
  short list fails at load rather than shipping one English month for one month
  of the year — and set `date_format` to the order the language writes
  (`{day} de {month} de {year}` for `es`).

`cover_letter.greeting` is the pack's best single default. Where a language's
salutation agrees with who receives it, the per-application form belongs in the
profile — see the section below.

A pack that ships with cvloom must be complete: `tests/test_locale.py` is
parametrised over every shipped pack and fails on any fallback warning.

**2. The linter data — optional.** Add `cvloom/linter_locales/<code>.py` with a
`LOCALE` object and register it in that package's `_registry()`. Without it,
`pack_for()` falls back to `en` and the language gets a correct document graded by
English heuristics — a real state, reported honestly rather than hidden.

The lexicons are Python rather than YAML on purpose: they are the tool's editorial
judgement, not your configuration. `section_titles` in the pack is content you
own; a weak-verb list is not.

Rules declare which locales they support, so a rule with no implementation for
your language is skipped and named rather than being applied wrongly.
