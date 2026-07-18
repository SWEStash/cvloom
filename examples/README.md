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
cvloom build --profile general --public          # HTML + PDF, placeholder contact
cvloom build --profile modern --public --skip-pdf
cvloom check --profile general                    # writing lint
```

Outputs land in `examples/dist/` (gitignored).

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
