# MCP Server

[Back to README](../README.md)

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that lets AI assistants interact with external tools and data sources through a structured interface. cvloom ships an MCP server that exposes 13 typed tools, so an LLM can query your CV data, build tailored outputs, create profiles, validate schemas, and run AI-powered analysis — all without leaving the conversation.

## Installation

The MCP server requires the optional `mcp` dependency group:

```bash
# Install with the mcp extra
uv sync --extra mcp

# Or install as a standalone tool
uv tool install cvloom[mcp]
```

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

If you installed via `uv tool install` or want to run without activating a virtualenv, use `uvx`:

```json
{
  "mcpServers": {
    "cvloom": {
      "command": "uvx",
      "args": ["--extra", "mcp", "cvloom-mcp"]
    }
  }
}
```

### Claude Code

In your project directory, run:

```bash
claude mcp add cvloom -- cvloom-mcp
```

## Tool reference

All tools accept an optional `project_root` parameter (string). When omitted, the server uses the current working directory. All tools return JSON strings.

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `list_profiles` | `project_root?` | Array of profile objects (`name`, `template`, `output_filename`, `include_tags`, `job_context`) | Lists all profiles found in `profiles/*.yaml`. |
| `list_projects` | `project_root?`, `tags?` (string array) | Array of project objects (`name`, `description`, `tags`) | Lists projects from `data/projects/*.yaml`. When `tags` is provided, only projects matching at least one tag are returned (intersection). |
| `get_section` | `section` (string), `project_root?` | Section data (object or array) | Reads raw YAML for a section. Valid values: `basics`, `work`, `education`, `skills`, `projects`, `contact`. Contact reads from `private/contact.yaml`; projects reads all files in `data/projects/`. |
| `build_cv` | `profile?` (default `"general"`), `public?` (bool), `skip_pdf?` (bool), `project_root?` | `{html_path, pdf_path, words, pages, section_word_counts}` | Builds the CV for the given profile. Set `public` to use placeholder contact info. Set `skip_pdf` to generate HTML only. Returns an error object if the build fails. |
| `create_profile` | `name` (string), `config` (object), `project_root?` | `{created: path}` or `{error, details}` | Validates `config` against the profile schema and writes it to `profiles/{name}.yaml`. |
| `upsert_project` | `project` (object), `project_root?` | `{written: path}` or `{error, details}` | Validates `project` against the project schema and writes it to `data/projects/{slug}.yaml`, where slug is derived from the project name. Creates or overwrites. |
| `validate_data` | `project_root?` | `{valid: true}` or `{valid: false, errors: [...]}` | Runs schema validation against all data files in the project. |
| `export_json_resume` | `profile?` (default `"general"`), `project_root?` | Full JSON Resume object | Resolves the given profile and exports it in [JSON Resume](https://jsonresume.org) format. |
| `check_cv` | `profile?` (default `"general"`), `rule_ids?` (string array), `project_root?` | Array of finding objects (`rule_id`, `severity`, `section`, `entry`, `message`, `fix_hint`) | Runs the ATS linter on the resolved profile. Optionally filter by rule IDs. |
| `trim_report` | `profile?` (default `"general"`), `target_pages?` (int, default 1), `project_root?` | `{total_words, estimated_pages, words_to_cut, sections: [...], recommendations: [...]}` | Per-section word count breakdown with actionable trim recommendations. |
| `diff_profiles` | `profile_a` (string), `profile_b` (string), `project_root?` | `{template_a, template_b, sections_only_in_a, sections_only_in_b, entries_only_in_a, entries_only_in_b, word_count_a, word_count_b, highlight_count_a, highlight_count_b}` | Compares two profiles: sections, entries, word counts, and highlight counts. |
| `match_jd` | `jd_text` (string), `profile?` (default `"general"`), `project_root?` | `{coverage, jd_word_count, matched: [...], gaps: [...], top_jd_keywords: [...]}` | Keyword gap analysis comparing CV content against a job description. |
| `ai_review_cv` | `profile?` (default `"general"`), `project_root?` | `{overall_score, sections: [...], top_priorities: [...]}` | AI section scoring 1–10 with strengths, weaknesses, and improvement suggestions. Requires `CVLOOM_AI_BASE_URL`. |
| `ai_generate_cover` | `profile?` (default `"general"`), `jd_text` (string), `project_root?` | `{letter, word_count, key_alignments: [...]}` | AI-generated tailored cover letter from CV and job description text. Requires `CVLOOM_AI_BASE_URL`. |
| `ai_suggest_improvements` | `profile?` (default `"general"`), `role?` (string), `project_root?` | `{suggestions: [...], missing_skills: [...], summary}` | AI content improvement suggestions for a target role. Requires `CVLOOM_AI_BASE_URL`. |
| `ai_align_to_jd` | `profile?` (default `"general"`), `jd_text` (string), `project_root?` | `{alignment_score, narrative, repositioning: [...], tone_gaps: [...], strengths: [...]}` | Qualitative AI analysis of CV-to-JD alignment — tone, framing, and repositioning actions. Requires `CVLOOM_AI_BASE_URL`. |

> **AI tools** require `uv sync --extra ai` and `CVLOOM_AI_BASE_URL` set. If the provider is not configured they return `{"error": "..."}` instead of raising.

## Example workflow

Suppose you are tailoring your CV for a new job application. Here is a realistic sequence of tool calls an LLM might make:

1. **Explore what you have.** Call `list_profiles` to see existing profiles and `list_projects` to browse your project catalog.

2. **Create a targeted profile.** Call `create_profile` with a name like `acme-sre` and a config that selects the right template, includes only relevant tags (`["kubernetes", "observability"]`), and sets a `job_context` describing the role.

3. **Check the data.** Call `validate_data` to make sure all YAML files pass schema validation before building.

4. **Build and review.** Call `build_cv` with `profile="acme-sre"` and `skip_pdf=true` for a quick HTML preview. The response includes word counts per section so the LLM can suggest trims if the CV is too long.

5. **Add a missing project.** Call `upsert_project` to add a new project entry, then rebuild.

6. **Export.** Call `export_json_resume` to produce a JSON Resume file for uploading to job boards.

Throughout this workflow, the LLM reads your data, validates changes, and builds outputs -- all through the MCP server, without requiring you to run any CLI commands manually.

## Data privacy

The MCP server runs entirely on your local machine. Your CV data, private contact information, and build outputs never leave your computer. The server communicates only with the connected MCP client over local stdio -- there are no network calls, no telemetry, and no cloud dependencies.
