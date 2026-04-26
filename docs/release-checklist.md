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

## 7) Publish Usability Check

- Create a GitHub Release and attach `dist/PhotomatorFlagSync-installer.dmg`
- Give the release notes a plain-language first line: "Download the `.dmg`, drag app to Applications, then open it."
- Verify the `README.md` top section still starts with the release download flow
- Open the release page in a private/incognito window and confirm the installer is visible without signing in
