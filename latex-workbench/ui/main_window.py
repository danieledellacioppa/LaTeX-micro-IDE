"""Main window for latex-workbench MVP."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QDesktopServices

from services.build_service import BuildService
from services.file_service import FileService
from ui.editor_panel import EditorPanel
from ui.log_panel import LogPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("latex-workbench")
        self.resize(1200, 800)

        self.current_file: Path | None = None

        self.editor = EditorPanel()
        self.log_panel = LogPanel()
        self.build_service = BuildService(self)

        self._setup_ui()
        self._setup_toolbar()
        self._connect_signals()

    def _setup_ui(self) -> None:
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([550, 250])

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

    def _setup_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")

        self.open_action = QAction("Open .tex", self)
        self.save_action = QAction("Save", self)
        self.build_action = QAction("Build", self)

        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.build_action)

    def _connect_signals(self) -> None:
        self.open_action.triggered.connect(self.open_file)
        self.save_action.triggered.connect(self.save_file)
        self.build_action.triggered.connect(self.build_file)

        self.build_service.output_received.connect(self.log_panel.append_text)
        self.build_service.build_finished.connect(self._on_build_finished)

    def open_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open LaTeX file",
            "",
            "TeX files (*.tex);;All files (*)",
        )
        if not file_name:
            return

        path = Path(file_name)
        try:
            content = FileService.read_text(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", f"Could not read file:\n{exc}")
            return

        self.current_file = path
        self.editor.setPlainText(content)
        self.statusBar().showMessage(f"Opened {path}", 5000)

    def save_file(self) -> None:
        if self.current_file is None:
            QMessageBox.warning(self, "No file selected", "Open a .tex file before saving.")
            return

        try:
            FileService.write_text(self.current_file, self.editor.toPlainText())
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save file:\n{exc}")
            return

        self.statusBar().showMessage(f"Saved {self.current_file}", 5000)

    def build_file(self) -> None:
        if self.current_file is None:
            QMessageBox.warning(self, "No file selected", "Open a .tex file before building.")
            return

        self.save_file()
        self.build_service.build(self.current_file)

    def _on_build_finished(self, success: bool, message: str) -> None:
        self.log_panel.append_text(f"\n=== {message} ===\n")
        if not success or self.current_file is None:
            return

        pdf_path = self.current_file.with_suffix(".pdf")
        if not pdf_path.exists():
            self.log_panel.append_text(f"Expected PDF not found: {pdf_path}\n")
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
        if opened:
            self.log_panel.append_text(f"Opened PDF: {pdf_path}\n")
        else:
            self.log_panel.append_text(f"Could not open PDF: {pdf_path}\n")
