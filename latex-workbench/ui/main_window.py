"""Main window for latex-workbench MVP."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QDesktopServices

from services.build_service import BuildService
from services.file_service import FileService
from services.git_service import GitService
from services.shell_service import ShellService
from ui.editor_panel import EditorPanel
from ui.git_panel import GitPanel
from ui.log_panel import LogPanel
from ui.terminal_panel import TerminalPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("latex-workbench")
        self.resize(1200, 800)

        self.current_file: Path | None = None
        self._active_build_file: Path | None = None

        self.editor = EditorPanel()
        self.log_panel = LogPanel()
        self.build_service = BuildService(self)
        self.shell_service = ShellService(self)
        self.git_service = GitService(self)

        self._setup_ui()
        self._setup_toolbar()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self.terminal_panel = TerminalPanel()
        self.git_panel = GitPanel()

        bottom_tabs = QTabWidget()
        bottom_tabs.addTab(self.log_panel, "Build Log")
        bottom_tabs.addTab(self.terminal_panel, "Shell")
        bottom_tabs.addTab(self.git_panel, "Git")

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(bottom_tabs)
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

        self.terminal_panel.command_submitted.connect(self.shell_service.run_command)
        self.shell_service.output_received.connect(self.terminal_panel.append_text)

        self.git_panel.pull_requested.connect(self.git_service.run_pull)
        self.git_panel.status_requested.connect(self.git_service.run_status)
        self.git_panel.push_requested.connect(self.git_service.run_push)
        self.git_panel.refresh_branches_requested.connect(self.git_service.refresh_branches)
        self.git_panel.checkout_requested.connect(self.git_service.checkout_branch)
        self.git_service.output_received.connect(self.git_panel.append_text)
        self.git_service.output_received.connect(self.log_panel.append_text)
        self.git_service.branches_received.connect(self.git_panel.set_branches)

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
        self._set_project_directory(path.parent)
        self.statusBar().showMessage(f"Opened {path}", 5000)


    def _set_project_directory(self, project_dir: Path) -> None:
        self.shell_service.set_project_dir(project_dir)
        self.git_service.set_project_dir(project_dir)
        self.git_service.refresh_branches()

    def save_file(self) -> bool:
        if self.current_file is None:
            QMessageBox.warning(self, "No file selected", "Open a .tex file before saving.")
            return False

        try:
            FileService.write_text(self.current_file, self.editor.toPlainText())
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save file:\n{exc}")
            return False

        self.statusBar().showMessage(f"Saved {self.current_file}", 5000)
        return True

    def build_file(self) -> None:
        if self.current_file is None:
            QMessageBox.warning(self, "No file selected", "Open a .tex file before building.")
            return

        if not self.save_file():
            return

        if self.build_service.is_running():
            self.build_service.build(self.current_file)
            return

        self._active_build_file = self.current_file
        self.build_service.build(self.current_file)

    def _on_build_finished(self, success: bool, message: str) -> None:
        self.log_panel.append_text(f"\n=== {message} ===\n")
        build_file = self._active_build_file
        self._active_build_file = None

        if not success or build_file is None:
            return

        pdf_path = build_file.with_suffix(".pdf")
        if not pdf_path.exists():
            self.log_panel.append_text(f"Expected PDF not found: {pdf_path}\n")
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
        if opened:
            self.log_panel.append_text(f"Opened PDF: {pdf_path}\n")
        else:
            self.log_panel.append_text(f"Could not open PDF: {pdf_path}\n")
