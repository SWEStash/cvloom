# AI-Powered Features

[Back to README](../../README.md)

cvloom includes optional AI-powered analysis that works with any OpenAI-compatible backend — local models via Ollama, cloud routing via LiteLLM, or OpenAI directly. All existing commands continue to work unchanged when AI is not configured.

## Installation

The AI features require the optional `ai` dependency group. Which command adds it
depends on how you installed cvloom:

```bash
# Installed globally with `uv tool install cvloom` (the default in the README):
uv tool install 'cvloom[ai]'

# Installed with pipx:
pipx install --force 'cvloom[ai]'

# Installed with pip, in a venv:
pip install --upgrade 'cvloom[ai]'

# Working from a git clone (dev checkout, has its own pyproject.toml):
uv sync --extra ai
```

`uv sync --extra ai` only works inside a cloned cvloom repo — it reads the
project's own `pyproject.toml`, which isn't present when cvloom was installed
as a packaged tool. Running it elsewhere fails with `No pyproject.toml found`.
If you're not sure which you have, `cvloom --version` running standalone (no
git repo needed) means you installed the package; if you cloned the repo to
hack on cvloom itself, you're in the dev checkout case.

> Reinstalling replaces the extras list rather than adding to it — installing a
> second extra later means listing both, e.g. `uv tool install 'cvloom[ai,mcp]'`.
> See the [uv tool docs](https://docs.astral.sh/uv/guides/tools/) for details.

## Configuration

Two places, and the environment always wins.

Set three environment variables (only `CVLOOM_AI_BASE_URL` is required):

```bash
CVLOOM_AI_BASE_URL=http://localhost:11434/v1   # your provider's base URL
CVLOOM_AI_API_KEY=ollama                        # API key ("ollama" for local Ollama)
CVLOOM_AI_MODEL=gemma3:27b                      # model identifier
```

Or record the endpoint and model in the project's own `cvloom.yaml`, so the
repository says which backend it is analysed with instead of that living only in
one shell:

```yaml
# cvloom.yaml
locale: en

ai:
  base_url: http://localhost:11434/v1
  model: gemma3:27b
```

> **The API key never goes in `cvloom.yaml`.** That file sits at the project root
> and is committed — unlike `private/`, it is tracked. cvloom refuses to load a
> config carrying an `api_key` at all, and the scaffolded pre-commit hook blocks
> one on the way into a commit. Use `CVLOOM_AI_API_KEY`.

`CVLOOM_AI_BASE_URL` and `CVLOOM_AI_MODEL` override the file. That direction is
deliberate: a committed `base_url` of `localhost:11434` is right for whoever
wrote it and wrong on every other machine, so the machine has the last word.

Verify your configuration at any time:

```bash
cvloom ai config
```

## Backends

### Ollama (local, free)

Ollama runs open-weight models on your own hardware — no API key or internet connection required for inference.

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull gemma3:27b`
3. Configure cvloom:

```bash
export CVLOOM_AI_BASE_URL=http://localhost:11434/v1
export CVLOOM_AI_API_KEY=ollama
export CVLOOM_AI_MODEL=gemma3:27b
```

Recommended models: `gemma3:27b`, `llama3.3:70b`, `qwen2.5:32b`

#### Context length — read this before running `ai` on a long CV

Ollama does not reject a prompt that is too long for the context window it is
running with. It silently discards the **front** of the prompt and answers with
what is left. Measured on Ollama 0.32.6 through the same OpenAI-compatible
endpoint cvloom uses: prompts up to roughly 2,500 tokens went through intact,
while every larger prompt was clamped to about 2,050 tokens ingested no matter
how much larger it was. `ollama serve --help` gives the default context length as
"4k/32k/256k based on VRAM", so a machine with modest VRAM is on 4k.

cvloom sends one prompt per command carrying your entire CV, plus the whole job
description for `ai cover` and `ai align`. A one-page CV sits comfortably inside
4k. A three-page CV with a long job description does not.

**You will see an error rather than a wrong answer.** cvloom puts the JSON schema
at the top of every prompt and the CV below it, so a discarded front takes the
schema with it, the model stops answering in JSON, and the command fails:

```
AI error: AI returned invalid JSON. Raw response:
Based on the information provided, this candidate ...
```

Treat that as the truncation signal. The ordering is deliberate: with the CV at
the top instead, truncation discards the CV and the model returns a fluent,
well-formed review of a CV it never read — and nothing on screen distinguishes
that from a real one.

**Fix it on the Ollama side.** cvloom talks to the OpenAI-compatible `/v1`
endpoint, which has no field for Ollama's per-request `num_ctx`, so the context
length has to be set where the server can see it:

```bash
OLLAMA_CONTEXT_LENGTH=16384 ollama serve
```

Or bake it into a model variant, which survives a restart:

```bash
printf 'FROM gemma3:27b\nPARAMETER num_ctx 16384\n' > Modelfile
ollama create gemma3-cv -f Modelfile
export CVLOOM_AI_MODEL=gemma3-cv
```

A longer context costs memory, so raise it to what your CV needs rather than to
the model's maximum. Note that asking the model how much context it has does not
work — it reports what its architecture supports, not what the server actually
gave it, and answers the same number whichever value you set.

### LiteLLM proxy (cloud routing)

LiteLLM lets you route to OpenAI, Anthropic, Google, and other providers through a single OpenAI-compatible endpoint without modifying your config.

See the quickstart: https://docs.litellm.ai/docs/proxy/quick_start

```bash
export CVLOOM_AI_BASE_URL=http://localhost:4000/v1
export CVLOOM_AI_API_KEY=<your-litellm-key>
export CVLOOM_AI_MODEL=claude-sonnet-4-6   # or any model your proxy supports
```

### OpenAI

```bash
export CVLOOM_AI_BASE_URL=https://api.openai.com/v1
export CVLOOM_AI_API_KEY=sk-...
export CVLOOM_AI_MODEL=gpt-4o
```

## Commands

### `ai config`

Shows current provider status and setup instructions — and, for each value,
**where it came from**:

```bash
cvloom ai config
```

```
AI provider: configured
  Base URL:  http://localhost:11434/v1 (cvloom.yaml)
  Model:     gpt-4o-mini (CVLOOM_AI_MODEL — overrides cvloom.yaml)
  API key:   ***set*** (CVLOOM_AI_API_KEY)
```

The source column is the point of the command with two config layers: an exported
variable you forgot about, quietly beating the model your project pins, otherwise
looks identical to it working.

### `ai review`

Scores each visible CV section 1–10 with strengths, weaknesses, and concrete improvement suggestions. Produces an overall score and a prioritised list of the three highest-impact changes across the whole CV.

```bash
cvloom ai review --profile general
```

Example output:

```
CV Review  profile: general
Overall score: 7.2/10

work  8.0/10
  + Strong quantified metrics throughout
  – Some bullets are overly long
  → Trim highlights to under 20 words each

skills  6.5/10
  + Good breadth across languages and tools
  – Missing cloud platform skills
  → Add AWS or GCP experience

Top priorities:
  1. Quantify impact on remaining non-metric bullets
  2. Add cloud platform skills (AWS/GCP)
  3. Tighten the professional summary to under 60 words
```

### `ai cover`

Generates a tailored cover letter from your CV and a job description file. Optionally writes to a file.

```bash
cvloom ai cover --profile backend-role --jd stripe-infra.txt
cvloom ai cover --profile backend-role --jd stripe-infra.txt --output cover.md
```

If `job_context` is set in the profile (`company`, `role`, `hiring_manager`), the prompt is personalised automatically.

### `ai suggest`

Suggests specific content improvements for a target role: new bullet points, skill additions, rewordings, and items to remove. Suggestions are non-destructive — they are ideas to apply manually.

```bash
cvloom ai suggest --profile backend-role --role "Senior Platform Engineer"
cvloom ai suggest --profile backend-role   # uses job_context.role from profile if set
```

Example output:

```
Improvement Suggestions  profile: backend-role  target role: Senior Platform Engineer

Focus on infrastructure ownership and quantified reliability metrics.

  [bullet] work / Acme Corp
    Reduced P99 API latency from 800ms to 120ms by migrating to async workers,
    improving throughput for 50k daily active users
    Adds measurable impact with scale context

  [skill] skills
    Kubernetes
    Widely required for senior platform roles; currently absent

Missing skills worth adding:
  • Kubernetes
  • Terraform
  • Prometheus
```

### `ai align`

Qualitative AI analysis of how well your CV is *positioned* for a specific job description — tone, framing, narrative gaps — beyond keyword coverage. Internally runs `cvloom match` first and passes the keyword analysis as context so the AI focuses on qualitative insights.

```bash
cvloom ai align --profile backend-role --jd stripe-infra.txt
```

Example output:

```
JD Alignment  profile: backend-role

Alignment Score: 6.8/10

The CV demonstrates solid backend experience but is framed around individual
feature delivery rather than the infrastructure ownership and reliability
engineering that Stripe emphasises throughout the JD...

Strengths:
  ✓ Python and distributed systems experience directly matches core requirements
  ✓ Quantified metrics throughout work history signal data-driven mindset

Tone & Framing Gaps:
  ⚠ JD uses "own" and "operate" repeatedly; CV uses "built" and "developed"
  ⚠ JD emphasises on-call and incident response; CV has no reliability framing

Repositioning Actions:
  1. Lead with distributed systems and reliability experience, not feature delivery
  2. Reframe highlights from delivery ("built X") to ownership ("owned and operated X")
  3. Surface on-call, SLO, and incident work that is currently absent
```

## MCP tools

If you use the [MCP server](../reference/mcp-server.md), all four AI commands are available as typed tools:

| Tool | What it does |
|---|---|
| `ai_review_cv(profile, project_root)` | Section scoring and feedback |
| `ai_generate_cover(profile, jd_text, project_root)` | Cover letter generation |
| `ai_suggest_improvements(profile, role, project_root)` | Content improvement suggestions |
| `ai_align_to_jd(profile, jd_text, project_root)` | Qualitative JD alignment analysis |

All tools return JSON and require `CVLOOM_AI_BASE_URL` to be set. If not configured, they return `{"error": "..."}` rather than raising.
