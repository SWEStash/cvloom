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

Installed by `cvloom init` (refresh it later with `cvloom sync`). Two rules:

1. **Anything staged under `private/` blocks the commit outright.** That directory should be gitignored; staging a file from it is the failure the hook exists to catch.
2. **Added lines are scanned for email addresses and phone numbers.** A match outside `private/` blocks the commit and prints the offending value.

### Why added lines, not whole files

The hook diffs what you are introducing. Re-scanning entire files means every commit touching a file that has always held a placeholder gets blocked — which trains you to reach for `--no-verify` by reflex, the exact habit that eventually lets real PII through.

### Reserved placeholder values

Values reserved for documentation and testing are never real contact data, so the hook allows them:

| Kind | Allowed | Source |
|---|---|---|
| Email | `example.com`, `example.org`, `example.net` | RFC 2606 |
| Email | any `.example`, `.test`, `.invalid` domain | RFC 2606 |
| Email | any `.localhost` domain | RFC 6761 |
| Phone | North American `555` exchange — e.g. `+1 (555) 123-4567` | NANP fiction range |
| Phone | UK Ofcom drama range — e.g. `+44 7700 900123` | Ofcom |

Prefer these in sample data, docs, and tests. A placeholder the hook recognises is better than one you have to bypass.

To bypass anyway:
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
