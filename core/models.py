from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Candidate:
    path: Path
    sidecar_path: Path | None
    is_flagged: bool
    fingerprint: str
    raw_companion_path: Path | None = None
    duplicate_reason: str | None = None

    @property
    def already_in_photos(self) -> bool:
        return self.duplicate_reason is not None

    @property
    def stem_key(self) -> str:
        return self.path.stem.lower()

    def import_paths(self, include_raw_companion: bool) -> list[Path]:
        paths = [self.path]
        if include_raw_companion and self.raw_companion_path and self.raw_companion_path != self.path:
            paths.append(self.raw_companion_path)
        return paths


@dataclass(slots=True)
class DuplicateGroup:
    key: str
    count: int
    filenames: str
    identifiers_text: str
    identifiers: list[str]
    created: str
