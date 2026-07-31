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
12. [Third-Party Template Packages](#third-party-template-packages)

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

Formats a date range from two date strings, using "Present" as the fallback for missing end
dates. Identical endpoints collapse to a single date, so a qualification known only by its
completion year renders "2017", not "2017 – 2017".

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

Splits `certifications` into its rendered groups, yielding
`(title_key, default_heading, entries)` per group. Credentials
(`type: certification` / `license`) come first, coursework
(`type: course` / `micro-credential`) second, and a group with no entries is omitted —
so a file of nothing but courses gets an accurate heading rather than one claiming they
are certifications.

```jinja2
{% for title_key, heading, group in certifications | cert_groups %}
<h2>{{ section_title(title_key, heading) }}</h2>
{% for cert in group %}…{% endfor %}
{% endfor %}
```

`title_key` is `"certifications"` or `"professional_development"` — pass it to
`section_title` so a profile can rename each group. Do not reverse-map the visible
heading text: it is the thing being overridden.

---

## Section Headings

`section_title(key, default)` is a Jinja **global**, not a filter. Templates pass their
own wording as *default*, and a profile's `section_titles` overrides it:

```jinja2
<h2>{{ section_title("skills", "Core Competencies") }}</h2>
```

This is how `cv/executive-dark` keeps saying "Core Competencies" while a profile that
sets `section_titles.skills` still wins. Route **every** heading through it — a
hardcoded `<h2>Skills</h2>` is simply not renameable.

Valid keys are `cvloom.sections.TITLE_KEYS`; the profile schema enumerates the same list,
so a template asking for a key outside it gets the default forever and a profile setting
one fails validation. Adding a key means adding it in both places.

It reads `section_titles` off the render context rather than being injected as a callable,
so a template renders fine when a caller supplies no overrides — which matters because
`render_template` is public API and is called directly by tests and by the MCP server.

---

## Separator Convention

If you are writing a template meant to survive an unknown ATS, join fields with ASCII:
`|` between contact-line fields, `,` between a role and its organisation. Design-led
templates may use a middot (`·`); the built-in `cv/ats-clean` and `cv/academic` do not,
because U+00B7 depends on the embedded font subset carrying the glyph while ASCII does not.
Extraction is not the issue — every separator extracts cleanly from a WeasyPrint PDF.

Date ranges follow the same split. `date_range` takes a `sep` argument defaulting to an
en dash; the ASCII-first templates pass `sep="-"`:

```jinja2
{{ job.start_date | date_range(job.end_date | default(none), sep="-") }}
{# ASCII-first: "2021-03 - Present"   design-led: "2021-03 – Present" #}
```

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

Pre-built utility CSS classes from `base.html.j2`: `.muted`, `.right`, `.clearfix`,
`.skill-tag`, `.skill-level`, `.skill-level-{1-4}`.

`base.html.j2` also sets the pagination rules, so you get them for free: `break-after:
avoid` on `h2`/`h3`/`.section-title`, and `break-inside: avoid` plus `orphans`/`widows`
of 2 on `.entry`, `.timeline-entry`, and `li`. Use those class names and a heading will
not strand at the foot of a page, and a job will not split from its own bullets.

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
.entry-header { display: flex; justify-content: space-between; }
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
        <div class="entry-header">
          <strong>{{ entry.title }}</strong> — {{ entry.company }}
          <span class="muted">{{ entry.start_date | date_range(entry.end_date) }}</span>
        </div>
        {% if entry.location is defined %}
        <span class="muted">{{ entry.location }}</span>
        {% endif %}
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

**Right-align a date only on entries that carry a bullet list.** A floated date is its own
geometric column, and an extractor flushes that column when the text beside it ends. On
work, education, and projects the bullets keep it open and the date lands correctly. On
publications, certifications, and awards it closes early and the date surfaces late — in
the worst measured case after the document's final section. Put those inline on the meta
line instead.

**Two columns interleave.** There is no styling that fixes it; `cv/sidebar-compact` is
kept and labelled rather than fixed. Use one column unless a human is the only reader.

If you add a template to the package, add it to `cvloom/templates_meta.py` — a test fails
for any packaged `cv/` template without an entry. A template of your own under
`templates/` shows as `unrated` in `cvloom list-templates`, which means "never measured",
not "safe".

---

## Third-Party Template Packages

Third-party template packages use the naming convention `cvloom-template-*`. They install templates into a location that cvloom can discover, following the same lookup order as project-local `templates/`.

When publishing a template package, name it `cvloom-template-<name>` and document which template path it provides (e.g. `cv/my-custom-name`).
