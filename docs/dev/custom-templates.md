# Custom Templates

[Back to README](../../README.md)

cvloom's templates are Jinja2 HTML files that extend a shared base. You can create custom templates in your project directory — they are automatically discovered and take priority over built-in templates.

---

## Table of Contents

1. [How Template Discovery Works](#how-template-discovery-works)
2. [Template Structure](#template-structure)
3. [Template Blocks](#template-blocks)
4. [Render Context Variables](#render-context-variables)
5. [Custom Jinja2 Filters](#custom-jinja2-filters)
6. [Section Headings](#section-headings)
7. [Separator Convention](#separator-convention)
8. [CSS Variables](#css-variables)
9. [Handling Optional Fields](#handling-optional-fields)
10. [Annotated Example](#annotated-example)
11. [Layout Choices That Break Extraction](#layout-choices-that-break-extraction)
12. [Decorations That Do Not Survive Every PDF Viewer](#decorations-that-do-not-survive-every-pdf-viewer)
13. [Third-Party Template Packages](#third-party-template-packages)

---

## How Template Discovery Works

cvloom looks for templates in two locations, in order:

1. **`templates/` in your project directory** (user overrides and additions)
2. **`cvloom/templates/` in the installed package** (built-in templates)

If a template named `cv/my-template` exists in your project's `templates/cv/my-template.html.j2`, it is used instead of any built-in template with the same path.

To use your custom template, set it in a profile:

```yaml
template: cv/my-template
```

Or override at build time:

```bash
cvloom build --template cv/my-template
```

---

## Template Structure

All CV templates extend `base.html.j2` and override specific blocks. A minimal template looks like:

```jinja2
{% extends "base.html.j2" %}

{% block css_vars %}
--accent: #2563eb;
{% endblock %}

{% block body %}
<div class="resume">
  <header>
    <h1>{{ contact.name }}</h1>
    <p>{{ basics.headline }}</p>
  </header>

  {% if show.work %}
  <section id="work">
    <h2>Experience</h2>
    {% for entry in data.work %}
    <div class="entry">
      <h3>{{ entry.title }} — {{ entry.company }}</h3>
      <span class="dates">{{ entry.start_date | date_range(entry.end_date) }}</span>
      <ul>
        {% for h in entry.highlights %}
        <li>{{ h | md }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endfor %}
  </section>
  {% endif %}
</div>
{% endblock %}
```

---

## Template Blocks

`base.html.j2` defines these blocks:

| Block | Purpose |
|---|---|
| `title` | `<title>` tag content. Default: `{{ contact.name }} — Resume` |
| `head_extra` | Additional `<head>` content (meta tags, etc.) |
| `fonts` | Font declarations (`<link>` tags for web fonts, or `@font-face`) |
| `css_vars` | CSS custom property overrides (inserted into `:root {}`) |
| `css_extra` | Additional CSS rules |
| `body` | The main HTML body content |

Override only the blocks you need. Blocks not overridden use their defaults from `base.html.j2`.

---

## Render Context Variables

These variables are available in every template:

| Variable | Type | Description |
|---|---|---|
| `contact` | dict | Contact data from `private/contact.yaml` (`name`, `email`, `phone`, `location`) |
| `basics` | dict | From `data/basics.yaml` (`headline`, `summary`, `links`) |
| `work` | list | Work entries after filtering and overlay application |
| `education` | list | Education entries |
| `skills` | list | Skill categories with items |
| `projects` | list | Project entries |
| `profile` | dict | The raw profile YAML (`template`, `output_filename`, `select`, etc.) |
| `publications` | list | Publication entries |
| `certifications` | list | Certification entries (render them through the `cert_groups` filter) |
| `awards` | list | Award entries |
| `languages` | list | Language entries |
| `show` | dict | Section visibility flags, one per orderable section. Value: `True`/`False` |
| `section_order` | list | Ordered list of section names to render |
| `section_titles` | dict | Heading overrides from the profile. Read it through the `section_title` global, not directly |
| `locale` | LocalePack | The project's locale pack (`html_lang`, `section_titles`, `ongoing`, `placeholder_contact`). `base.html.j2` uses `locale.html_lang`; otherwise reach it through `section_title` and `date_range` |
| `job_context` | dict | From `job_context:` in the profile (`company`, `role`, `hiring_manager`, `notes`); keys always present, empty string when unset |
| `public` | bool | `True` when built with `--public` |
| `today` | str | Current date formatted as `"Month DD, YYYY"` |

**Work entry fields:** `company`, `title`, `location`, `start_date`, `end_date`, `highlights` (list of strings), `tags`

**Education entry fields:** `institution`, `degree`, `field`, `location`, `start_date`, `end_date`, `highlights`

**Skills category fields:** `category` (string), `items` (list of strings or `{name, level}` dicts)

**Project entry fields:** `name`, `description`, `url`, `start_date`, `end_date`, `highlights`, `tags`

**Publication entry fields:** `name`, `publisher`, `release_date`, `identifier`, `url`, `summary`, `tags`

**Certification entry fields:** `name`, `issuer`, `type`, `date`, `expiry_date`, `identifier`, `url`, `tags`

**Award entry fields:** `title`, `awarder`, `date`, `summary`, `tags`

**Language entry fields:** `language`, `fluency`

---

## Custom Jinja2 Filters

These custom filters are available in all templates:

### `md`

Renders a Markdown string to HTML. Unwraps single `<p>` tags for inline use.

```jinja2
{{ "**Strong** and _emphasis_" | md }}
{# → <strong>Strong</strong> and <em>emphasis</em> #}

{{ entry.description | md }}
```

### `date_range`

Formats a date range from two date strings, using the locale pack's open-ended word
("Present" in `en`) as the fallback for missing end dates. Identical endpoints collapse to
a single date, so a qualification known only by its completion year renders "2017", not
"2017 – 2017".

```jinja2
{{ entry.start_date | date_range(entry.end_date) }}
{# → "2021-03 – Present" or "2018-06 – 2021-02" #}

{{ entry.start_date | date_range(entry.end_date, sep="-") }}
{# → "2021-03 - Present" — see Separator Convention below #}
```

### `skill_level_bar`

Renders a skill proficiency indicator as an HTML span with a CSS class.

```jinja2
{% if item.level is defined %}
{{ item.level | skill_level_bar }}
{% endif %}
{# → <span class="skill-level skill-level-3" aria-label="advanced"></span> #}
```

Level-to-number mapping: `beginner` → 1, `intermediate` → 2, `advanced` → 3, `expert` → 4.

Style `.skill-level-1` through `.skill-level-4` in your CSS to control the visual appearance.

> **This renders an empty `<span>`.** The proficiency is carried entirely by a CSS class,
> so there is **no text in the PDF** and no parser can read it. None of the built-in
> templates use this filter. If proficiency matters to a reader, write it as text
> (`Python (expert)`); a bar is decoration that also happens to be invisible to an ATS.

### `link_anchor`

Renders one `basics.links` entry as an anchor whose visible text is the URL itself.

```jinja2
{% for link in basics.links | default([]) %}
<span>{{ link | link_anchor }}</span>
{% endfor %}
{# → <span><a href="https://github.com/jane">github.com/jane</a></span> #}
```

Use this rather than hand-writing `<a href="…">{{ link.label }}</a>`. ATS parsers
split on whether they read visible text or the `href`; anchor text that hides the
URL leaves the text-reading half with nothing usable. The filter trims only the
scheme and `www.` from the display text, so both halves get a complete address,
and WeasyPrint turns the `href` into a real PDF link annotation for the human
reader.

### `cert_groups`

Splits `certifications` into its rendered groups, yielding `(title_key, entries)` per
group. Credentials (`type: certification` / `license`) come first, coursework
(`type: course` / `micro-credential`) second, and a group with no entries is omitted —
so a file of nothing but courses gets an accurate heading rather than one claiming they
are certifications.

```jinja2
{% for title_key, group in certifications | cert_groups %}
<h2>{{ section_title(title_key) }}</h2>
{% for cert in group %}…{% endfor %}
{% endfor %}
```

`title_key` is `"certifications"` or `"professional_development"` — pass it to
`section_title` so the locale supplies the wording and a profile can rename each group.
The filter deliberately yields no heading text: that is the thing being overridden.

---

## Section Headings

`section_title(key)` is a Jinja **global**, not a filter. Route **every** heading through
it — a hardcoded `<h2>Skills</h2>` is neither renameable nor translatable:

```jinja2
<h2>{{ section_title("skills") }}</h2>
```

Three things can decide the wording, narrowest winning:

| Source | Who owns it |
|---|---|
| `section_titles` in the profile | The user, per output variant. The only customization mechanism |
| The project's locale pack (`cvloom/locales/<code>.yaml`) | The default, one flat heading per key |
| The optional second argument, `section_title(key, "Fallback")` | Your template, for a key no pack carries |

A packaged template passes **no** fallback. If your design reads better with different
wording — "Core Competencies" rather than "Skills" — that is a *suggestion*, declared in
`cvloom/templates_meta.py` as `TemplateInfo.suggested_titles` and printed by
`cvloom list-templates` as a `section_titles:` block the user pastes into a profile. Two
mechanisms competing for one heading is what that split avoids.

Valid keys are `cvloom.sections.TITLE_KEYS`; the profile schema and every locale pack
enumerate the same list, so a template asking for a key outside it falls through to your
fallback and a profile setting one fails validation. Adding a key means adding it in all
three places — `TITLE_KEYS`, `profile.json`, and `locales/en.yaml`, whose completeness
test enforces exactly that.

Both `section_titles` and `locale` are read off the render context rather than injected as
callables, so a template renders fine when a caller supplies neither — which matters
because `render_template` is public API and is called directly by tests and by the MCP
server.

**Head sections with `<h2>`.** `tests/test_locale_qa.py` is what stops English creeping
back into a packaged template: it renders under a pseudo-locale that brackets every
pack-sourced string and fails on any heading the pack does not own. It finds those
headings by extracting `<h2>` elements, because that is what all six packaged templates
use. A section headed with an `<h3>` or a styled `<div>` is not audited, so a hardcoded
literal there would ship unnoticed. If a design genuinely needs a different element,
widen `_H2_RE` in that test in the same change.

---

## Separator Convention

If you are writing a template meant to survive an unknown ATS, join fields with ASCII:
`|` between contact-line fields, `,` between a role and its organisation. Design-led
templates may use a middot (`·`); the built-in `cv/ats-clean` and `cv/academic` do not,
because U+00B7 depends on the embedded font subset carrying the glyph while ASCII does not.
Extraction is not the issue — every separator extracts cleanly from a WeasyPrint PDF.

Date ranges are ASCII everywhere. `date_range` defaults `sep` to a hyphen, and every
built-in template and every export format uses it, so one dash character appears across
the whole document set:

```jinja2
{{ job.start_date | date_range(job.end_date | default(none)) }}
{# "2021-03 - Present" #}
```

An en dash is better typography for a range, but a CV is meant to be machine-read: a
document mixing `-`, `–` and `—` gives a parser three things to handle instead of one.
`wl-023` flags non-ASCII dashes left in your own content.

`tests/test_renderer.py` asserts the two ASCII-first templates emit no middot and no en
dash, and that the four design-led ones still do, so drifting either way fails the suite.

---

## CSS Variables

`base.html.j2` defines these CSS variables in `:root`. Override them in the `css_vars` block:

| Variable | Default | Description |
|---|---|---|
| `--accent` | `#1a56db` | Primary accent color |
| `--text` | `#111827` | Body text color |
| `--muted` | `#6b7280` | Secondary/muted text |
| `--border` | `#e5e7eb` | Border color |
| `--bg` | `#ffffff` | Background color |
| `--font-body` | `Arial, Helvetica, sans-serif` | Body font stack |
| `--font-mono` | `"Courier New", monospace` | Monospace font |
| `--page-width` | `210mm` | Page width for print |
| `--page-padding` | `18mm 16mm` | Page padding for print |

Example:

```jinja2
{% block css_vars %}
:root {
  --accent: #4a5568;
  --font-body: Lato, Calibri, Arial, sans-serif;
}
{% endblock %}
```

### What base owns, and what you own

`base.html.j2` owns the document skeleton, the design tokens, element-level typography,
the print setup, and the **cross-cutting correctness rules** — kerning off, pagination,
heading semantics. It reaches your template through element selectors and a small shared
**role vocabulary**. It does not know your class names, and it must not: a rule keyed on
one template's class is a guarantee that applies only if base has heard of you.

Everything visual is yours. You opt into base's guarantees by using the role classes.

| Role class | What base guarantees |
|---|---|
| `.entry` | `break-inside: avoid` and `orphans`/`widows` of 2 — an entry is not split across a page break |
| `.entry-title` on an `<h3>` | Inherited size and bold weight, so the title is a real heading in the PDF structure tree |
| `.entry-meta`, `.entry-date`, `.entry-location`, `.entry-sep` | One size and family across the meta line; override `.entry-meta`, never the individual fields |
| `.contact-line` | Anchors inside it inherit the surrounding colour, so a header on an accent background stays legible |
| `.skill-level*` | The rendering of whatever `skill_level_bar` emits — you call the filter, base draws the bar |

`h2` and `h3` get `break-after: avoid` as elements, so a heading never strands at the
foot of a page. That is one reason section titles must be real headings.

**A skin goes alongside a role, never instead of it.** `cv/timeline-clean` styles its
entries as timeline nodes and writes:

```html
<div class="entry timeline-entry">
```

`entry` is the role — base protects it from splitting. `timeline-entry` is the skin —
the template styles it and base has never heard of it. Writing only `timeline-entry`
is what a template did before, and it worked solely because base had been taught that
name; every *other* template that invented an entry class silently lost its page-break
protection.

`tests/test_renderer.py` enforces both halves: base may not style a class fewer than two
packaged templates use, and no packaged template may render a `*-entry` box without the
`entry` role.

---

## Handling Optional Fields

The Jinja2 environment uses `StrictUndefined` — accessing an undefined variable raises an error. Always guard optional fields with `is defined`:

```jinja2
{% if entry.location is defined %}
<span class="location">{{ entry.location }}</span>
{% endif %}

{% for link in basics.links | default([]) %}
{{ link | link_anchor }}
{% endfor %}

{% if job_context and job_context.company is defined %}
<p>Application to {{ job_context.company }}</p>
{% endif %}
```

---

## Annotated Example

A complete minimal CV template:

```jinja2
{# templates/cv/minimal.html.j2 #}
{% extends "base.html.j2" %}

{# Load a web font #}
{% block fonts %}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
{% endblock %}

{# Override CSS variables #}
{% block css_vars %}
--accent: #0f766e;
--font-body: "Inter", Arial, sans-serif;
{% endblock %}

{# Extra CSS for this template #}
{% block css_extra %}
.resume { max-width: 800px; margin: 0 auto; padding: 2rem; }
.entry-meta { color: var(--muted); font-size: 9.5pt; }
{% endblock %}

{# Main content #}
{% block body %}
<div class="resume">

  {# Header #}
  <header>
    <h1>{{ contact.name }}</h1>
    {% if basics.headline is defined %}
    <p class="muted">{{ basics.headline }}</p>
    {% endif %}
    {% if basics.summary is defined %}
    <p>{{ basics.summary | md }}</p>
    {% endif %}
  </header>

  {# Render sections in profile-defined order #}
  {% for section in section_order %}

    {% if section == "work" and show.work %}
    <section>
      <h2>Experience</h2>
      {% for entry in work %}
      <div class="entry">
        <h3 class="entry-title">{{ entry.title }}</h3>
        <div class="entry-meta">
          <span class="entry-org">{{ entry.company }}</span>
          <span class="entry-sep"> | </span>
          <span class="entry-date">{{ entry.start_date | date_range(entry.end_date) }}</span>
          {% if entry.location is defined %}
          <span class="entry-sep"> | </span>
          <span class="entry-location">{{ entry.location }}</span>
          {% endif %}
        </div>
        <ul>
          {% for h in entry.highlights %}
          <li>{{ h | md }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endfor %}
    </section>
    {% endif %}

    {% if section == "skills" and show.skills %}
    <section>
      <h2>Skills</h2>
      {% for category in skills %}
      <p>
        <strong>{{ category.category }}:</strong>
        {% for item in category.items %}
          {% if item is string %}{{ item }}{% else %}{{ item.name }}{% endif %}{% if not loop.last %}, {% endif %}
        {% endfor %}
      </p>
      {% endfor %}
    </section>
    {% endif %}

    {# Education and projects sections follow the same pattern #}

  {% endfor %}
</div>
{% endblock %}
```

---

## Layout Choices That Break Extraction

Every ATS extracts the PDF's text layer before it parses anything, and a layout can
scramble that without looking wrong on the page. Three rules, all measured against
WeasyPrint output — see [ATS-readiness](../reference/ats-readiness.md):

**Cap heading `letter-spacing` at `.08em`.** WeasyPrint writes it as real inter-glyph
advance, and extractors reinsert a word break past roughly that point: `EDUCATION` comes
back as `E D U C AT I O N`. Section headings are what a parser segments on, so a tracked
heading costs its whole section a label. The built-in templates use `.06em`, and
`tests/test_renderer.py` fails the build above `.08em`.

**Do not right-align the date.** It leaves an empty vertical band down the page, which
poppler and pdfminer read as a column and use to lift dates out of their entries. How wide
that band gets depends on the user's bullet length, so no styling makes it safe. Put the date
on the entry's meta line — `company · date · location` — as the packaged templates do.
`tests/test_renderer.py` fails any packaged template that styles an `.entry-header`.

**Use real heading elements.** Section titles and entry titles must be `<h2>` and `<h3>`, not
styled `div`s: headings are what a parser segments a CV on, and a `div.section-title` reaches
the PDF structure tree as an anonymous `/Div`. `tests/test_extraction_fidelity.py` asserts
`/H1`, `/H2` and `/H3` are all present in the built PDF.

**Two columns interleave.** There is no styling that fixes it; `cv/sidebar-compact` is
kept and labelled rather than fixed. Use one column unless a human is the only reader.

If you add a template to the package, add it to `cvloom/templates_meta.py` — a test fails
for any packaged `cv/` template without an entry. A template of your own under
`templates/` shows as `unrated` in `cvloom list-templates`, which means "never measured",
not "safe".

---

## Decorations That Do Not Survive Every PDF Viewer

A rule, a dot or a bar can be correct in the browser, correct in `pdftoppm`, and
missing in the viewer your reader actually opens the file in. Two rules, both
measured against WeasyPrint output:

**Draw hairlines as a solid fill, never as a gradient.** WeasyPrint emits every CSS
gradient as a form XObject containing a shading, inside a transparency group, with a
BBox covering the whole page — the visible part is produced by *alpha in the colour
function*, not by geometry. For a filled shape that is fine. For a 2px rule it is not:
viewers rasterize the soft mask at their own resolution, and a 2px feature can be
sampled away completely. `cv/timeline-clean` drew its vertical rule as a
`linear-gradient` with hard colour stops and the line rendered in poppler and vanished
elsewhere. Use `border-left`, or a `background-color` on a sized box — both reach the
PDF as a plain filled rectangle. `tests/test_extraction_fidelity.py` fails the build if
`cv/timeline-clean` emits an axial (type 2) shading at all.

**Do not use `position` to place a decoration.** Positioned boxes paint in a later pass
than in-flow content, and that pass is also where they land in the PDF's content
stream — an absolutely positioned timeline dot moved the *entire* timeline after the
sections that follow it, so `SKILLS` and `EDUCATION` extracted from the middle of the
work history while the page looked untouched. Place decorations with backgrounds and
borders on in-flow boxes. When paint order matters — a dot that must sit *on* its
line rather than under it — put the two on different elements: a parent's border paints
before an in-flow child's background, and a negative margin on the child lets it reach
back over that border. `cv/timeline-clean` does exactly this.

---

## Third-Party Template Packages

Third-party template packages use the naming convention `cvloom-template-*`. They install templates into a location that cvloom can discover, following the same lookup order as project-local `templates/`.

When publishing a template package, name it `cvloom-template-<name>` and document which template path it provides (e.g. `cv/my-custom-name`).
