from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, UnidentifiedImageError

from core.flag_parsing import parse_pick_value, parse_xmp_flag
from core.models import Candidate

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",
    ".png",
    ".tif",
    ".tiff",
    ".gif",
    ".bmp",
    ".cr2",
    ".cr3",
    ".dng",
    ".nef",
    ".arw",
    ".orf",
    ".raf",
    ".rw2",
    ".mp4",
    ".mov",
    ".m4v",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",
    ".png",
    ".tif",
    ".tiff",
    ".gif",
    ".bmp",
    ".cr2",
    ".cr3",
    ".dng",
    ".nef",
    ".arw",
    ".orf",
    ".raf",
    ".rw2",
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
RAW_EXTENSIONS = {".cr2", ".cr3", ".dng", ".nef", ".arw", ".orf", ".raf", ".rw2"}
EMBEDDED_FLAG_EXTENSIONS = IMAGE_EXTENSIONS - RAW_EXTENSIONS


def iter_photo_files(root: Path, recursive: bool) -> Iterable[Path]:
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def iter_xmp_files(root: Path, recursive: bool) -> Iterable[Path]:
    iterator = root.rglob("*.xmp") if recursive else root.glob("*.xmp")
    for path in iterator:
        if path.is_file():
            yield path


def candidate_sidecars(path: Path) -> list[Path]:
    return [
        path.with_suffix(path.suffix + ".xmp"),
        path.with_suffix(".xmp"),
    ]


def media_candidates_for_sidecar(sidecar_path: Path) -> list[Path]:
    stem = sidecar_path.stem.lower()
    matches = [
        path
        for path in sidecar_path.parent.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and path.stem.lower() == stem
    ]
    return sorted(matches, key=candidate_priority)


def matching_raw_files(path: Path) -> list[Path]:
    stem = path.stem.lower()
    matches = [
        sibling
        for sibling in path.parent.iterdir()
        if sibling.is_file() and sibling.suffix.lower() in RAW_EXTENSIONS and sibling.stem.lower() == stem
    ]
    return sorted(matches, key=lambda item: item.suffix.lower())


def candidate_priority(path: Path) -> tuple[int, int]:
    suffix = path.suffix.lower()
    is_raw = suffix in RAW_EXTENSIONS
    is_jpeg = suffix in {".jpg", ".jpeg"}
    return (1 if is_raw else 0, 0 if is_jpeg else 1)


def collapse_candidates(candidates: list[Candidate]) -> list[Candidate]:
    grouped: dict[str, Candidate] = {}
    for candidate in candidates:
        if candidate.path.suffix.lower() not in RAW_EXTENSIONS:
            raw_matches = matching_raw_files(candidate.path)
            if raw_matches:
                candidate.raw_companion_path = raw_matches[0]
        existing = grouped.get(candidate.stem_key)
        if existing is None or candidate_priority(candidate.path) < candidate_priority(existing.path):
            if existing and existing.raw_companion_path and candidate.raw_companion_path is None:
                candidate.raw_companion_path = existing.raw_companion_path
            grouped[candidate.stem_key] = candidate
        elif existing.raw_companion_path is None and candidate.raw_companion_path is not None:
            existing.raw_companion_path = candidate.raw_companion_path
    return sorted(grouped.values(), key=lambda item: item.path.name.lower())


def get_sidecar_and_flag(path: Path) -> tuple[Path | None, bool]:
    for sidecar in candidate_sidecars(path):
        if sidecar.exists():
            return sidecar, parse_xmp_flag(sidecar)
    return None, False


def extract_embedded_flagged(
    paths: list[Path],
    exiftool_path: str | None,
    progress: Callable[[int, int, str], None] | None = None,
) -> list[Candidate]:
    if not paths or exiftool_path is None:
        return []

    candidates: list[Candidate] = []
    chunk_size = 200
    total = len(paths)

    for offset in range(0, total, chunk_size):
        chunk = paths[offset : offset + chunk_size]
        if progress:
            progress(
                min(offset + len(chunk), total),
                total,
                f"Reading embedded metadata ({offset + 1}-{offset + len(chunk)})...",
            )

        command = [
            exiftool_path,
            "-json",
            "-n",
            "-Pick",
            "-SourceFile",
            *[str(path) for path in chunk],
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            continue
        try:
            records = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        for record in records:
            if not parse_pick_value(record.get("Pick")):
                continue
            source = record.get("SourceFile")
            if not source:
                continue
            path = Path(source)
            if not path.exists():
                continue
            sidecar_path, _ = get_sidecar_and_flag(path)
            candidates.append(
                Candidate(
                    path=path,
                    sidecar_path=sidecar_path,
                    is_flagged=True,
                    fingerprint=source_fingerprint(path),
                )
            )

    return candidates


def image_properties_for_path(path: Path) -> tuple[int | None, int | None, str | None]:
    try:
        with Image.open(path) as image:
            width, height = image.size
            exif = image.getexif()
            exif_date = exif.get(36867) or exif.get(36868) or exif.get(306)
            return width, height, exif_date
    except (UnidentifiedImageError, OSError):
        return None, None, None


def normalize_datetime_text(value: str | None) -> str | None:
    if not value:
        return None

    text = value.strip()
    formats = (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            continue
    return None


def normalize_nsdate(value) -> str | None:
    if value is None:
        return None
    seconds = float(value.timeIntervalSince1970())
    parsed = datetime.fromtimestamp(seconds, timezone.utc).replace(microsecond=0)
    return parsed.isoformat()


def source_fingerprint(path: Path) -> str:
    width, height, exif_date = image_properties_for_path(path)
    stat = path.stat()
    date_text = normalize_datetime_text(exif_date)
    filename = path.name.lower()
    parts = [
        filename,
        str(width or ""),
        str(height or ""),
        date_text or "",
        str(stat.st_size),
    ]
    return "|".join(parts)
