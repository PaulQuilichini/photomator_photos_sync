# Release Checklist

Use this checklist before publishing a new version of `PhotomatorFlagSync`.

## 1) Validate Locally

- Run `make check`
- Run the app once with `make run`
- Confirm first-run permission prompts still behave correctly

## 2) Build Artifacts

- Build app bundle: `make build`
- Build installer artifact: `make installer`
- Verify output exists in `dist/`

## 3) Smoke Test Built App

- Launch `dist/PhotomatorFlagSync.app`
- Run a quick sync test on a small folder
- Run a quick duplicate scan test

## 4) Documentation Review

- `README.md` still matches actual commands and outputs
- Add/update screenshot in `docs/screenshots/` if UI changed

## 5) Git Hygiene

- `git status` looks intentional
- Commit message clearly describes release/polish work

## 6) Release (Optional)

- Tag release (example): `v1.0.0`
- Attach installer artifact from `dist/`
