"""Git controls panel with branch actions, ignore management, and Auto Push workflow."""

from fnmatch import fnmatch
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class AutoPushDialog(QDialog):
    ...


class IgnorePatternDialog(QDialog):
    def __init__(self, repo_root: Path, tracked_files: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ignore Pattern")
        self.resize(700, 460)
        self._repo_root = repo_root
        self._tracked_files = tracked_files

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Pattern (examples: *.pyc, __pycache__/, *.aux):"))
        self.pattern_input = QLineEdit(self)
        layout.addWidget(self.pattern_input)

        self.remove_checkbox = QCheckBox("Also remove already tracked matching files from Git index", self)
        self.remove_checkbox.setChecked(True)
        layout.addWidget(self.remove_checkbox)

        layout.addWidget(QLabel("Preview of tracked files that would be removed (files remain on disk):"))
        self.preview = QListWidget(self)
        layout.addWidget(self.preview)

        self.pattern_input.textChanged.connect(self._refresh_preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_preview(self) -> None:
        pattern = self.pattern_input.text().strip()
        self.preview.clear()
        if not pattern:
            return
        matches = [f for f in self._tracked_files if _pattern_matches(pattern, f)]
        self.preview.addItems(matches)

    def _validate_and_accept(self) -> None:
        if not self.pattern().strip():
            QMessageBox.warning(self, "Missing pattern", "Please enter an ignore pattern.")
            return
        self.accept()

    def pattern(self) -> str:
        return self.pattern_input.text().strip()

    def remove_from_index(self) -> bool:
        return self.remove_checkbox.isChecked()


class AutoPushDialog(QDialog):
    def __init__(self, changed_files: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Auto Push Confirmation")
        self.resize(700, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Files to be committed and pushed:"))

        self.files_list = QListWidget(self)
        self.files_list.addItems(changed_files)
        layout.addWidget(self.files_list)

        layout.addWidget(QLabel("Commit message:"))
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Describe this change")
        layout.addWidget(self.message_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.message_input.text().strip():
            QMessageBox.warning(self, "Missing commit message", "Please enter a commit message.")
            return
        self.accept()

    def commit_message(self) -> str:
        return self.message_input.text().strip()


class GitPanel(QWidget):
    pull_requested = Signal()
    status_requested = Signal()
    refresh_branches_requested = Signal()
    checkout_requested = Signal(str)
    autopush_requested = Signal(str)
    delete_local_requested = Signal(str, bool)
    delete_remote_requested = Signal(str)
    ignore_pattern_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._branches: list[dict] = []

        self.current_branch_label = QLabel("Current Branch: unknown", self)
        self.pull_button = QPushButton("Pull", self)
        self.status_button = QPushButton("Status", self)
        self.refresh_button = QPushButton("Refresh", self)
        self.auto_push_button = QPushButton("Auto Push", self)
        self.ignore_button = QPushButton("Ignore Pattern", self)

        self.checkout_button = QPushButton("Checkout", self)
        self.delete_local_button = QPushButton("Delete Local Branch", self)
        self.delete_remote_button = QPushButton("Delete Remote Branch", self)

        self.branch_table = QTableWidget(0, 3, self)
        self.branch_table.setHorizontalHeaderLabels(["Branch", "Type", "Last Commit Date"])
        self.branch_table.horizontalHeader().setStretchLastSection(True)
        self.branch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.branch_table.setSelectionMode(QTableWidget.SingleSelection)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)

        top = QHBoxLayout()
        top.addWidget(self.pull_button)
        top.addWidget(self.status_button)
        top.addWidget(self.refresh_button)
        top.addWidget(self.auto_push_button)
        top.addWidget(self.ignore_button)

        actions = QHBoxLayout()
        actions.addWidget(self.checkout_button)
        actions.addWidget(self.delete_local_button)
        actions.addWidget(self.delete_remote_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.current_branch_label)
        layout.addLayout(top)
        layout.addWidget(self.branch_table)
        layout.addLayout(actions)
        layout.addWidget(self.output)

        self.pull_button.clicked.connect(self.pull_requested.emit)
        self.status_button.clicked.connect(self.status_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_branches_requested.emit)
        self.ignore_button.clicked.connect(self.ignore_pattern_requested.emit)
        self.checkout_button.clicked.connect(self._emit_checkout)
        self.delete_local_button.clicked.connect(self._emit_delete_local)
        self.delete_remote_button.clicked.connect(self._emit_delete_remote)

    def set_branches(self, branches: list[dict]) -> None:
        self._branches = branches
        self.branch_table.setRowCount(len(branches))
        for idx, branch in enumerate(branches):
            self.branch_table.setItem(idx, 0, QTableWidgetItem(branch["name"]))
            self.branch_table.setItem(idx, 1, QTableWidgetItem(branch.get("type", "local")))
            self.branch_table.setItem(idx, 2, QTableWidgetItem(branch["date"]))

    def set_current_branch(self, branch: str) -> None:
        self.current_branch_label.setText(f"Current Branch: {branch}")

    def selected_branch(self) -> dict | None:
        row = self.branch_table.currentRow()
        if row < 0 or row >= len(self._branches):
            return None
        return self._branches[row]

    def _emit_checkout(self) -> None:
        branch = self.selected_branch()
        if branch:
            self.checkout_requested.emit(branch["name"])

    def _emit_delete_local(self) -> None:
        branch = self.selected_branch()
        if not branch or branch.get("type") != "local":
            QMessageBox.warning(self, "Delete local branch", "Select a local branch first.")
            return
        self.delete_local_requested.emit(branch["name"], False)

    def _emit_delete_remote(self) -> None:
        branch = self.selected_branch()
        if not branch or branch.get("type") != "remote":
            QMessageBox.warning(self, "Delete remote branch", "Select a remote branch first.")
            return
        self.delete_remote_requested.emit(branch["name"])

    def ask_ignore_pattern(self, repo_root: Path, tracked_files: list[str]) -> tuple[str, bool] | None:
        dialog = IgnorePatternDialog(repo_root, tracked_files, self)
        if dialog.exec() == QDialog.Accepted:
            return dialog.pattern(), dialog.remove_from_index()
        return None

    def ask_autopush_confirmation(self, changed_files: list[str]) -> str | None:
        dialog = AutoPushDialog(changed_files, self)
        if dialog.exec() == QDialog.Accepted:
            return dialog.commit_message()
        return None

    def append_text(self, text: str) -> None:
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)


def _pattern_matches(pattern: str, file_path: str) -> bool:
    p = pattern.strip()
    if p.endswith("/"):
        d = p.rstrip("/")
        return file_path == d or file_path.startswith(f"{d}/") or f"/{d}/" in file_path
    return fnmatch(file_path, p) or fnmatch(Path(file_path).name, p)
