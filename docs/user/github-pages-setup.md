# GitHub Pages Setup

[Back to README](../../README.md)

Publish a public version of your CV (with placeholder contact) automatically on push.

## Prerequisites

- Your repo is public (or Pages is enabled on a private repo)
- GitHub Actions is enabled

## Setup steps

1. Go to **Settings → Variables → Actions** and add a repository variable `DEPLOY_PAGES` with value `true`.

2. Go to **Settings → Pages → Source** and select **GitHub Actions**.

3. The workflow at `.github/workflows/build.yml` runs `cvloom build --public` on every push to `main`.

4. The built `dist/` directory is deployed to the `gh-pages` branch.

5. Your CV will be available at `https://<username>.github.io/<repo>/`.

## What gets published

Only files built with `--public` mode — placeholder contact data, never your real PII.

## Private builds in CI (advanced)

If you need real contact data in CI (e.g. for a private Pages instance):

1. Add your `private/contact.yaml` content as a GitHub Actions secret `CONTACT_YAML`.
2. In the workflow, write it to `private/contact.yaml` before building:
   ```yaml
   - name: Write private contact
     run: |
       mkdir -p private
       echo "${{ secrets.CONTACT_YAML }}" > private/contact.yaml
   ```
3. Change the build step to `cvloom build --private`.

Keep the `--public` fallback for the public Pages deployment.
