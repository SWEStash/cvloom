#!/usr/bin/env bash
#
# Verify that a project created by the PREVIOUS release upgrades cleanly to the
# working tree. Run once per release, before merging the release PR.
#
#   scripts/verify-upgrade.sh            # previous version from the latest git tag
#   scripts/verify-upgrade.sh 0.6.1      # or name it explicitly
#
# Why this exists: 0.7.0 added `cvloom.yaml`, and nothing brought that file to a
# project scaffolded by 0.6.x. Every unit test passed, because every unit test
# starts from a project the current code created. The gap only appears when the
# project is built by the *old* version and then handed to the new one — which is
# what every real user does, and what this script does.
#
# Needs network: it installs the previous release from PyPI via uvx.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREV="${1:-$(git -C "$REPO_ROOT" describe --tags --abbrev=0 | sed 's/^v//')}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; DIM=$'\033[2m'; NC=$'\033[0m'
fail() { echo "${RED}✗ $1${NC}"; exit 1; }
pass() { echo "${GREEN}✓${NC} $1"; }

echo "Upgrading a project built by cvloom ${PREV} to the working tree"
echo "${DIM}  scratch: ${WORK}${NC}"
echo

# ── 1. Build a project with the PREVIOUS release ──────────────────────────
cd "$WORK"
git init -q .
uvx "cvloom==${PREV}" init >/dev/null 2>&1 || fail "\`uvx cvloom==${PREV} init\` failed — is ${PREV} on PyPI?"
pass "scaffolded a project with ${PREV}"

# It must build under the old version, or the rest proves nothing.
uvx "cvloom==${PREV}" build --profile general --public --skip-pdf >/dev/null 2>&1 \
  || fail "the ${PREV} project does not build under ${PREV}"
pass "it builds under ${PREV}"

BEFORE="$(find . -name '*.html' -newer .git -exec md5sum {} + | sort || true)"

# ── 2. Upgrade it with the working tree — ONE command ─────────────────────
CVLOOM="uv run --project ${REPO_ROOT} cvloom"
$CVLOOM sync --force >"$WORK/sync.log" 2>&1 || { cat "$WORK/sync.log"; fail "\`sync --force\` failed"; }
sed 's/^/    /' "$WORK/sync.log"
pass "one command upgraded it: cvloom sync --force"

# ── 3. Assert the upgrade actually landed ─────────────────────────────────
# Every project-level file the current version expects must now exist. Derived
# from the code, not listed here, so a file added in a later release is covered
# by this script without editing it.
MISSING="$(uv run --project "$REPO_ROOT" python - <<'PY'
from pathlib import Path
from cvloom import config, scaffold
missing = [] if scaffold.config_exists(Path.cwd()) else [config.CONFIG_FILENAME]
missing += [m.dest_rel for m in scaffold.MANAGED_FILES
            if scaffold.managed_status(m, Path.cwd()) not in ("current", "unavailable")]
print(" ".join(missing))
PY
)"
[ -z "$MISSING" ] || fail "still stale after sync --force: $MISSING"
pass "every project file the new version expects is present and current"

# Captured rather than piped into `grep -q`: under `pipefail`, grep exiting early
# closes the pipe, cvloom dies of SIGPIPE, and the pipeline reports a failure that
# never happened.
SECOND="$($CVLOOM sync 2>&1)"
grep -q "up to date" <<<"$SECOND" || { echo "$SECOND"; fail "a second sync does not report a clean project (not idempotent)"; }
pass "sync is idempotent"

# ── 4. The upgraded project must still work ───────────────────────────────
$CVLOOM build --all --public --skip-pdf >/dev/null 2>&1 || fail "the upgraded project does not build"
pass "it builds under the working tree"
# `check` exits non-zero when it finds anything, which is content, not failure.
CHECK="$($CVLOOM check --profile general 2>&1 || true)"
grep -q "rules ran" <<<"$CHECK" || { echo "$CHECK"; fail "\`check\` does not report rule coverage"; }
pass "check runs and reports coverage"

AFTER="$(find . -name '*.html' -newer .git -exec md5sum {} + | sort || true)"
if [ "$BEFORE" != "$AFTER" ]; then
  echo "${DIM}  note: rendered output changed between ${PREV} and this tree.${NC}"
  echo "${DIM}  Expected when a release changes the document; confirm it is intended${NC}"
  echo "${DIM}  and that the release notes say so.${NC}"
fi

echo
echo "${GREEN}Upgrade path verified: ${PREV} → working tree, in one command.${NC}"
