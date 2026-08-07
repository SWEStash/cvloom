# Keeping your cvloom instance updated

[Back to README](../../README.md)

cvloom is designed to be used as an **installed tool** against a repo that holds only *your
data*. That keeps updates simple: the tool and your CV are separate, so upgrading the tool never
touches your content.

## The short version

```bash
uv tool upgrade cvloom && cvloom sync --force
```

Or, without installing anything:

```bash
uvx cvloom@latest sync --force
```

Run it from your CV project. The rest of this page explains what each half does and what
`sync` may write.

## 1. Update the tool

```bash
uv tool upgrade cvloom
```

That's the whole update for cvloom itself. Check the [CHANGELOG](../../CHANGELOG.md) for any
breaking changes before a major upgrade.

## 2. Bring the project up to date with `cvloom sync`

`cvloom init` scaffolds files *into your project* — the pre-commit PII-scanner hook and the
GitHub Pages publish workflow. These are copies, so a tool upgrade doesn't change them. A
release may also add a project file that did not exist when you scaffolded, such as
`cvloom.yaml`. `sync` handles both:

```bash
cvloom sync           # report what is out of date or missing (writes nothing)
cvloom sync --force   # write it
```

`cvloom sync` byte-compares each managed file against the version shipped in the installed
package and reports `up to date` / `out of date` / `missing`. Nothing is overwritten unless you
pass `--force`, so your own edits are never lost by accident — review the diff (e.g. `git diff`)
after a forced sync.

Managed files, byte-compared and overwritten only with `--force`:

| File | Purpose |
|---|---|
| `.git/hooks/pre-commit` | PII scanner that blocks committing `private/` data, and credentials |
| `.github/workflows/publish-cv.yml` | GitHub Pages publish workflow |

Project files, **created when absent and never overwritten** — not even by `--force`, because
their content is your choice:

| File | Purpose | Added in |
|---|---|---|
| `cvloom.yaml` | Project settings: `locale`, and optionally an `ai` block | 0.7.0 |

A project with no `cvloom.yaml` already behaved as `locale: en`, so `sync` creating one changes
nothing on its own. If your CV is not in English, set `locale:` afterwards — see
[Locales](../reference/locales.md) and `cvloom list-locales`.

> **Upgrading a project scaffolded before 0.7.0?** One thing `sync` cannot fix for you: if your
> `profiles/cover-letter.yaml` still carries `hiring_manager: "Hiring Manager"` from the old
> sample, that English literal overrides your locale's salutee. Delete the line to let the
> locale supply it (`Responsable de Contratación` in `es`), or set it to the real recipient.

## Uninstalling

Removing cvloom only removes the tool — your CV data lives in its own repo and is
never touched:

```bash
uv tool uninstall cvloom      # if installed with `uv tool install`
pipx uninstall cvloom         # if installed with pipx
pip uninstall cvloom          # if installed with pip, in a venv
```

Two things it does *not* remove, both scoped to your data repo, not the tool:

- Your `data/`, `profiles/`, and `private/` content — nothing under your project
  directory is touched by any of the commands above.
- The scaffolded pre-commit hook (`.git/hooks/pre-commit`) and GitHub Pages
  workflow (`.github/workflows/publish-cv.yml`) from `cvloom init` — these are
  plain files copied into your repo, not managed by the tool's install. Delete
  them yourself if you no longer want them.

## Why not fork + upstream?

A common instinct is to fork the cvloom repo and pull updates with a git `upstream` remote.
**Don't do this for your CV.** Forking mixes the tool's source code with your data in one repo,
which means every upgrade becomes a merge of tool internals you don't care about — and merge
conflicts. Keeping cvloom installed as a tool (and your data in its own repo) avoids all of that.

The fork + `upstream` pattern is only relevant if you're **contributing to cvloom itself** — see
[CONTRIBUTING.md](../../CONTRIBUTING.md).
