# Keeping your cvloom instance updated

[Back to README](../../README.md)

cvloom is designed to be used as an **installed tool** against a repo that holds only *your
data*. That keeps updates simple: the tool and your CV are separate, so upgrading the tool never
touches your content.

## 1. Update the tool

```bash
uv tool upgrade cvloom
```

That's the whole update for cvloom itself. Check the [CHANGELOG](../../CHANGELOG.md) for any
breaking changes before a major upgrade.

## 2. Refresh scaffolded files with `cvloom sync`

`cvloom init` scaffolds a few files *into your project* — the pre-commit PII-scanner hook and the
GitHub Pages publish workflow. These are copies, so a tool upgrade doesn't change them. After
upgrading, refresh them:

```bash
cvloom sync           # report which scaffolded files are out of date (writes nothing)
cvloom sync --force   # overwrite the out-of-date / missing ones with the new versions
```

`cvloom sync` byte-compares each managed file against the version shipped in the installed
package and reports `up to date` / `out of date` / `missing`. Nothing is overwritten unless you
pass `--force`, so your own edits are never lost by accident — review the diff (e.g. `git diff`)
after a forced sync.

Managed files:

| File | Purpose |
|---|---|
| `.git/hooks/pre-commit` | PII scanner that blocks committing `private/` data |
| `.github/workflows/publish-cv.yml` | GitHub Pages publish workflow |

## Why not fork + upstream?

A common instinct is to fork the cvloom repo and pull updates with a git `upstream` remote.
**Don't do this for your CV.** Forking mixes the tool's source code with your data in one repo,
which means every upgrade becomes a merge of tool internals you don't care about — and merge
conflicts. Keeping cvloom installed as a tool (and your data in its own repo) avoids all of that.

The fork + `upstream` pattern is only relevant if you're **contributing to cvloom itself** — see
[CONTRIBUTING.md](../../CONTRIBUTING.md).
