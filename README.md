# Photomator Flag Sync

Small macOS utility with a PySide6 GUI that:

- scans a folder for supported photo/video files
- looks for matching `.xmp` sidecars
- treats `XMP Pick = 1` as flagged
- checks Apple Photos for likely existing imports
- imports only the flagged files not already present

## Run

```bash
python3 app.py
```

## Notes

- The app uses PhotoKit, so macOS will prompt for Photos access the first time you run it.
- Duplicate detection is conservative. It prefers skipping a likely existing item rather than re-importing it.
- Sidecar detection currently targets standard `.xmp` sidecars named either `photo.ext.xmp` or `photo.xmp`.
