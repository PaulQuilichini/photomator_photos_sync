#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller
pyinstaller "packaging/PhotomatorFlagSync.spec"

echo "Built app: dist/PhotomatorFlagSync.app"
