# Behavior Baseline (Pre-cleanup)

Purpose: freeze current behavior before refactoring so cleanup stays zero-risk.

## Scope

This project is considered correct already. This baseline is a guardrail to confirm no behavior drift during cleanup.

## Baseline Checklist

Run this checklist on your known-good sample folder before and after cleanup changes.

1. Launch app with `python3 app.py`.
2. Select the same sample folder each time.
3. Confirm flagged detection count is unchanged.
4. Confirm duplicate-skip behavior is unchanged.
5. Confirm final imported count is unchanged.
6. Confirm no new warnings/errors appear in the UI.

## Capture Template

Record results in this format:

- Date:
- macOS version:
- Python version (`python3 --version`):
- Sample folder path:
- Files scanned:
- Flagged files detected:
- Skipped as likely existing:
- Imported:
- Notes:

## Golden Rule For Cleanup

If any of the counts or outcomes above differ, stop cleanup and treat it as a behavior regression.
