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

#### Why the recommendation starts at ~27B

Small models are not merely worse here — they fail in a specific, measurable way,
and the repo's evaluation suite (`uv run pytest -m evals`) exists to show it.
Measured on `qwen2.5:3b-instruct`, 2026-08-11, 8 of 16 checks passed. The split
is not random:

**Passed** — everything about the *shape* of the answer. It followed the JSON
schema, banded every section inside the rubric, answered in the CV's language,
cited only rule ids that were really in its context, never leaked an internal
`section/entry` label into prose, and never rewrote a flagged opener into another
flagged one.

**Failed** — everything about *what to say and what to leave out*:

- Handed a **privacy policy** in place of a job description, it wrote an
  enthusiastic cover letter anyway, and `ai align` analysed the CV's fit against
  it rather than reporting that the document is not a job posting.
- `--body-only` output carried `Dear Hiring Manager` and `Sincerely` — the exact
  duplication that flag exists to prevent, since the template supplies its own.
- Given a CV with nothing in it, it produced improvement advice instead of saying
  so. On a genuinely empty one it *did* say "the CV is nearly empty", then
  returned an assessment as well.
- It invented figures in example bullets — suggesting "Reduced backend response
  time by 83%" for a CV that says 800ms → 120ms. The grounding rules explicitly
  require an `[add metric: …]` placeholder here instead, and inventing a number
  in an illustration is the same harm as inventing one anywhere: it is the string
  the user pastes.

So a small model can be trusted with the *form* of the output and not with its
*judgement*, and the anti-fabrication rules are exactly the instructions it drops
first. If a 3B model is what you have, treat `ai suggest` and `ai review` as
prompts for your own thinking, check every number against your CV, and do not use
`ai cover` output without reading it line by line.

**This is not a prompt-wording problem, and it was worth checking.** Two
plausible fixes were tested against `qwen2.5:3b-instruct` and both failed:
restating the constraint as the very last line the model reads, which is what
`CLOSING` exists for, changed nothing on any of the three failures; and removing
the competing "open the letter with exactly this salutation" instruction did not
produce a refusal either, it only added a heading. The model does what it was
broadly asked and does not act on a conditional that would cancel that.

Which points at a structural fix rather than a wording one, if these cases matter
to you: the same model follows *structural* instructions near-perfectly. A
separate cheap call asking "is this a job posting?" and branching on the answer
turns a judgement it fails into a classification it does not. That is a change to
how the feature works, not to what the prompt says, and it is not implemented.

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

**cvloom tells you when this happens.** Backends report how many prompt tokens
they actually ingested, and cvloom compares that against what it sent. A count far
below the prompt's real size means the backend cropped it:

```
note: The backend counted only 2048 prompt tokens for a prompt of roughly 5200.
It has very likely cropped the front of the prompt to fit its context window,
which is where the instructions and the grounding rules are. Raise the model's
context size (num_ctx on Ollama) or build a shorter profile.
```

The note appears above the normal output, which still prints. Treat everything
below it as a review of a CV the model only partly saw. Not every backend reports
a token count; when none comes back, cvloom stays silent rather than guessing.

The prompt ordering is a second line of defence. cvloom puts the JSON schema at the
top and the CV below it, so a discarded front takes the schema with it and the model
stops answering in JSON — a loud failure. With the CV at the top instead, truncation
would discard the CV and the model would return a fluent, well-formed review of a CV
it never read, and nothing on screen would distinguish that from a real one.

A reply that is not valid JSON is retried once, with the decode error shown to the
model; most recover. Only a second unparseable reply fails the command:

```
AI error: AI returned invalid JSON. Raw response:
Based on the information provided, this candidate ...
```

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

## Language

Every `ai` command answers in **your project's language**, taken from `locale:` in
`cvloom.yaml`. On an `es` project, `ai review` returns Spanish feedback, `ai suggest`
writes Spanish replacement bullets, and `ai cover` writes a Spanish letter that opens
and closes with the same words `cvloom build` would use — see
[Cover-letter furniture](../reference/locales.md#cover-letter-furniture-two-sources-narrowest-wins).

Two things stay English on purpose:

- **The terminal output around the answer.** Labels, headings and warnings are the
  CLI's, and the CLI is English everywhere — the same rule `cvloom check` follows.
- **JSON keys, section names and the suggestion `type`** (`bullet`, `skill`,
  `reword`, `remove`). These are parsed by cvloom, not read by you. The prompt says
  so explicitly, because a model told only "answer in Spanish" will happily return
  `"type": "viñeta"` and leave the CLI unable to categorize its own output.

A locale with no pack of its own falls back the way everything else does: the prompt
names the language by code, and the model does the rest.

## What the model is told, besides your CV

Every `ai` command sends an `<analysis>` block alongside the CV text: what
`cvloom check`, `cvloom trim` and the template's measured parse rating already
know. Its purpose is to stop the AI guessing at things cvloom answers exactly.

```
<analysis>
locale: en — 24 of 25 lint rules ran (wl-025 has no en implementation)
length: 252 words, about 1 page against a 3-page target
template: cv/ats-clean — 1 column, PDF text extraction rated "safe"
findings: 22 (writing 17, structure 1, ats-parse 4)

wl-005 [writing/warning] x4 — fix: Add context, impact, or metrics …
  - education / State University, bullet 1: Highlight too short (2 words, min 8).
  ... and 1 more of wl-005
not shown: wl-013 x3, wl-016 x6
</analysis>
```

One rule sends more than its findings. When a weak opener is flagged, the block
also names **every** opener wl-004 checks for:

```
openers wl-004 will flag again — avoid starting a bullet with any of them:
"helped", "assisted", "worked on", "was responsible for", "participated in",
"was involved in". Any other verb is yours to choose.
```

Without it the model knows only that *your* opener is weak, so it rewrites
"was responsible for" into "participated in" — also on the list — and the finding
fires again on the bullet it just fixed. It appears only when a wl-004 finding is
already in the block, so a CV that does not have this problem does not pay for
the sentence. The openers are in your project's language; the Spanish set is
longer, and it is the case that makes this worth sending, since those phrases are
cvloom's own editorial judgement rather than something a model can infer.

What is deliberately **not** sent is a list of verbs to use instead. Sharing the
rule leaves the wording yours; handing over five approved verbs is how every CV
written with an AI's help ends up opening the same way.

This changes what `ai review` is **for**. It no longer re-derives, worse, what the
linter computes exactly — it is told not to repeat those findings back, and asked
instead for what no rule can produce: whether an achievement is credible for the
seniority claimed, whether the career narrative holds, and which of the findings
actually matter for this application. Run `cvloom check` for the findings
themselves; run `ai review` to find out which ones to spend your time on.

`ai review` and `ai suggest` can cite the rule they address, shown as
`(addresses wl-004)`. A cited id always appears in your own `cvloom check` output
— if one does not, the model invented it, and cvloom shows it rather than hiding
it so you can see that happening.

**Each command gets only what it can act on.** `ai align` receives counts and the
aggregate writing signal, not individual bullets. `ai cover` receives no defect
findings at all — instead it is told which entries already carry a quantified
outcome, so it leads with them. Telling a cover-letter generator "this entry has
no metric" is how you get an invented metric.

### When the analysis has to be cut down

The block is budgeted as a fraction of your CV, so it can never crowd the CV out
of a small model's context window. If your CV has more findings than fit, cvloom
sheds the lowest-priority ones, lists them under `not shown:`, and prints a note:

```
note: 14 lower-priority lint findings were left out of the AI context to keep
      the CV itself in the prompt.
```

That note only appears when something was actually dropped. See
[Context length](#context-length--read-this-before-running-ai-on-a-long-cv) for
the related failure, where the *backend* truncates the prompt rather than cvloom.

Notes are also how cvloom reports what the *call* had to give up, not just the
prompt. Two more can appear, and neither is gated behind `--verbose` — each one is
a caveat on the output printed below it:

- **JSON mode was refused.** Some OpenAI-compatible backends reject
  `response_format`. cvloom retries without it, since the prompt demands JSON
  anyway, but nothing then enforces the shape of what comes back.
- **The reply had to be requested twice.** The first response was not valid JSON
  and the model was shown the decode error.

None of them fire on a healthy run against a well-behaved backend.

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

Assesses each visible CV section as `strong`, `adequate` or `needs work`, with
strengths, weaknesses and concrete improvement suggestions, plus a prioritised
list of the three highest-impact changes across the whole CV.

The bands carry written criteria, stated in the prompt: `strong` means nothing
there would cost an interview, `adequate` means accurate but under-selling with
concrete fixes available, and `needs work` means a skimming recruiter would learn
little or would hit a credibility or parsing problem. The overall band is the
**worst** section rather than an average, and cvloom computes it — the model is
never asked to aggregate its own answer.

There is deliberately no number here. `docs/reference/ats-readiness.md` sets out
why a single score is dishonest, and an AI score was the last place in cvloom
still printing one.

It is handed everything `cvloom check` found and told not to repeat it, so it
complements that command rather than restating it — see
[What the model is told](#what-the-model-is-told-besides-your-cv).

```bash
cvloom ai review --profile general
```

Example output:

```
CV Review  profile: general
Overall: adequate (weakest section)

work  strong
  + Strong quantified metrics throughout
  – Some bullets are overly long
  → Trim highlights to under 20 words each

skills  adequate
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

#### Feeding the cover-letter template: `--body-only`

By default `ai cover` writes a complete letter — its own salutation and sign-off
included. That is the right shape for pasting into an email, and the wrong shape for
a `cover-letter/*` template, which renders the body from `job_context.notes` and
supplies the greeting, closing and signature itself from the locale pack. Pasting a
full letter there gives you two of each.

`--body-only` asks the model for the body paragraphs alone and prints them as a
pasteable block:

```bash
cvloom ai cover --profile cover-letter --jd stripe-infra.txt --body-only
```

```yaml
job_context:
  notes: |
    I have spent the last six years building payment infrastructure, and the
    ingestion work you describe is the part of that I would choose again.

    At Acme I owned the pipeline end to end, which is the closest thing I have
    to the problem in your posting.
```

Paste the `notes:` key into your profile's existing `job_context:` block, then
`cvloom build --profile cover-letter`. The letter comes out with exactly one
greeting, one closing and one signature, in the project's locale — the model never
writes those, so it cannot write them in the wrong language.

cvloom prints the block rather than editing the profile for you. It has no
comment-preserving YAML writer, and rewriting a hand-maintained profile would drop
its comments, blank lines and key order. If the profile already has `notes`, the
command says so before you paste over it. With `--output FILE`, the block is written
to that file instead of printed.

> The two shipped cover-letter templates differ in one respect: `standard` renders the
> pack's closing word (`Sincerely,` / `Atentamente,`) above the signature, and `brief`
> ends on the name alone. Both render the greeting.

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

Alignment: adequate

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
| `ai_generate_cover(profile, jd_text, project_root, body_only)` | Cover letter generation |
| `ai_suggest_improvements(profile, role, project_root)` | Content improvement suggestions |
| `ai_align_to_jd(profile, jd_text, project_root)` | Qualitative JD alignment analysis |

All tools return JSON and require `CVLOOM_AI_BASE_URL` to be set. If not configured, they return `{"error": "..."}` rather than raising.
