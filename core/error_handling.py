from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback


ERROR_REPORT_PATH = Path.home() / "Library" / "Application Support" / "PhotomatorFlagSync" / "error_reports.log"


def write_error_report(context: str, exc: Exception) -> str:
    ERROR_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"[{timestamp}] {context}",
        f"{type(exc).__name__}: {exc}",
        "".join(traceback.format_exception(exc)),
        "-" * 80,
        "",
    ]
    try:
        with ERROR_REPORT_PATH.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    except OSError:
        pass
    return str(ERROR_REPORT_PATH)


def format_unexpected_error(context: str, exc: Exception) -> str:
    report_path = write_error_report(context, exc)
    return (
        f"{context} failed with an unexpected error:\n"
        f"{type(exc).__name__}: {exc}\n\n"
        f"A detailed traceback was written to:\n{report_path}"
    )
