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

trap 'echo "ERROR: Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

# Ensure we're on the default branch and in sync with remote
DEFAULT_BRANCH="$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')"
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]]; then
    echo "ERROR: Must be on '${DEFAULT_BRANCH}' branch (currently on '${CURRENT_BRANCH}'). Abort." >&2
    exit 1
fi

git fetch origin "$DEFAULT_BRANCH"
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "origin/${DEFAULT_BRANCH}")"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
    echo "ERROR: Local ${DEFAULT_BRANCH} (${LOCAL_SHA:0:8}) differs from remote (${REMOTE_SHA:0:8}). Pull or push first. Abort." >&2
    exit 1
fi

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
CHECKS_FOUND=0
for i in $(seq 1 30); do
    sleep 1
    if gh pr checks 2>&1 | grep -qE 'pending'; then
        CHECKS_FOUND=1
        break
    fi
done

if [[ "$CHECKS_FOUND" -eq 0 ]]; then
    echo "ERROR: No CI checks appeared after 30s. Abort." >&2
    exit 1
fi

echo "==> Watching CI checks..."
if gh pr checks --watch --interval 1 --fail-fast; then
    echo "==> CI passed. Merging..."
    if gh pr merge --squash --delete-branch; then
        echo "==> Merge successful."
    else
        echo "==> Merge failed!"
    fi
fi
