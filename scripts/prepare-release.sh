#!/usr/bin/env bash
# Create a release branch from the current (already bumped) version,
# sync lockfile, commit, push, open PR, and watch CI checks.
#
# Usage: ./scripts/prepare-release.sh
#
# Prerequisites:
#   - bump-my-version bump has already been run (without --commit)
#   - Working directory is the repo root
#   - gh CLI is authenticated

set -euo pipefail

# Ensure no uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: Working directory has uncommitted changes. Abort." >&2
    exit 1
fi

# Ensure we're on main and in sync with remote
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "==> Switching to main branch"
    git checkout main
fi
echo "==> Pulling latest from remote"
git pull --ff-only origin main

VERSION="$(bump-my-version show current_version)"
if [[ -z "$VERSION" ]]; then
    echo "ERROR: Could not determine current version" >&2
    exit 1
fi

# Detect if this is an RC version
if [[ "$VERSION" =~ -rc[0-9]+$ ]]; then
    BRANCH="chore/bump-${VERSION}"
    PR_TITLE="Bumping version to ${VERSION}"
    # Revert RC heading in CHANGELOG.md — keep only ## Unreleased
    if ! python scripts/revert_changelog_rc.py; then
        echo "WARNING: revert_changelog_rc.py failed" >&2
    fi
else
    BRANCH="chore/release-${VERSION}"
    PR_TITLE="Release ${VERSION}"
fi

echo "==> Preparing release for v${VERSION} on branch ${BRANCH}"

# Create branch
git checkout -b "${BRANCH}"

# Sync lockfile
UV_LOCKED=0 uv sync --all-groups

# Commit all bumped files + lockfile
git add -A
git commit --no-edit -m "Bump version: ${VERSION}"

# Push and create PR
git push --set-upstream origin "${BRANCH}"
gh pr create --title "${PR_TITLE}" --body "${PR_TITLE}"

echo "==> Waiting for CI checks to be registered..."
for i in $(seq 1 30); do
    if gh pr checks 2>&1 | grep -qv "no checks"; then
        break
    fi
    sleep 2
done

echo "==> Watching CI checks..."
gh pr checks --watch --fail-fast

echo "==> CI passed. Ready to merge."
