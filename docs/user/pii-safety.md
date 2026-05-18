# PII Safety Guide

[Back to README](../../README.md)

cvloom is designed so that your name, email, phone number, and address **never enter version control**.

## How it works

```
cvloom/
├── data/          ← committed: all CV content, PII-free
├── profiles/      ← committed: build configurations
├── private/       ← GITIGNORED: contact.yaml, cover letters
└── dist/          ← GITIGNORED: build output
```

`private/` is the first line of `.gitignore`. The pre-commit hook provides a second layer of protection.

## The two build modes

| Mode | Contact data | When to use |
|---|---|---|
| `cvloom build --private` | `private/contact.yaml` (real data) | Local builds for applications |
| `cvloom build --public` | Placeholder values | CI, GitHub Actions, GitHub Pages |

## Pre-commit hook

Installed by `cvloom init`. It scans every staged file for:
- Email addresses (regex)
- Phone numbers (regex)

If a match is found outside `private/`, the commit is blocked with a clear error message.

To bypass (e.g. for a placeholder in a template):
```bash
git commit --no-verify
```

## GitHub Pages safety

The provided GitHub Actions workflow always uses `--public` mode. Your real contact details are never in `dist/` when building for Pages.

## What to put in private/contact.yaml

```yaml
name: "Jane Smith"
email: "jane@example.com"
phone: "+44 7700 900000"
location: "London, UK"
website: "https://janesmith.dev"
linkedin: "janesmith"
github: "janesmith"
```

Keep `private/cover-letters/` for job-specific prose as well.
