from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.app_state import format_history_entry, load_persisted_app_data, save_persisted_app_data
from core.config import (
    ACCESSIBILITY_SETTINGS_URL,
    APP_FONT_PT,
    APP_NAME,
    APP_SUPPORT_DIR_NAME,
    CONTACT_EMAIL,
    CONTACT_WEBSITE,
    CONTROL_HEIGHT_PX,
    DEFAULT_SOURCE_FOLDER,
    HEADER_LOGO_SIZE_PX,
    PHOTOS_SETTINGS_URL,
)
from core.models import Candidate, DuplicateGroup
from core.photos_bridge import PhotosLibraryBridge
from core.styles import app_palette, build_stylesheet
from core.workers import DuplicateScanWorker, ImportWorker, ScanWorker


def resource_base_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def app_support_dir() -> Path:
    path = Path.home() / "Library" / "Application Support" / APP_SUPPORT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def first_existing_resource_path(*candidates: str) -> Path:
    for candidate in candidates:
        path = RESOURCE_BASE_PATH / candidate
        if path.exists():
            return path
    return RESOURCE_BASE_PATH / candidates[0]


RESOURCE_BASE_PATH = resource_base_path()
APP_DATA_PATH = app_support_dir() / "app_state.json"
APP_ICON_PATH = first_existing_resource_path(
    "assets/logo_poru_main.svg",
    "logo_poru_main.svg",
    "assets/logo_poru.svg",
    "logo_poru.svg",
    "assets/pq_logo_smiling.png",
    "pq_logo_smiling.png",
    "assets/pq_logo_smiling.svg",
    "pq_logo_smiling.svg",
)
APP_HEADER_LOGO_PATH = first_existing_resource_path(
    "assets/logo_poru_main.svg",
    "logo_poru_main.svg",
    "assets/logo_poru.svg",
    "logo_poru.svg",
    "assets/pq_logo_smiling.svg",
    "pq_logo_smiling.svg",
    "assets/pq_logo_smiling.png",
    "pq_logo_smiling.png",
)
EXIFTOOL_PATH = (
    str(RESOURCE_BASE_PATH / "exiftool") if (RESOURCE_BASE_PATH / "exiftool").exists() else shutil.which("exiftool")
)


class ToggleSwitch(QCheckBox):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(26)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(max(hint.height(), 26))
        hint.setWidth(hint.width() + 14)
        return hint

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        track_w = 38
        track_h = 22
        margin = 2
        track_x = 0
        track_y = (rect.height() - track_h) // 2
        track_rect = rect.adjusted(track_x, track_y, -(rect.width() - track_w), -(rect.height() - track_y - track_h))

        palette = app_palette()
        track_color = QColor(palette["accent"] if self.isChecked() else palette["segment_track"])
        border_color = QColor(palette["accent_hover"] if self.isChecked() else palette["border"])
        thumb_color = QColor("#ffffff")
        text_color = QColor(palette["text"])

        painter.setPen(border_color)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, 11, 11)

        thumb_d = 16
        thumb_x = (
            track_rect.x() + track_rect.width() - thumb_d - margin if self.isChecked() else track_rect.x() + margin
        )
        thumb_y = track_rect.y() + (track_h - thumb_d) // 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_x, thumb_y, thumb_d, thumb_d)

        text_rect = rect.adjusted(track_w + 10, 0, 0, 0)
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


def applescript_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def search_photos_for_filename(filename: str) -> tuple[bool, str]:
    query = filename.strip()
    if not query:
        return False, "No filename was available to search in Photos."
    result = subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Photos" to activate',
            "-e",
            "delay 0.5",
            "-e",
            'tell application "System Events"',
            "-e",
            'tell process "Photos" to click menu item "Find" of menu 1 of menu bar item "Edit" of menu bar 1',
            "-e",
            "delay 0.2",
            "-e",
            'keystroke "a" using {command down}',
            "-e",
            "delay 0.1",
            "-e",
            "key code 51",
            "-e",
            "delay 0.1",
            "-e",
            f"keystroke {applescript_quote(query)}",
            "-e",
            "end tell",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True, ""
    details = (result.stderr or result.stdout or "").strip()
    if "not allowed to send keystrokes" in details:
        return (
            False,
            "macOS blocked keyboard automation. In System Settings > Privacy & Security > Accessibility, enable the actual process running this app: usually Terminal.app or iTerm.app, and if needed the Python executable used for `python3 app.py`.",
        )
    return False, details or "Photos could not search for the requested filename."


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(980, 680)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self._palette = app_palette()
        self.setStyleSheet(build_stylesheet(self._palette))
        base_font = QFont()
        base_font.setPointSize(APP_FONT_PT)
        self.setFont(base_font)

        self.photos_bridge = PhotosLibraryBridge()
        self.app_data = load_persisted_app_data(APP_DATA_PATH)
        self.scan_thread: QThread | None = None
        self.import_thread: QThread | None = None
        self.dupe_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.import_worker: ImportWorker | None = None
        self.dupe_worker: DuplicateScanWorker | None = None
        self.candidates: list[Candidate] = []
        self.duplicate_groups: list[DuplicateGroup] = []
        self.last_import_paths: list[Path] = []

        default_folder = (
            Path(self.app_data["last_folder"]).expanduser()
            if self.app_data.get("last_folder")
            else (DEFAULT_SOURCE_FOLDER if DEFAULT_SOURCE_FOLDER.exists() else Path.home() / "Pictures")
        )
        self.folder_edit = QLineEdit(str(default_folder))
        self.browse_button = QPushButton("Browse…")
        self.scan_button = QPushButton("Scan")
        self.import_button = QPushButton("Import To Photos")
        self.import_button.setEnabled(False)
        self.dupe_scan_button = QPushButton("Scan Photos For Duplicates")
        self.dupe_delete_button = QPushButton("Delete Selected Duplicates")
        self.dupe_delete_button.setEnabled(False)
        self.recursive_checkbox = ToggleSwitch("Scan subfolders")
        self.recursive_checkbox.setChecked(bool(self.app_data.get("scan_subfolders", True)))
        self.include_raw_checkbox = ToggleSwitch("Import matching RAW files")
        self.include_raw_checkbox.setChecked(bool(self.app_data.get("include_raw", False)))
        self.album_edit = QLineEdit(self.app_data.get("album_name", ""))
        self.album_edit.setPlaceholderText("Optional target album")
        self.dupe_album_edit = QLineEdit(self.app_data.get("dupe_album_name", ""))
        self.dupe_album_edit.setPlaceholderText("Blank = whole Photos library")
        self.dupe_strict_checkbox = ToggleSwitch("Exact mode (adds resource size/type)")
        self.dupe_strict_checkbox.setChecked(bool(self.app_data.get("dupe_strict_mode", False)))

        self.summary_label = QLabel("Choose a folder and scan for flagged photos.")
        self.summary_label.setObjectName("SummaryLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Photo", "Sidecar", "Status", "Reason"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 140)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.history_view = QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setMaximumBlockCount(500)
        self.dupe_summary_label = QLabel("Scan your Photos library for likely duplicate assets.")
        self.dupe_summary_label.setObjectName("SummaryLabel")
        self.dupe_progress_bar = QProgressBar()
        self.dupe_progress_bar.setRange(0, 1)
        self.dupe_progress_bar.setValue(0)
        self.dupe_table = QTableWidget(0, 4)
        self.dupe_table.setHorizontalHeaderLabels(["Count", "Filenames", "Created", "Local Identifiers"])
        self.dupe_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.dupe_table.horizontalHeader().setStretchLastSection(True)
        self.dupe_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dupe_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dupe_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.dupe_table.setAlternatingRowColors(True)
        self.dupe_table.setColumnWidth(0, 70)
        self.dupe_table.setColumnWidth(1, 320)
        self.dupe_table.setColumnWidth(2, 180)

        self.browse_button.setObjectName("Secondary")
        self.scan_button.setObjectName("Secondary")
        self.import_button.setObjectName("Primary")
        self.dupe_scan_button.setObjectName("Secondary")
        self.dupe_delete_button.setObjectName("Secondary")
        for button in (
            self.browse_button,
            self.scan_button,
            self.import_button,
            self.dupe_scan_button,
            self.dupe_delete_button,
        ):
            button.setFixedHeight(CONTROL_HEIGHT_PX)

        self.sync_tab_button = QToolButton()
        self.sync_tab_button.setObjectName("SegTabSync")
        self.sync_tab_button.setText("PhotomatorSync")
        self.sync_tab_button.setCheckable(True)
        self.sync_tab_button.setChecked(True)
        self.sync_tab_button.setFixedHeight(CONTROL_HEIGHT_PX - 4)
        self.sync_tab_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.dupe_tab_button = QToolButton()
        self.dupe_tab_button.setObjectName("SegTabDupes")
        self.dupe_tab_button.setText("DupeFind")
        self.dupe_tab_button.setCheckable(True)
        self.dupe_tab_button.setChecked(False)
        self.dupe_tab_button.setFixedHeight(CONTROL_HEIGHT_PX - 4)
        self.dupe_tab_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        segmented_track = QFrame()
        segmented_track.setObjectName("SegmentedTrack")
        segmented_track.setFixedHeight(CONTROL_HEIGHT_PX)
        segmented_layout = QHBoxLayout(segmented_track)
        segmented_layout.setContentsMargins(2, 2, 2, 2)
        segmented_layout.setSpacing(0)
        segmented_layout.addWidget(self.sync_tab_button, 1)
        segmented_layout.addWidget(self.dupe_tab_button, 1)

        segmented_container = QFrame()
        segmented_container.setObjectName("SegmentShell")
        segmented_container_layout = QVBoxLayout(segmented_container)
        segmented_container_layout.setContentsMargins(0, 8, 0, 0)
        segmented_container_layout.setSpacing(0)
        segmented_container_layout.addWidget(segmented_track)

        if APP_HEADER_LOGO_PATH.exists() and APP_HEADER_LOGO_PATH.suffix.lower() == ".svg":
            self.logo_label = QSvgWidget(str(APP_HEADER_LOGO_PATH))
            self.logo_label.setFixedSize(HEADER_LOGO_SIZE_PX, HEADER_LOGO_SIZE_PX)
        else:
            self.logo_label = QLabel()
            self.logo_label.setFixedSize(HEADER_LOGO_SIZE_PX, HEADER_LOGO_SIZE_PX)
            if APP_HEADER_LOGO_PATH.exists():
                logo_pixmap = QPixmap(str(APP_HEADER_LOGO_PATH)).scaled(
                    HEADER_LOGO_SIZE_PX,
                    HEADER_LOGO_SIZE_PX,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.logo_label.setPixmap(logo_pixmap)
                self.logo_label.setAlignment(Qt.AlignCenter)

        top_layout = QGridLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setHorizontalSpacing(12)
        top_layout.setVerticalSpacing(10)
        top_layout.addWidget(QLabel("Folder"), 0, 0)
        top_layout.addWidget(self.folder_edit, 0, 1)
        top_layout.addWidget(self.browse_button, 0, 2)
        toggle_row = QGridLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setHorizontalSpacing(28)
        toggle_row.setVerticalSpacing(0)
        toggle_row.addWidget(self.recursive_checkbox, 0, 0)
        toggle_row.addWidget(self.include_raw_checkbox, 0, 1)
        toggle_row.setColumnStretch(0, 1)
        toggle_row.setColumnStretch(1, 1)
        top_layout.addLayout(toggle_row, 1, 1, 1, 2)
        top_layout.addWidget(QLabel("Target album"), 2, 0)
        top_layout.addWidget(self.album_edit, 2, 1, 1, 2)
        top_layout.setColumnStretch(1, 1)

        top_panel = QFrame()
        top_panel.setObjectName("FormPanel")
        top_panel.setLayout(top_layout)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(10)
        button_row.addWidget(self.scan_button)
        button_row.addWidget(self.import_button)
        button_row.addStretch(1)

        action_panel = QFrame()
        action_panel.setObjectName("ActionPanel")
        action_panel.setLayout(button_row)

        sync_page = QWidget()
        sync_layout = QVBoxLayout(sync_page)
        sync_layout.setContentsMargins(0, 0, 0, 0)
        sync_layout.setSpacing(10)
        sync_layout.addWidget(top_panel)
        sync_layout.addWidget(action_panel)
        sync_layout.addWidget(self.summary_label)
        sync_layout.addWidget(self.progress_bar)

        log_panel = QFrame()
        log_panel.setObjectName("ContentPanel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)
        log_label = QLabel("Log")
        log_label.setObjectName("SectionLabel")
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log)

        history_panel = QFrame()
        history_panel.setObjectName("ContentPanel")
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)
        history_label = QLabel("Import History")
        history_label.setObjectName("SectionLabel")
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_view)

        lower_splitter = QSplitter(Qt.Horizontal)
        lower_splitter.addWidget(log_panel)
        lower_splitter.addWidget(history_panel)
        lower_splitter.setChildrenCollapsible(False)
        lower_splitter.setSizes([520, 360])

        sync_splitter = QSplitter(Qt.Vertical)
        sync_splitter.addWidget(self.table)
        sync_splitter.addWidget(lower_splitter)
        sync_splitter.setChildrenCollapsible(False)
        sync_splitter.setSizes([380, 220])

        sync_layout.addWidget(sync_splitter, 1)

        dupe_page = QWidget()
        dupe_layout = QVBoxLayout(dupe_page)
        dupe_top_layout = QGridLayout()
        dupe_top_layout.setContentsMargins(0, 0, 0, 0)
        dupe_top_layout.setHorizontalSpacing(12)
        dupe_top_layout.setVerticalSpacing(14)
        dupe_top_layout.addWidget(QLabel("Album"), 0, 0)
        dupe_top_layout.addWidget(self.dupe_album_edit, 0, 1)
        dupe_top_layout.addWidget(self.dupe_strict_checkbox, 1, 1)
        dupe_top_layout.setColumnStretch(1, 1)
        dupe_button_row = QHBoxLayout()
        dupe_button_row.setContentsMargins(0, 0, 0, 0)
        dupe_button_row.setSpacing(10)
        dupe_button_row.addWidget(self.dupe_scan_button)
        dupe_button_row.addWidget(self.dupe_delete_button)
        dupe_button_row.addStretch(1)

        dupe_top_panel = QFrame()
        dupe_top_panel.setObjectName("FormPanel")
        dupe_top_panel.setLayout(dupe_top_layout)

        dupe_action_panel = QFrame()
        dupe_action_panel.setObjectName("ActionPanel")
        dupe_action_panel.setLayout(dupe_button_row)

        dupe_layout.setContentsMargins(0, 0, 0, 0)
        dupe_layout.setSpacing(14)
        dupe_layout.addWidget(dupe_top_panel)
        dupe_layout.addWidget(dupe_action_panel)
        dupe_layout.addWidget(self.dupe_summary_label)
        dupe_layout.addWidget(self.dupe_progress_bar)
        dupe_layout.addWidget(self.dupe_table, 1)

        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(sync_page)
        self.page_stack.addWidget(dupe_page)

        header_row = QHBoxLayout()
        header_row.setAlignment(Qt.AlignTop)
        header_row.addWidget(self.logo_label, 0, Qt.AlignTop)
        header_row.addWidget(segmented_container, 1, Qt.AlignTop)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(14)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(20, 16, 20, 20)
        root_layout.setSpacing(18)
        root_layout.addLayout(header_row)
        root_layout.addWidget(self.page_stack, 1)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)
        self.setup_footer_about_link()

        self.browse_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.start_scan)
        self.import_button.clicked.connect(self.start_import)
        self.dupe_scan_button.clicked.connect(self.start_dupe_scan)
        self.dupe_delete_button.clicked.connect(self.delete_selected_duplicates)
        self.sync_tab_button.clicked.connect(lambda: self.show_page(0))
        self.dupe_tab_button.clicked.connect(lambda: self.show_page(1))
        self.recursive_checkbox.toggled.connect(lambda _: self.persist_state())
        self.include_raw_checkbox.toggled.connect(lambda _: self.persist_state())
        self.dupe_strict_checkbox.toggled.connect(lambda _: self.persist_state())
        self.album_edit.editingFinished.connect(self.persist_state)
        self.dupe_album_edit.editingFinished.connect(self.persist_state)
        self.dupe_table.itemSelectionChanged.connect(self.update_dupe_delete_enabled)
        self.dupe_table.itemDoubleClicked.connect(self.open_duplicate_group_in_photos)
        self.refresh_history_view()
        self.setup_menu()

    def setup_footer_about_link(self) -> None:
        about_link = QPushButton(f"About {APP_NAME}")
        about_link.setFlat(True)
        about_link.setCursor(Qt.PointingHandCursor)
        about_link.clicked.connect(self.show_about_dialog)
        self.statusBar().addPermanentWidget(about_link)

    def setup_menu(self) -> None:
        menu_bar = self.menuBar()
        app_menu = menu_bar.addMenu(APP_NAME)
        about_action = QAction(f"About {APP_NAME}", self)
        about_action.setMenuRole(QAction.AboutRole)
        about_action.triggered.connect(self.show_about_dialog)
        app_menu.addAction(about_action)

    def show_about_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"About {APP_NAME}")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(APP_NAME)
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel("Copyright 2026 Paul Quilichini"))
        layout.addWidget(QLabel(f"Email: {CONTACT_EMAIL}"))
        layout.addWidget(QLabel(f"Website: {CONTACT_WEBSITE}"))

        buttons = QDialogButtonBox(dialog)
        email_button = buttons.addButton("Email", QDialogButtonBox.ActionRole)
        website_button = buttons.addButton("Website", QDialogButtonBox.ActionRole)
        close_button = buttons.addButton(QDialogButtonBox.Close)

        email_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:{CONTACT_EMAIL}")))
        website_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(CONTACT_WEBSITE)))
        close_button.clicked.connect(dialog.accept)

        layout.addWidget(buttons)
        dialog.exec()

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            self.persist_state()

    def append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"[{timestamp}] {message}")

    def show_operation_error(self, operation: str, message: str, *, show_photos_dialog: bool = False) -> None:
        clean_message = message.strip() or "Unknown error."
        self.append_log(f"ERROR [{operation}] {clean_message}")
        QMessageBox.critical(self, f"{operation} failed", clean_message)
        if show_photos_dialog and any(
            token in clean_message.lower()
            for token in ("photos access", "authorization", "privacy", "not allowed", "accessibility")
        ):
            self.show_photos_access_dialog(clean_message)

    def show_page(self, index: int) -> None:
        self.page_stack.setCurrentIndex(index)
        self.sync_tab_button.setChecked(index == 0)
        self.dupe_tab_button.setChecked(index == 1)

    def persist_state(self) -> None:
        self.app_data["last_folder"] = self.folder_edit.text()
        self.app_data["scan_subfolders"] = self.recursive_checkbox.isChecked()
        self.app_data["include_raw"] = self.include_raw_checkbox.isChecked()
        self.app_data["album_name"] = self.album_edit.text().strip()
        self.app_data["dupe_album_name"] = self.dupe_album_edit.text().strip()
        self.app_data["dupe_strict_mode"] = self.dupe_strict_checkbox.isChecked()
        save_persisted_app_data(APP_DATA_PATH, self.app_data)

    def refresh_history_view(self) -> None:
        history = self.app_data.get("history", [])
        if not history:
            self.history_view.setPlainText("No imports recorded yet.")
            return
        self.history_view.setPlainText("\n\n".join(format_history_entry(entry) for entry in reversed(history[-12:])))

    def record_import_history(self, imported: int, errors: list[str]) -> None:
        history = self.app_data.setdefault("history", [])
        history.append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "folder": self.folder_edit.text(),
                "include_raw": self.include_raw_checkbox.isChecked(),
                "album_name": self.album_edit.text().strip(),
                "imported": imported,
                "files": [path.name for path in self.last_import_paths],
                "errors": errors,
            }
        )
        self.app_data["history"] = history[-50:]
        self.persist_state()
        self.refresh_history_view()

    def set_busy(self, busy: bool) -> None:
        self.scan_button.setEnabled(not busy)
        self.import_button.setEnabled(
            (not busy) and any(not candidate.already_in_photos for candidate in self.candidates)
        )
        self.browse_button.setEnabled(not busy)
        self.recursive_checkbox.setEnabled(not busy)
        self.include_raw_checkbox.setEnabled(not busy)
        self.album_edit.setEnabled(not busy)
        self.dupe_scan_button.setEnabled(not busy)
        self.dupe_delete_button.setEnabled(
            (not busy) and bool(self.dupe_table.selectionModel() and self.dupe_table.selectionModel().selectedRows())
        )
        self.dupe_album_edit.setEnabled(not busy)
        self.dupe_strict_checkbox.setEnabled(not busy)
        self.sync_tab_button.setEnabled(not busy)
        self.dupe_tab_button.setEnabled(not busy)

    def update_dupe_delete_enabled(self) -> None:
        busy = any(thread is not None for thread in (self.scan_thread, self.import_thread, self.dupe_thread))
        self.dupe_delete_button.setEnabled(
            (not busy) and bool(self.dupe_table.selectionModel() and self.dupe_table.selectionModel().selectedRows())
        )

    def show_photos_access_dialog(self, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Photos Access Required")
        dialog.setText(message)
        dialog.setInformativeText("Use System Settings to allow Photos access, then run the scan again.")
        open_button = dialog.addButton("Open Settings", QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()
        if dialog.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl(PHOTOS_SETTINGS_URL))

    def show_accessibility_dialog(self, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("Accessibility Access Required")
        dialog.setText(message)
        dialog.setInformativeText(
            "Add or enable Terminal.app or iTerm.app first. If that still does not work, add the Python executable used to launch `python3 app.py`, then try again."
        )
        open_button = dialog.addButton("Open Settings", QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Close)
        dialog.exec()
        if dialog.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl(ACCESSIBILITY_SETTINGS_URL))

    def update_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)
        self.summary_label.setText(message)

    def update_dupe_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.dupe_progress_bar.setRange(0, total)
            self.dupe_progress_bar.setValue(current)
        else:
            self.dupe_progress_bar.setRange(0, 0)
        self.dupe_summary_label.setText(message)

    def start_scan(self) -> None:
        folder = Path(self.folder_edit.text()).expanduser()
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Invalid folder", "Choose an existing folder to scan.")
            return
        self.persist_state()

        self.append_log(f"Starting scan in {folder}")
        self.summary_label.setText("Preparing scan...")
        self.progress_bar.setRange(0, 0)
        self.table.setRowCount(0)
        self.candidates = []
        self.set_busy(True)

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(
            str(folder), self.recursive_checkbox.isChecked(), self.photos_bridge, EXIFTOOL_PATH
        )
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.update_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()

    def start_dupe_scan(self) -> None:
        self.persist_state()
        self.dupe_table.setRowCount(0)
        self.duplicate_groups = []
        scope_suffix = (
            f" in album '{self.dupe_album_edit.text().strip()}'" if self.dupe_album_edit.text().strip() else ""
        )
        mode_suffix = " using exact mode" if self.dupe_strict_checkbox.isChecked() else ""
        self.dupe_summary_label.setText(f"Preparing duplicate scan{scope_suffix}{mode_suffix}...")
        self.dupe_progress_bar.setRange(0, 0)
        self.set_busy(True)

        self.dupe_thread = QThread(self)
        self.dupe_worker = DuplicateScanWorker(
            self.dupe_album_edit.text().strip(),
            self.dupe_strict_checkbox.isChecked(),
            self.photos_bridge,
        )
        self.dupe_worker.moveToThread(self.dupe_thread)
        self.dupe_thread.started.connect(self.dupe_worker.run)
        self.dupe_worker.progress.connect(self.update_dupe_progress)
        self.dupe_worker.finished.connect(self.dupe_scan_finished)
        self.dupe_worker.finished.connect(self.dupe_worker.deleteLater)
        self.dupe_thread.finished.connect(self.dupe_thread.deleteLater)
        self.dupe_thread.start()

    def scan_finished(self, candidates: list[Candidate], error_message: str) -> None:
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.scan_thread = None
        self.scan_worker = None

        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        if error_message:
            self.summary_label.setText("Scan failed. See error details.")
            self.show_operation_error("Scan", error_message, show_photos_dialog=True)
            self.set_busy(False)
            return

        self.candidates = candidates
        importable = sum(1 for candidate in candidates if not candidate.already_in_photos)
        duplicates = len(candidates) - importable
        self.summary_label.setText(
            f"Found {len(candidates)} flagged photo(s): {importable} importable, {duplicates} already in Photos."
        )
        self.append_log(self.summary_label.text())
        self.populate_table()
        self.set_busy(False)

    def dupe_scan_finished(self, duplicates: list[DuplicateGroup], error_message: str) -> None:
        if self.dupe_thread:
            self.dupe_thread.quit()
            self.dupe_thread.wait()
            self.dupe_thread = None
        self.dupe_worker = None

        self.dupe_progress_bar.setRange(0, 1)
        self.dupe_progress_bar.setValue(0)

        if error_message:
            self.dupe_summary_label.setText("Duplicate scan failed. See error details.")
            self.show_operation_error("Duplicate scan", error_message, show_photos_dialog=True)
            self.set_busy(False)
            return

        self.duplicate_groups = duplicates
        scope_suffix = (
            f" in album '{self.dupe_album_edit.text().strip()}'"
            if self.dupe_album_edit.text().strip()
            else " in Photos"
        )
        mode_suffix = " with exact mode" if self.dupe_strict_checkbox.isChecked() else ""
        self.dupe_summary_label.setText(
            f"Found {len(duplicates)} possible duplicate group(s){scope_suffix}{mode_suffix}."
        )
        self.populate_dupe_table()
        self.set_busy(False)

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.candidates))
        for row, candidate in enumerate(self.candidates):
            status = "Already in Photos" if candidate.already_in_photos else "Ready to import"
            if candidate.duplicate_reason:
                reason = candidate.duplicate_reason
            elif candidate.sidecar_path is not None:
                reason = "Flagged in sidecar"
            else:
                reason = "Flagged in embedded metadata"
            if candidate.raw_companion_path is not None:
                reason = f"{reason}; RAW companion: {candidate.raw_companion_path.name}"
            values = [
                str(candidate.path),
                str(candidate.sidecar_path or ""),
                status,
                reason,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if candidate.already_in_photos:
                    item.setForeground(Qt.darkYellow)
                self.table.setItem(row, column, item)

    def populate_dupe_table(self) -> None:
        self.dupe_table.setRowCount(len(self.duplicate_groups))
        for row, group in enumerate(self.duplicate_groups):
            values = [str(group.count), group.filenames, group.created, group.identifiers_text]
            for column, value in enumerate(values):
                self.dupe_table.setItem(row, column, QTableWidgetItem(value))
        self.update_dupe_delete_enabled()

    def open_duplicate_group_in_photos(self, item) -> None:
        row = item.row()
        if row < 0 or row >= len(self.duplicate_groups):
            return
        group = self.duplicate_groups[row]
        first_filename = group.filenames.split(", ", 1)[0]
        ok, message = search_photos_for_filename(first_filename)
        if ok:
            self.append_log(f"Searched Photos for duplicate filename: {first_filename}")
            return
        self.append_log(message)
        if "Accessibility" in message:
            self.show_accessibility_dialog(message)
            return
        QMessageBox.warning(self, "Open in Photos failed", message)

    def delete_selected_duplicates(self) -> None:
        selected_rows = sorted({index.row() for index in self.dupe_table.selectionModel().selectedRows()})
        if not selected_rows:
            return

        identifiers_to_delete: list[str] = []
        groups_count = 0
        for row in selected_rows:
            group = self.duplicate_groups[row]
            if len(group.identifiers) <= 1:
                continue
            identifiers_to_delete.extend(group.identifiers[1:])
            groups_count += 1

        if not identifiers_to_delete:
            QMessageBox.information(
                self, "Nothing to delete", "The selected groups do not contain deletable duplicates."
            )
            return

        answer = QMessageBox.question(
            self,
            "Delete duplicates",
            f"Delete {len(identifiers_to_delete)} duplicate asset(s) from {groups_count} selected group(s)?\nThe first item in each group will be kept.",
        )
        if answer != QMessageBox.Yes:
            return

        self.set_busy(True)
        deleted, errors = self.photos_bridge.delete_assets_by_identifiers(identifiers_to_delete)
        self.set_busy(False)
        if errors:
            self.show_operation_error("Delete duplicates", "\n".join(errors))
            return

        self.append_log(f"Deleted {deleted} duplicate Photos asset(s).")
        QMessageBox.information(self, "Delete complete", f"Deleted {deleted} duplicate asset(s).")
        self.start_dupe_scan()

    def start_import(self) -> None:
        importable = [candidate for candidate in self.candidates if not candidate.already_in_photos]
        if not importable:
            QMessageBox.information(self, "Nothing to import", "No flagged photos are waiting to be imported.")
            return

        import_paths: list[Path] = []
        seen_paths: set[Path] = set()
        for candidate in importable:
            for path in candidate.import_paths(self.include_raw_checkbox.isChecked()):
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                import_paths.append(path)
        self.last_import_paths = import_paths
        self.persist_state()

        album_suffix = f" into album '{self.album_edit.text().strip()}'" if self.album_edit.text().strip() else ""
        self.append_log(f"Importing {len(import_paths)} file(s) into Photos{album_suffix}")
        self.summary_label.setText(f"Importing {len(import_paths)} file(s){album_suffix}...")
        self.progress_bar.setRange(0, len(import_paths))
        self.progress_bar.setValue(0)
        self.set_busy(True)

        self.import_thread = QThread(self)
        self.import_worker = ImportWorker(
            self.candidates,
            self.include_raw_checkbox.isChecked(),
            self.album_edit.text().strip(),
            self.photos_bridge,
        )
        self.import_worker.moveToThread(self.import_thread)
        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.progress.connect(self.update_progress)
        self.import_worker.finished.connect(self.import_finished)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)
        self.import_thread.start()

    def import_finished(self, imported: int, errors: list[str], error_message: str) -> None:
        if self.import_thread:
            self.import_thread.quit()
            self.import_thread.wait()
            self.import_thread = None
        self.import_worker = None

        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        if error_message:
            self.summary_label.setText("Import failed. See error details.")
            self.show_operation_error("Import", error_message, show_photos_dialog=True)
            self.set_busy(False)
            return

        album_suffix = (
            f" and added to album '{self.album_edit.text().strip()}'" if self.album_edit.text().strip() else ""
        )
        self.summary_label.setText(f"Imported {imported} photo(s) into Photos{album_suffix}.")
        self.append_log(self.summary_label.text())
        for error in errors:
            self.append_log(f"ERROR [Import item] {error}")
        self.record_import_history(imported, errors)

        QMessageBox.information(self, "Import complete", self.summary_label.text())
        self.start_scan()

    def closeEvent(self, event) -> None:
        self.persist_state()
        super().closeEvent(event)
