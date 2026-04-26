from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.flag_parsing import parse_pick_value, parse_xmp_flag


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_xmp_pick_flag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        picked = tmp_path / "picked.xmp"
        write_text(
            picked,
            """<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmp:Pick="1" />
  </rdf:RDF>
</x:xmpmeta>
""",
        )
        assert parse_xmp_flag(picked) is True

        not_picked = tmp_path / "not_picked.xmp"
        write_text(
            not_picked,
            """<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmp:Pick="0" />
  </rdf:RDF>
</x:xmpmeta>
""",
        )
        assert parse_xmp_flag(not_picked) is False


def test_embedded_pick_value_parsing() -> None:
    assert parse_pick_value("1") is True
    assert parse_pick_value(1) is True
    assert parse_pick_value(["0", "1"]) is True
    assert parse_pick_value(["0", " 1 "]) is True

    assert parse_pick_value(None) is False
    assert parse_pick_value("0") is False
    assert parse_pick_value(["0", "0"]) is False


def main() -> int:
    test_xmp_pick_flag()
    test_embedded_pick_value_parsing()
    print("Flag parsing check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
