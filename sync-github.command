#!/usr/bin/env bash
set -euo pipefail

# Local convenience script: add, commit, and push current branch.
# Not intended for repository distribution.

# Always run from the script's directory so it works from anywhere.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository."
  exit 1
fi

branch="$(git branch --show-current)"
if [[ -z "${branch}" ]]; then
  echo "Could not determine current branch."
  exit 1
fi

git add -A

if git diff --cached --quiet; then
  echo "No staged changes to commit."
  exit 0
fi

default_message="chore: sync ${branch} $(date +'%Y-%m-%d %H:%M')"
commit_message="${1:-$default_message}"

git commit -m "${commit_message}"
git push origin "${branch}"

echo "Synced ${branch} to origin."
