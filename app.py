from __future__ import annotations

import importlib
import os
import subprocess
import sys


def ensure_runtime_dependencies() -> None:
    """Install missing runtime dependencies when running from source."""
    if getattr(sys, "frozen", False):
        return
    if os.environ.get("PHOTOMATOR_SKIP_AUTO_INSTALL") == "1":
        return

    required_modules = [
        ("Pillow", "PIL"),
        ("PySide6", "PySide6"),
        ("pyobjc-core", "objc"),
        ("pyobjc-framework-Cocoa", "Foundation"),
        ("pyobjc-framework-Photos", "Photos"),
    ]
    missing_packages: list[str] = []
    for package_name, module_name in required_modules:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing_packages.append(package_name)

    if not missing_packages:
        return

    print(f"Installing missing dependencies: {', '.join(missing_packages)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Failed to install dependencies automatically: {exc}") from exc


ensure_runtime_dependencies()

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.config import APP_NAME
from core.main_window import APP_ICON_PATH, MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
