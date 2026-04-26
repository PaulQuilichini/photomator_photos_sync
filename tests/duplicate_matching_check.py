from __future__ import annotations

import os
import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["PHOTOMATOR_SKIP_AUTO_INSTALL"] = "1"

from core.models import Candidate
from core.scan_logic import collapse_candidates, normalize_datetime_text


def touch(path: Path) -> None:
    path.write_bytes(b"")


def test_candidate_collapse_prefers_jpeg_and_keeps_raw_companion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        jpg = root / "IMG_0001.jpg"
        cr3 = root / "IMG_0001.cr3"
        heic = root / "IMG_0001.heic"
        touch(jpg)
        touch(cr3)
        touch(heic)

        candidates = [
            Candidate(path=cr3, sidecar_path=None, is_flagged=True, fingerprint="raw"),
            Candidate(path=heic, sidecar_path=None, is_flagged=True, fingerprint="heic"),
            Candidate(path=jpg, sidecar_path=None, is_flagged=True, fingerprint="jpg"),
        ]
        collapsed = collapse_candidates(candidates)

        assert len(collapsed) == 1
        assert collapsed[0].path == jpg
        assert collapsed[0].raw_companion_path == cr3


def test_datetime_normalization_for_duplicate_matching() -> None:
    expected = "2026-04-01T12:34:56+00:00"
    assert normalize_datetime_text("2026:04:01 12:34:56") == expected
    assert normalize_datetime_text("2026-04-01T12:34:56") == expected
    assert normalize_datetime_text("not-a-date") is None


def main() -> int:
    test_candidate_collapse_prefers_jpeg_and_keeps_raw_companion()
    test_datetime_normalization_for_duplicate_matching()
    print("Duplicate matching check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
