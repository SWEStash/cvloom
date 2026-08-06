# MCP Server

[Back to README](../../README.md)

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that lets AI assistants interact with external tools and data sources through a structured interface. cvloom ships an MCP server that exposes 16 typed tools, so an LLM can query your CV data, build tailored outputs, create profiles, validate schemas, and run AI-powered analysis — all without leaving the conversation.

## Installation

The MCP server requires the optional `mcp` dependency group. Which command adds
it depends on how you installed cvloom:

```bash
# Installed globally with `uv tool install cvloom` (the default in the README):
uv tool install 'cvloom[mcp]'

# Installed with pipx:
pipx install --force 'cvloom[mcp]'

# Installed with pip, in a venv:
pip install --upgrade 'cvloom[mcp]'

# Working from a git clone (dev checkout, has its own pyproject.toml):
uv sync --extra mcp
```

`uv sync --extra mcp` only works inside a cloned cvloom repo — it reads the
project's own `pyproject.toml`, which isn't present when cvloom was installed
as a packaged tool. Running it elsewhere fails with `No pyproject.toml found`.

> Reinstalling replaces the extras list rather than adding to it — want both
> MCP and AI features? Install them together: `uv tool install 'cvloom[mcp,ai]'`.
> See the [uv tool docs](https://docs.astral.sh/uv/guides/tools/) for details.

## Starting the server

Run the entry point directly:

```bash
cvloom-mcp
```

The server communicates over stdio using the MCP protocol. You do not interact with it directly -- an MCP-aware client (Claude Desktop, Claude Code, etc.) connects to it automatically.

## Client configuration

### Claude Desktop

Add the following to your Claude Desktop configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cvloom": {
      "command": "cvloom-mcp",
      "args": []
    }
  }
}
```

To run without installing anything first, use `uvx`. The extra goes in `--from`, not a
separate flag:

```json
{
  "mcpServers": {
    "cvloom": {
      "command": "uvx",
      "args": [
        "--directory", "/absolute/path/to/your-cv-project",
        "--from", "cvloom[mcp]",
        "cvloom-mcp"
      ]
    }
  }
}
```

`--directory` matters here — see [Which project the server operates on](#which-project-the-server-operates-on) below.

### Claude Code

In your project directory, run:

```bash
claude mcp add cvloom -- cvloom-mcp
```

Claude Code starts the server in the directory you ran this from, so it picks up that
project automatically. Add `--scope user` if you want the server available in every
session rather than just this project — but then pin the project explicitly, as below.

### Which project the server operates on

Every tool takes an optional `project_root`. When omitted the server falls back to its own
**current working directory**, which is whatever directory the MCP client launched it in —
not the directory you happen to be chatting about.

That default is right for Claude Code started inside a cvloom project, and wrong for Claude
Desktop, which has no project notion. Pick one:

- **Pin the working directory** at launch — `uvx --directory /path/to/your-cv-project …`, as
  in the config above. Best when you have one CV project.
- **Pass `project_root` on every call** and tell the assistant the absolute path once at the
  start of the conversation. Best when you juggle several.

Without either, the tools will read a `data/` directory that isn't yours — usually surfacing
as an empty `list_profiles` or a `data/work.yaml not found` error.

## Tool reference

All tools accept an optional `project_root` parameter (string). When omitted, the server uses the current working directory. All tools return JSON strings.

### Core tools (always available)

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `list_profiles` | `project_root?` | Array of profile objects (`name`, `template`, `output_filename`, `select`, `job_context`) | Lists all profiles found in `profiles/*.yaml`. |
| `list_projects` | `project_root?`, `tags?` (string array) | Array of project objects (`name`, `description`, `tags`) | Lists projects from `data/projects/*.yaml`. When `tags` is provided, only projects matching at least one tag are returned. |
| `get_section` | `section` (string), `project_root?` | Section data (object or array) | Reads raw YAML for a section. Valid values: `basics`, `skills`, `contact`, and every entry-list section — `work`, `education`, `projects`, `publications`, `certifications`, `awards`, `languages`. |
| `build_cv` | `profile?` (default `"general"`), `public?` (bool), `skip_pdf?` (bool), `project_root?` | `{html_path, pdf_path, words, pages, section_word_counts}` | Builds the CV for the given profile. Set `public` to use placeholder contact info. |
| `create_profile` | `name` (string), `config` (object), `project_root?` | `{created: path}` or `{error, details}` | Validates `config` against the profile schema and writes it to `profiles/{name}.yaml`. |
| `upsert_project` | `project` (object), `project_root?` | `{written: path}` or `{error, details}` | Validates `project` against the project schema and writes it to `data/projects/{slug}.yaml`. Creates or overwrites. |
| `validate_data` | `project_root?` | `{valid: true}` or `{valid: false, errors: [...]}` | Runs schema validation against `cvloom.yaml` and all data files in the project. Config is checked first: a project whose config is invalid cannot build, so reporting the data as valid would be misleading. |
| `export_json_resume` | `profile?` (default `"general"`), `public?` (bool, default **true**), `project_root?` | Full JSON Resume object | Resolves the given profile and exports it in [JSON Resume](https://jsonresume.org) format. **PII fence:** `public` defaults to `true` (email/phone stripped); pass `public=false` to include real contact PII. |
| `check_cv` | `profile?` (default `"general"`), `rule_ids?` (string array), `project_root?` | Array of finding objects (`rule_id`, `category`, `severity`, `section`, `entry`, `message`, `fix_hint`) | Runs the writing lint on the resolved profile; each finding carries a `category` (`writing`/`structure`/`ats-parse`). Optionally filter by rule IDs. |
| `trim_report` | `profile?` (default `"general"`), `target_pages?` (int, default 3), `project_root?` | `{total_words, estimated_pages, words_to_cut, sections: [...], recommendations: [...]}` | Per-section word count breakdown with actionable trim recommendations. |
| `diff_profiles` | `profile_a` (string), `profile_b` (string), `project_root?` | `{template_a, template_b, sections_only_in_a, sections_only_in_b, entries_only_in_a, entries_only_in_b, word_count_a, word_count_b, highlight_count_a, highlight_count_b}` | Compares two profiles: sections, entries, word counts, and highlight counts. |
| `match_jd` | `jd_text` (string), `profile?` (default `"general"`), `project_root?` | `{coverage, jd_word_count, matched: [...], gaps: [...], top_jd_keywords: [...]}` | Keyword gap analysis comparing CV content against a job description. |

### AI tools (require `--extra ai` and `CVLOOM_AI_BASE_URL`)

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `ai_review_cv` | `profile?` (default `"general"`), `project_root?` | `{overall_score, sections: [...], top_priorities: [...]}` | AI section scoring 1–10 with strengths, weaknesses, and improvement suggestions. |
| `ai_generate_cover` | `profile?` (default `"general"`), `jd_text` (string), `project_root?` | `{letter, word_count, key_alignments: [...]}` | AI-generated tailored cover letter from CV and job description text. |
| `ai_suggest_improvements` | `profile?` (default `"general"`), `role?` (string), `project_root?` | `{suggestions: [...], missing_skills: [...], summary}` | AI content improvement suggestions for a target role. |
| `ai_align_to_jd` | `profile?` (default `"general"`), `jd_text` (string), `project_root?` | `{alignment_score, narrative, repositioning: [...], tone_gaps: [...], strengths: [...]}` | Qualitative AI analysis of CV-to-JD alignment — tone, framing, and repositioning actions. |

> AI tools return `{"error": "..."}` instead of raising when `CVLOOM_AI_BASE_URL` is not set.

## Example workflow

Suppose you are tailoring your CV for a new job application. Here is a realistic sequence of tool calls an LLM might make:

1. **Explore what you have.** Call `list_profiles` to see existing profiles and `list_projects` to browse your project catalog.

2. **Create a targeted profile.** Call `create_profile` with a name like `acme-sre` and a config that selects the right template, includes only relevant tags (`["kubernetes", "observability"]`), and sets a `job_context` describing the role.

3. **Check the data.** Call `validate_data` to make sure all YAML files pass schema validation before building.

4. **Build and review.** Call `build_cv` with `profile="acme-sre"` and `skip_pdf=true` for a quick HTML preview. The response includes word counts per section so the LLM can suggest trims if the CV is too long.

5. **Add a missing project.** Call `upsert_project` to add a new project entry, then rebuild.

6. **Run AI analysis.** Call `ai_align_to_jd` with the job description text to get qualitative alignment insights beyond keyword coverage.

7. **Export.** Call `export_json_resume` to produce a JSON Resume file for uploading to job boards.

Throughout this workflow, the LLM reads your data, validates changes, and builds outputs -- all through the MCP server, without requiring you to run any CLI commands manually.

## Data privacy

The MCP server runs entirely on your local machine. Your CV data, private contact information, and build outputs never leave your computer. The server communicates only with the connected MCP client over local stdio -- there are no network calls, no telemetry, and no cloud dependencies.

### Agent-safety guarantees

The server is designed to be a *safe data layer for LLM agents*, with two explicit guarantees:

- **Schema-validated writes.** The mutating tools (`create_profile`, `upsert_project`) validate their input against the JSON Schema **before** writing anything. On failure they return a structured `{"error": "Validation failed", "details": [...]}` and write nothing — a malformed write never lands a partial file.
- **PII fence.** Read/analysis tools (`check_cv`, `trim_report`, `diff_profiles`, `match_jd`, `export_json_resume`, and the `ai_*` tools) resolve in **public mode**, so the agent never sees your email or phone. The only ways to surface real contact PII are `get_section("contact")` — a deliberate, named read — and `export_json_resume(public=false)` — an explicit opt-out. Both require the caller to ask for it on purpose.
