# PhotomatorFlagSync

A macOS desktop utility (PySide6) that imports flagged media into Apple Photos.

## Quick Start from Source

1. Open the `Terminal` app on your Mac.
2. Go to this project folder.
   - Type `cd `, drag the folder into Terminal, press Enter.
3. Run:

```bash
./scripts/run-app.sh
```

If you see “permission denied”, run:

```bash
chmod +x scripts/run-app.sh
./scripts/run-app.sh
```

### Build App Bundle (.app)

Run:

```bash
./scripts/build-app.sh
```

Open:

- `dist/PhotomatorFlagSync.app`

### Build an Installer File to Share

Run:

```bash
./scripts/build-installer.sh
```

Output:

- `dist/PhotomatorFlagSync-installer.dmg` (preferred)
- `dist/PhotomatorFlagSync-installer.zip` (fallback)

### Optional: Simple Commands via Make

With `make`:

```bash
make run
make build
make installer
make check
```

## What It Does

- Scans a folder for supported photo/video files.
- Looks for matching `.xmp` sidecars and reads embedded metadata from supported image files (including JPEG).
- Treats `Pick = 1` as flagged (from sidecar or embedded metadata).
- Checks Apple Photos for likely existing imports.
- Imports only flagged files that are not already present.
- Includes a Photos duplicate finder to detect likely duplicates in the library.

## Requirements

- macOS
- Python `3.11+`
- `exiftool` at `/usr/local/bin/exiftool`

## Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
# Optional: pre-install runtime dependencies
python3 -m pip install Pillow PySide6 pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Photos
```

## Manual Run

```bash
source .venv/bin/activate
python3 app.py
```

or

```bash
./scripts/run-app.sh
```

## Permissions (First Run)

macOS may prompt for permissions the first time you use features that touch Photos or control the Photos app.

- **Photos access**: required for duplicate checks, existing-item detection, and imports.
- **Automation/Accessibility (System Events)**: required for "open in Photos" actions.

If needed, re-enable in **System Settings > Privacy & Security** for **Photos** and **Accessibility**.

## Error Reporting

- Operational failures are shown in the UI and written to the in-app log panel with `ERROR [...]` prefixes.
- Unexpected exceptions also write a traceback report to:
  - `~/Library/Application Support/PhotomatorFlagSync/error_reports.log`

## Quality Guardrails

Install checks:

```bash
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
pre-commit install
```

Run checks:

```bash
source .venv/bin/activate
pre-commit run --all-files
python3 tests/smoke_check.py
python3 tests/flag_parsing_check.py
python3 tests/duplicate_matching_check.py
```

CI:

- GitHub Actions runs lint, format check, and compile smoke check on each push and pull request.

## Notes

- Duplicate detection is conservative: it prefers skip-over re-import.
- Sidecar detection targets `.xmp` files named either `photo.ext.xmp` or `photo.xmp`.
- Flag detection can come from `.xmp` sidecars or embedded image metadata (including JPEG metadata).

## Project Layout

- `app.py`: minimal launcher and dependency bootstrap.
- `core/main_window.py`: main Qt UI and event wiring.
- `core/`: internal modules (`config`, `styles`, `photos_bridge`, `workers`, `scan_logic`, `models`, `flag_parsing`, `app_state`, `error_handling`).
- `scripts/`: run/build/installer helper scripts.
- `packaging/`: packaging artifacts such as the PyInstaller spec.
- `assets/`: static visual assets used by runtime/build.
- `docs/`: maintenance and cleanup guardrail documents.

## Release

- `docs/release-checklist.md`
