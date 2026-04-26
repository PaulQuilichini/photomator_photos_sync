from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.error_handling import format_unexpected_error
from core.flag_parsing import parse_xmp_flag
from core.models import Candidate, DuplicateGroup
from core.photos_bridge import PHAsset, PHAssetResource, PhotosLibraryBridge
from core.scan_logic import (
    EMBEDDED_FLAG_EXTENSIONS,
    RAW_EXTENSIONS,
    collapse_candidates,
    extract_embedded_flagged,
    iter_photo_files,
    iter_xmp_files,
    media_candidates_for_sidecar,
    normalize_nsdate,
    source_fingerprint,
)


class ScanWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list, str)

    def __init__(
        self, folder: str, recursive: bool, photos_bridge: PhotosLibraryBridge, exiftool_path: str | None
    ) -> None:
        super().__init__()
        self.folder = Path(folder).expanduser()
        self.recursive = recursive
        self.photos_bridge = photos_bridge
        self.exiftool_path = exiftool_path

    def run(self) -> None:
        try:
            flagged_candidates: list[Candidate] = []
            embedded_paths = [
                path
                for path in iter_photo_files(self.folder, self.recursive)
                if path.suffix.lower() in EMBEDDED_FLAG_EXTENSIONS
            ]
            flagged_candidates.extend(
                extract_embedded_flagged(
                    embedded_paths,
                    self.exiftool_path,
                    progress=lambda current, total, message: self.progress.emit(current, total, message),
                )
            )

            sidecars = list(iter_xmp_files(self.folder, self.recursive))

            for index, sidecar in enumerate(sidecars, start=1):
                self.progress.emit(index, len(sidecars), f"Scanning sidecar {sidecar.name}...")
                is_flagged = parse_xmp_flag(sidecar)
                if not is_flagged:
                    continue

                media_matches = media_candidates_for_sidecar(sidecar)
                for path in media_matches:
                    if path.suffix.lower() not in RAW_EXTENSIONS:
                        continue
                    fingerprint = source_fingerprint(path)
                    candidate = Candidate(path=path, sidecar_path=sidecar, is_flagged=True, fingerprint=fingerprint)
                    flagged_candidates.append(candidate)

            candidates = collapse_candidates(flagged_candidates)
            if not candidates:
                self.finished.emit([], "")
                return

            ok, message = self.photos_bridge.ensure_authorized()
            if not ok:
                self.finished.emit(candidates, message)
                return

            self.progress.emit(0, 0, f"Indexing Photos library for {len(candidates)} flagged item(s)...")
            self.photos_bridge.build_index(
                progress=lambda current, total: self.progress.emit(
                    current, total, f"Indexing Photos library ({current}/{total})..."
                )
            )

            for index, candidate in enumerate(candidates, start=1):
                self.progress.emit(index, len(candidates), f"Checking Photos for {candidate.path.name}...")
                candidate.duplicate_reason = self.photos_bridge.match_reason(candidate)

            self.finished.emit(candidates, "")
        except Exception as exc:
            self.finished.emit([], format_unexpected_error("Scan", exc))


class ImportWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(int, list, str)

    def __init__(
        self,
        candidates: list[Candidate],
        include_raw_companion: bool,
        album_name: str,
        photos_bridge: PhotosLibraryBridge,
    ) -> None:
        super().__init__()
        self.candidates = candidates
        self.include_raw_companion = include_raw_companion
        self.album_name = album_name
        self.photos_bridge = photos_bridge

    def run(self) -> None:
        try:
            ok, message = self.photos_bridge.ensure_authorized()
            if not ok:
                self.finished.emit(0, [], message)
                return

            importable: list[Path] = []
            seen_paths: set[Path] = set()
            for candidate in self.candidates:
                if candidate.already_in_photos:
                    continue
                for path in candidate.import_paths(self.include_raw_companion):
                    if path in seen_paths:
                        continue
                    seen_paths.add(path)
                    importable.append(path)
            total = len(importable)
            if total == 0:
                self.finished.emit(0, [], "")
                return

            imported = 0
            errors: list[str] = []
            for index, path in enumerate(importable, start=1):
                self.progress.emit(index, total, f"Importing {path.name}...")
                current_imported, current_errors = self.photos_bridge.import_files([path], self.album_name)
                imported += current_imported
                errors.extend(current_errors)

            self.finished.emit(imported, errors, "")
        except Exception as exc:
            self.finished.emit(0, [], format_unexpected_error("Import", exc))


class DuplicateScanWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list, str)

    def __init__(self, album_name: str, strict_mode: bool, photos_bridge: PhotosLibraryBridge) -> None:
        super().__init__()
        self.album_name = album_name.strip()
        self.strict_mode = strict_mode
        self.photos_bridge = photos_bridge

    def run(self) -> None:
        try:
            ok, message = self.photos_bridge.ensure_authorized()
            if not ok:
                self.finished.emit([], message)
                return

            if self.album_name:
                album = self.photos_bridge.find_album_by_title(self.album_name)
                if album is None:
                    self.finished.emit([], f"Album '{self.album_name}' was not found in Photos.")
                    return
                assets = PHAsset.fetchAssetsInAssetCollection_options_(album, None)
                scope_label = f"album '{self.album_name}'"
            else:
                assets = PHAsset.fetchAssetsWithOptions_(None)
                scope_label = "Photos library"
            count = int(assets.count())
            grouped: dict[str, list[tuple[str, str]]] = {}

            for index in range(count):
                asset = assets.objectAtIndex_(index)
                resources = PHAssetResource.assetResourcesForAsset_(asset)
                if not resources:
                    continue

                resource = next((item for item in resources if hasattr(item, "originalFilename")), resources[0])
                filename = str(resource.originalFilename())
                created = normalize_nsdate(asset.creationDate()) or ""
                width = int(asset.pixelWidth())
                height = int(asset.pixelHeight())
                key_parts = [filename.lower(), str(width), str(height), created]
                if self.strict_mode:
                    try:
                        file_size = str(resource.valueForKey_("fileSize") or "")
                    except Exception:
                        file_size = ""
                    try:
                        uti = str(resource.valueForKey_("uniformTypeIdentifier") or "")
                    except Exception:
                        uti = ""
                    key_parts.extend([file_size, uti])
                key = "|".join(key_parts)
                grouped.setdefault(key, []).append((filename, str(asset.localIdentifier())))
                self.progress.emit(index + 1, count, f"Scanning {scope_label} ({index + 1}/{count})...")

            duplicates: list[DuplicateGroup] = []
            for key, items in grouped.items():
                if len(items) < 2:
                    continue
                filenames = ", ".join(item[0] for item in items)
                identifier_list = [item[1] for item in items]
                identifiers = "\n".join(identifier_list)
                duplicates.append(
                    DuplicateGroup(
                        key=key,
                        count=len(items),
                        filenames=filenames,
                        identifiers_text=identifiers,
                        identifiers=identifier_list,
                        created=created,
                    )
                )

            duplicates.sort(key=lambda item: (-item.count, item.filenames.lower()))
            self.finished.emit(duplicates, "")
        except Exception as exc:
            self.finished.emit([], format_unexpected_error("Duplicate scan", exc))
