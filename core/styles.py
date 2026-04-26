from __future__ import annotations

from core.config import APP_FONT_PT


def app_palette() -> dict[str, str]:
    return {
        "bg": "#f4f6f8",
        "surface": "#ffffff",
        "surface_alt": "#fbfcfd",
        "text": "#1f2329",
        "muted": "#6e737b",
        "border": "#d9dde2",
        "separator": "#e8ebef",
        "accent": "#43d0b7",
        "accent_hover": "#38bea6",
        "accent_pressed": "#2fa58f",
        "accent_soft": "#c9f2ea",
        "accent_text": "#143731",
        "danger": "#d14343",
        "btn_neutral": "#f4f5f7",
        "btn_neutral_hover": "#eceef1",
        "btn_neutral_pressed": "#e3e6ea",
        "segment_track": "#d9dde2",
        "segment_border": "#cfd4da",
        "selection": "#d8ecff",
        "selection_border": "#b9dafc",
    }


def build_stylesheet(palette: dict[str, str]) -> str:
    p = palette
    fs = f"{APP_FONT_PT}pt"
    return f"""
        QWidget {{ font-size: {fs}; color: {p["text"]}; }}
        QMainWindow {{ background-color: {p["bg"]}; }}
        QLabel {{ color: {p["text"]}; }}
        QLabel#SummaryLabel {{ color: {p["muted"]}; font-weight: 500; }}
        QLabel#SectionLabel {{
            color: {p["muted"]};
            font-size: 11pt;
            font-weight: 600;
        }}
        QFrame#FormPanel, QFrame#ActionPanel, QFrame#ContentPanel {{
            background-color: transparent;
            border: none;
        }}
        QFrame#SegmentShell {{
            background-color: transparent;
            border: none;
        }}
        QLineEdit {{
            background-color: {p["surface_alt"]};
            border: 1px solid {p["border"]};
            padding: 9px 12px;
            border-radius: 10px;
        }}
        QLineEdit:focus {{
            border-color: {p["accent_hover"]};
            background-color: {p["surface"]};
        }}
        QCheckBox {{
            spacing: 10px;
            padding: 2px 0px;
        }}
        QPushButton#Primary {{
            background-color: {p["accent"]};
            color: {p["accent_text"]};
            border: 1px solid {p["accent_hover"]};
            padding: 0px 20px;
            border-radius: 11px;
            font-weight: 600;
        }}
        QPushButton#Primary:hover {{ background-color: {p["accent_hover"]}; }}
        QPushButton#Primary:pressed {{ background-color: {p["accent_pressed"]}; }}
        QPushButton#Primary:disabled {{ background-color: #d8eeea; color: #7a8f8b; border-color: #d1e7e2; }}
        QPushButton#Secondary {{
            background-color: {p["btn_neutral"]};
            color: {p["text"]};
            border: 1px solid {p["border"]};
            padding: 0px 20px;
            border-radius: 11px;
            font-weight: 500;
        }}
        QPushButton#Secondary:hover {{ background-color: {p["btn_neutral_hover"]}; }}
        QPushButton#Secondary:pressed {{ background-color: {p["btn_neutral_pressed"]}; }}
        QPushButton#Secondary:disabled {{ background-color: #f2f3f5; color: #a2a8b0; border-color: #dde1e6; }}
        QProgressBar {{
            background-color: rgba(255, 255, 255, 0.75);
            border: 1px solid {p["separator"]};
            border-radius: 7px;
            text-align: center;
            min-height: 18px;
        }}
        QProgressBar::chunk {{
            background-color: {p["accent"]};
            border-radius: 6px;
        }}
        QTableWidget {{
            background-color: {p["surface"]};
            border: 1px solid {p["separator"]};
            border-radius: 12px;
            gridline-color: {p["separator"]};
            selection-background-color: {p["selection"]};
            selection-color: {p["text"]};
            alternate-background-color: #fafbfd;
            padding: 2px;
        }}
        QHeaderView::section {{
            background-color: transparent;
            color: {p["muted"]};
            border: none;
            border-bottom: 1px solid {p["separator"]};
            padding: 8px 10px;
            font-weight: 500;
        }}
        QPlainTextEdit {{
            background-color: {p["surface"]};
            border: 1px solid {p["separator"]};
            border-radius: 14px;
            padding: 14px;
            font-family: Menlo, Monaco, "Courier New", monospace;
        }}
        QFrame#SegmentedTrack {{
            background-color: #d7dce2;
            border: none;
            border-radius: 16px;
        }}
        QToolButton#SegTabSync, QToolButton#SegTabDupes {{
            background-color: transparent;
            border: none;
            color: {p["muted"]};
            font-weight: 500;
            padding: 0px 16px;
            margin: 0px;
            min-height: 26px;
            max-height: 26px;
        }}
        QToolButton#SegTabSync:checked, QToolButton#SegTabDupes:checked {{
            background-color: {p["surface"]};
            color: {p["text"]};
            font-weight: 600;
            border-radius: 13px;
            border: none;
        }}
        QToolButton#SegTabSync:hover:!checked, QToolButton#SegTabDupes:hover:!checked {{
            color: {p["text"]};
        }}
        QSplitter::handle {{
            background-color: transparent;
        }}
        QSplitter::handle:horizontal {{
            width: 10px;
        }}
        QSplitter::handle:vertical {{
            height: 10px;
        }}
        QMessageBox {{
            background-color: {p["bg"]};
        }}
    """
