# PhotomatorFlagSync

A macOS desktop utility (PySide6) that imports flagged media into Apple Photos.

## Quick Start

If you just want to run the app, follow these steps exactly.

1. Open the `Terminal` app on your Mac.
2. Go to this project folder.
   - Tip: type `cd ` (with a space), then drag the folder into Terminal, then press Enter.
3. Run:

```bash
./scripts/run-app.sh
```

If that says “permission denied”, run this once and try again:

```bash
chmod +x scripts/run-app.sh
./scripts/run-app.sh
```

### First Run Prompts

When the app opens the first time, macOS may ask for permissions:

- **Photos**: allow this, so the app can check/import photos.
- **Accessibility** (only if you use “open in Photos” actions): allow this for your Terminal/Python process.

### If You Want a Normal App Icon (.app)

Run:

```bash
./scripts/build-app.sh
```

Then open:

- `dist/PhotomatorFlagSync.app`

### If You Want an Installer File to Share

Run:

```bash
./scripts/build-installer.sh
```

You will get:

- preferred: `dist/PhotomatorFlagSync-installer.dmg`
- fallback: `dist/PhotomatorFlagSync-installer.zip`

### Optional: Simple Commands via Make

If you have `make` available, you can use:

```bash
make run
make build
make installer
make check
```

## App Preview

You can add a screenshot of the current UI at:

- `docs/screenshots/main-window.png`

Then uncomment this line in the README:

<!-- ![PhotomatorFlagSync main window](docs/screenshots/main-window.png) -->

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
- `exiftool` available at `/usr/local/bin/exiftool` (for packaged app and embedded metadata reads)

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
# Optional: pre-install dependencies up front (the app can also auto-install missing ones on launch)
python3 -m pip install Pillow PySide6 pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Photos
```

## Run

```bash
source .venv/bin/activate
python3 app.py
```

or

```bash
./scripts/run-app.sh
```

Expected behavior on first launch:

- macOS asks for Photos permission.
- The app window opens with `Sync` and `DupeFind` workflows.
- If runtime packages are missing when running from source, the app attempts to auto-install them with `pip`.

## Permissions (First Run)

macOS may prompt for permissions the first time you use features that touch Photos or control the Photos app.

- **Photos access**: required to read your library for duplicate checks and existing-item detection, and to import flagged files into Photos.
- **Automation/Accessibility (System Events)**: required when using "open in Photos" actions from duplicate results, so the app can bring Photos to the matching item.

If you denied a prompt and need to re-enable it:

- Open **System Settings > Privacy & Security > Photos** and allow this app.
- Open **System Settings > Privacy & Security > Accessibility** and allow your Python interpreter (or packaged app).

## Error Reporting

- Operational failures are shown in the UI and written to the in-app log panel with `ERROR [...]` prefixes.
- Unexpected exceptions also write a traceback report to:
  - `~/Library/Application Support/PhotomatorFlagSync/error_reports.log`

## Build (PyInstaller)

```bash
source .venv/bin/activate
python3 -m pip install pyinstaller
pyinstaller packaging/PhotomatorFlagSync.spec
```

or

```bash
./scripts/build-app.sh
```

Expected output:

- `dist/PhotomatorFlagSync.app`

## Installer

```bash
./scripts/build-installer.sh
```

Output:

- Preferred: `dist/PhotomatorFlagSync-installer.dmg` (if `create-dmg` is installed)
- Fallback: `dist/PhotomatorFlagSync-installer.zip`

## Quality Guardrails

Install and enable local checks:

```bash
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
pre-commit install
```

Run checks manually:

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

## Cleanup Safety

- Before refactors, run and fill out `docs/behavior-baseline.md`.
- Re-run the same checklist after each cleanup step to confirm no behavior drift.

## Project Layout

- `app.py`: minimal launcher and dependency bootstrap.
- `core/main_window.py`: main Qt UI and event wiring.
- `core/`: internal modules (`config`, `styles`, `photos_bridge`, `workers`, `scan_logic`, `models`, `flag_parsing`, `app_state`, `error_handling`).
- `scripts/`: run/build/installer helper scripts.
- `packaging/`: packaging artifacts such as the PyInstaller spec.
- `assets/`: static visual assets used by runtime/build.
- `docs/`: maintenance and cleanup guardrail documents.

## Release

- See `docs/release-checklist.md` for a simple pre-release checklist.
