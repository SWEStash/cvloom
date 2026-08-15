# Releasing cvloom

[Back to README](../../README.md)

release-please owns versioning, `CHANGELOG.md` and publishing. Pushing a branch does nothing;
merging to `main` updates a single open **release PR**; merging *that* PR tags, releases and
publishes to PyPI. Several feature PRs can land while the release is held — the release PR is
recomputed from every commit since the last tag, and the highest bump wins.

This page is the **per-release task list**. It is the same every time; work it top to bottom.

---

## 1. Versioning is computed, not chosen

Plain semver, no pre-1.0 special-casing: `fix:` → PATCH, `feat:` → MINOR, breaking → MAJOR.

**Below 1.0.0 a single `!` commit publishes 1.0.0.** Reserve the breaking marker for a
deliberate declaration that the CLI and data schema are stable. A changed *document layout* is
not breaking — the contract is the CLI, the YAML schema, the Python API and the JSON Resume
export.

Squash merges take the PR title as the commit subject, so **PR titles must be Conventional
Commits**. The commit body is the changelog source; do not hand-edit `CHANGELOG.md`.

Before tagging, confirm the bump is the one you meant:

```bash
git log --format='%B' "$(git describe --tags --abbrev=0)"..origin/main \
  | grep -nE '^BREAKING[ -]CHANGE|^[a-z]+(\([^)]*\))?!:'   # expect no output below 1.0.0
```

## 2. Verify the release commit, not yesterday's main

```bash
uv run pytest
uv run ruff check cvloom tests scripts && uv run ruff format --check cvloom tests scripts
uv run mypy cvloom
cd examples    && uv run cvloom build --all --public && uv run cvloom check --profile general
cd examples-es && uv run cvloom build --all --public && uv run cvloom check --profile general
```

`check` exits non-zero when it finds anything — that is content, not a failing gate.

## 3. Verify the upgrade path — the step unit tests cannot cover

```bash
scripts/verify-upgrade.sh          # previous version, from the latest git tag
```

It scaffolds a project with the **previous release** from PyPI, upgrades it with the working
tree using the single documented command, and asserts the result is complete, idempotent and
still builds.

This exists because every unit test starts from a project the *current* code created, so a
project the *old* code created is exactly the case they all miss. 0.7.0 added `cvloom.yaml` and
nothing brought that file to a 0.6.x project; the full suite was green throughout.

**If the release adds a project-level file, `sync` must create it.** That is the contract the
script checks: managed files are byte-compared and overwritten with `--force`; project files are
created when absent and never overwritten. Add the new file to `scaffold` on the correct side of
that line, and to the table in
[keeping-updated.md](../user/keeping-updated.md#2-bring-the-project-up-to-date-with-cvloom-sync).

## 4. Check what the release PR actually says

release-please recomputes the release PR on every push to `main`. Confirm it caught the merge
you just made — **this has silently failed before**, leaving the release PR three sub-phases
stale:

```bash
gh api "repos/SWEStash/cvloom/actions/runs?head_sha=$(git rev-parse origin/main)" --jq '.total_count'
gh pr view 5 --json updatedAt,body   # or whatever number the release PR carries
```

`total_count: 0` means no workflow ran for that push. Nothing will recompute until another push
lands, so push again (an empty commit works) and confirm a `release-please` run appears **before**
merging the release PR.

Then read the generated notes as a user would: every user-visible change should be recognisable
from its subject line, and anything that changes existing output should be obvious.

## 5. Merge the release PR

That merge tags, creates the GitHub release, and publishes to PyPI via trusted publishing.

- The PyPI trusted publisher is scoped to the **workflow filename** (`release-please.yml`).
  Renaming or splitting that workflow breaks publishing with `invalid-publisher`.
- `uv.lock` is refreshed by a step in `release-please.yml`; the release PR carries the hunk.
  Confirm it is there rather than assuming.

## 6. Smoke-test what users will actually install

```bash
cd "$(mktemp -d)" && git init -q .
uvx "cvloom==<new version>" init
uvx "cvloom==<new version>" build --profile general --public
```

A failure here is a new patch release, which is why steps 2 and 3 come first.

---

## Maintainer PII

Nothing in a tracked file may carry the maintainer's identity. Grep the diff before staging;
the shipped hook matches email, phone and credential patterns only — names, employers and
locations pass straight through. See the Maintainer PII section of `CLAUDE.md`.
