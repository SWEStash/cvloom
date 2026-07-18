# Security Policy

## Supported versions

cvloom is pre-1.0 and maintained by a single author. Security fixes land on the latest release
only; please upgrade before reporting (`uv tool upgrade cvloom`).

## Reporting a vulnerability

Please report vulnerabilities **privately** — do not open a public issue.

Use GitHub's private vulnerability reporting: the repository's **Security → Report a vulnerability**
tab (GitHub Security Advisories). Include the affected version, reproduction steps, and impact.

As a solo-maintainer project, there is no formal SLA, but reports are taken seriously and
acknowledged as soon as practical.

## PII-safety posture

cvloom is designed to keep personal contact data out of version control: it lives only in the
gitignored `private/` directory, a pre-commit hook scans staged files for leaks, `--public` builds
strip email and phone, and the MCP server fences PII from agent context. If you find a path where
**real contact data (name, email, phone, address) can leak** — into a tracked file, a `--public`
build, a published GitHub Pages artifact, or an MCP tool response — please report it via the
process above; that is treated as a security issue, not just a bug.
