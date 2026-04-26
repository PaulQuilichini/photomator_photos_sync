# Contributing

Thanks for improving `PhotomatorFlagSync`.

## Ground Rules

- Preserve behavior unless the change explicitly targets behavior.
- Keep changes small, focused, and easy to review.
- Favor clear names over clever abstractions.

## Local Workflow

```bash
./scripts/run-app.sh
```

Quality checks:

```bash
pre-commit run --all-files
python3 tests/smoke_check.py
python3 tests/flag_parsing_check.py
python3 tests/duplicate_matching_check.py
```

## Build + Installer

```bash
./scripts/build-app.sh
./scripts/build-installer.sh
```

## Project Structure

- `app.py`: launcher/bootstrap only.
- `core/main_window.py`: primary UI and interactions.
- `core/`: domain logic, workers, Photos bridge, state, and error handling.
- `packaging/`: PyInstaller spec and packaging assets.
- `tests/`: deterministic script-based checks.
