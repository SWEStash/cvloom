# cvloom examples

This directory is **demo content** — a fictional CV used to showcase cvloom and to power the
project's own GitHub Pages preview. It is *not* anyone's real résumé; names like "Acme Corp"
and "State University" are placeholders.

The repository root is the **tool**. This folder is the only place a buildable dataset lives in
the repo — so contributors and the CI demo build from here, while real users scaffold their own
project elsewhere with `cvloom init`.

## Build the demo

```bash
cd examples
cvloom build --profile general --public              # full CV: HTML + PDF, placeholder contact
cvloom build --profile example-job --public          # same data, tailored for a role via overlays
cvloom diff general example-job                       # see how the two variants differ
cvloom check --profile example-job                   # writing lint
cvloom match --jd stripe-infra-jd.txt -p example-job # keyword gap vs a sample job description
```

Outputs land in `examples/dist/` (gitignored). `stripe-infra-jd.txt` is a sample job description
for the `match` command.

## Layout

| Path | What it is |
|---|---|
| `data/` | Sample CV sections (basics, work, education, skills, projects) |
| `profiles/` | Example build profiles (`general`, `modern`, `example-job`) showing overlays and tag filtering |

## Making your own CV

Don't edit these files for your own résumé. Instead, in a fresh directory:

```bash
cvloom init          # scaffolds data/, private/, profiles/, and a publish workflow
```

See the [getting-started guide](../docs/user/getting-started.md) and the
[profiles & overlays reference](../docs/reference/profiles-and-overlays.md).
