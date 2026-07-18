# Publish your CV to GitHub Pages

[Back to README](../../README.md)

`cvloom init` scaffolds a ready-to-use workflow at `.github/workflows/publish-cv.yml` that
builds your CV in **public mode** (email and phone stripped) and deploys the HTML to GitHub
Pages. It's the same mechanism cvloom uses to publish its own [`examples/`](../../examples/)
demo — pointed at your data instead.

## Prerequisites

- A GitHub repository containing your cvloom project (created by `cvloom init`)
- GitHub Actions enabled

## Setup steps

1. **Settings → Pages → Build and deployment → Source:** select **GitHub Actions**.
2. **Settings → Secrets and variables → Actions → Variables:** add a repository variable
   `DEPLOY_PAGES` with value `true`.
   Until this variable is set, the workflow **builds but does not deploy** — a safety gate so
   nothing is published by accident.
3. Push to `main` (or run the workflow manually from the Actions tab).
4. Your CV appears at `https://<username>.github.io/<repo>/`.

By default the workflow publishes the `general` profile — change the `PROFILE:` value at the top
of `.github/workflows/publish-cv.yml` to publish a different one.

## What gets published

The workflow builds with `--public`, so **email and phone are always stripped** before anything
reaches Pages. With no contact configured, the name shows as a placeholder.

## Showing your real name and links (optional)

To put your real name, location, and LinkedIn/GitHub links on the published page (still without
email/phone):

1. **Settings → Secrets and variables → Actions → Secrets:** add a secret `CONTACT_YAML` whose
   value is the full contents of your `private/contact.yaml`.
2. The scaffolded workflow writes it to `private/contact.yaml` at build time, then builds with
   `--public` — so email and phone are stripped even if present in the secret.

`private/contact.yaml` stays gitignored; the secret is the only way your contact reaches CI.

## Keeping the workflow up to date

The workflow file is a scaffolded copy. When a new cvloom release ships an improved workflow,
refresh it with [`cvloom sync`](keeping-updated.md).

## The tool's own demo

cvloom's repository publishes its `examples/` demo with the same pattern via
`.github/workflows/build.yml` (which also runs the test suite). That job builds every example
profile from `examples/` and deploys when `DEPLOY_PAGES=true`.
