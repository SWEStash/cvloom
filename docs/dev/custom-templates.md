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
6. [CSS Variables](#css-variables)
7. [Handling Optional Fields](#handling-optional-fields)
8. [Annotated Example](#annotated-example)
9. [Third-Party Template Packages](#third-party-template-packages)

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
| `contact` | dict | Contact data from `private/contact.yaml` (`name`, `email`, `phone`, `location`, `website`, `linkedin`, `github`) |
| `basics` | dict | From `data/basics.yaml` (`headline`, `summary`, `public_links`) |
| `work` | list | Work entries after filtering and overlay application |
| `education` | list | Education entries |
| `skills` | list | Skill categories with items |
| `projects` | list | Project entries |
| `profile` | dict | The raw profile YAML (`template`, `output_filename`, `include_tags`, etc.) |
| `show` | dict | Section visibility flags. Keys: `work`, `education`, `skills`, `projects`. Value: `True`/`False` |
| `section_order` | list | Ordered list of section names to render |
| `job_context` | dict or None | From `job_context:` in the profile (`company`, `role`, `hiring_manager`, `notes`) |
| `public` | bool | `True` when built with `--public` |
| `today` | str | Current date formatted as `"Month DD, YYYY"` |

**Work entry fields:** `company`, `title`, `location`, `start_date`, `end_date`, `highlights` (list of strings), `tags`

**Education entry fields:** `institution`, `degree`, `field`, `location`, `start_date`, `end_date`, `highlights`

**Skills category fields:** `category` (string), `items` (list of strings or `{name, level}` dicts)

**Project entry fields:** `name`, `description`, `url`, `start_date`, `end_date`, `highlights`, `tags`

---

## Custom Jinja2 Filters

Three custom filters are available in all templates:

### `md`

Renders a Markdown string to HTML. Unwraps single `<p>` tags for inline use.

```jinja2
{{ "**Strong** and _emphasis_" | md }}
{# → <strong>Strong</strong> and <em>emphasis</em> #}

{{ entry.description | md }}
```

### `date_range`

Formats a date range from two date strings, using "Present" as the fallback for missing end dates.

```jinja2
{{ entry.start_date | date_range(entry.end_date) }}
{# → "2021-03 – Present" or "2018-06 – 2021-02" #}
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
--accent: #7c3aed;
--font-body: "Inter", Arial, sans-serif;
{% endblock %}
```

Pre-built utility CSS classes from `base.html.j2`: `.muted`, `.right`, `.clearfix`, `.skill-tag`, `.skill-level`, `.skill-level-{1-4}`.

---

## Handling Optional Fields

The Jinja2 environment uses `StrictUndefined` — accessing an undefined variable raises an error. Always guard optional fields with `is defined`:

```jinja2
{% if entry.location is defined %}
<span class="location">{{ entry.location }}</span>
{% endif %}

{% if contact.linkedin is defined %}
<a href="https://linkedin.com/in/{{ contact.linkedin }}">LinkedIn</a>
{% endif %}

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

## Third-Party Template Packages

Third-party template packages use the naming convention `cvloom-template-*`. They install templates into a location that cvloom can discover, following the same lookup order as project-local `templates/`.

When publishing a template package, name it `cvloom-template-<name>` and document which template path it provides (e.g. `cv/my-custom-name`).
