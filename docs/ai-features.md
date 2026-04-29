# AI-Powered Features

[Back to README](../README.md)

cvloom includes optional AI-powered analysis that works with any OpenAI-compatible backend — local models via Ollama, cloud routing via LiteLLM, or OpenAI directly. All existing commands continue to work unchanged when AI is not configured.

## Installation

The AI features require the optional `ai` dependency group:

```bash
uv sync --extra ai
```

## Configuration

Set three environment variables (only `CVLOOM_AI_BASE_URL` is required):

```bash
CVLOOM_AI_BASE_URL=http://localhost:11434/v1   # your provider's base URL
CVLOOM_AI_API_KEY=ollama                        # API key ("ollama" for local Ollama)
CVLOOM_AI_MODEL=gemma3:27b                      # model identifier
```

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

Shows current provider status and setup instructions.

```bash
cvloom ai config
```

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

## MCP tool

If you use the [MCP server](./mcp-server.md), `ai_review_cv` exposes the same scoring logic as a typed tool for LLM assistants:

```python
ai_review_cv(profile="general", project_root="/path/to/project")
```

Returns a JSON object with `overall_score`, `sections` (per-section scores and feedback), and `top_priorities`.
