from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def ensure_file_exists(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")


def main() -> int:
    app_path = ROOT / "app.py"
    spec_path = ROOT / "packaging" / "PhotomatorFlagSync.spec"
    logo_path = ROOT / "assets" / "logo_poru_main.svg"
    core_dir = ROOT / "core"

    ensure_file_exists(app_path)
    ensure_file_exists(spec_path)
    ensure_file_exists(logo_path)
    ensure_file_exists(core_dir / "__init__.py")

    py_compile.compile(str(app_path), doraise=True)

    app_text = app_path.read_text(encoding="utf-8")
    if 'if __name__ == "__main__":' not in app_text:
        raise SystemExit("Entrypoint guard missing in app.py")
    if "def main() -> int:" not in app_text:
        raise SystemExit("main() function signature missing in app.py")

    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
