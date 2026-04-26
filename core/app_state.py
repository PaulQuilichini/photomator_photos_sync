from __future__ import annotations

import json
from pathlib import Path


def load_persisted_app_data(app_data_path: Path) -> dict:
    if not app_data_path.exists():
        return default_app_data()
    try:
        data = json.loads(app_data_path.read_text())
    except (OSError, json.JSONDecodeError):
        return default_app_data()
    data.setdefault("last_folder", "")
    data.setdefault("scan_subfolders", True)
    data.setdefault("include_raw", False)
    data.setdefault("album_name", "")
    data.setdefault("dupe_album_name", "")
    data.setdefault("dupe_strict_mode", False)
    data.setdefault("history", [])
    return data


def save_persisted_app_data(app_data_path: Path, data: dict) -> None:
    app_data_path.write_text(json.dumps(data, indent=2))


def format_history_entry(entry: dict) -> str:
    timestamp = entry.get("timestamp", "")
    imported = entry.get("imported", 0)
    folder = entry.get("folder", "")
    include_raw = "yes" if entry.get("include_raw") else "no"
    album_name = entry.get("album_name", "")
    files = entry.get("files", [])
    lines = [f"{timestamp} | imported {imported} file(s) | include RAW: {include_raw}", folder]
    if album_name:
        lines.append(f"album: {album_name}")
    if files:
        lines.extend(f"  - {name}" for name in files[:20])
        if len(files) > 20:
            lines.append(f"  - ... {len(files) - 20} more")
    if entry.get("errors"):
        lines.append("  errors:")
        lines.extend(f"  - {item}" for item in entry["errors"][:10])
    return "\n".join(lines)


def default_app_data() -> dict:
    return {
        "last_folder": "",
        "scan_subfolders": True,
        "include_raw": False,
        "album_name": "",
        "dupe_album_name": "",
        "dupe_strict_mode": False,
        "history": [],
    }
