"""Git controls panel with branch actions and Auto Push workflow."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)


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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.pull_button = QPushButton("Pull", self)
        self.status_button = QPushButton("Status", self)
        self.refresh_button = QPushButton("Refresh", self)
        self.auto_push_button = QPushButton("Auto Push", self)

        self.branch_combo = QComboBox(self)
        self.branch_combo.setMinimumWidth(320)
        self.checkout_button = QPushButton("Checkout", self)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Git command output...")

        top = QHBoxLayout()
        top.addWidget(self.pull_button)
        top.addWidget(self.status_button)
        top.addWidget(self.refresh_button)
        top.addStretch(1)
        top.addWidget(QLabel("Branch:"))
        top.addWidget(self.branch_combo)
        top.addWidget(self.checkout_button)
        top.addWidget(self.auto_push_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.output)

        self.pull_button.clicked.connect(self.pull_requested.emit)
        self.status_button.clicked.connect(self.status_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_branches_requested.emit)
        self.checkout_button.clicked.connect(self._emit_checkout)

    def set_branches(self, branches: list[dict]) -> None:
        self.branch_combo.clear()
        for branch in branches:
            name = branch["name"]
            date = branch["date"]
            self.branch_combo.addItem(f"{name} — {date}", userData=name)

    def _emit_checkout(self) -> None:
        branch = self.branch_combo.currentData()
        if isinstance(branch, str) and branch.strip():
            self.checkout_requested.emit(branch.strip())

    def ask_autopush_confirmation(self, changed_files: list[str]) -> str | None:
        dialog = AutoPushDialog(changed_files, self)
        if dialog.exec() == QDialog.Accepted:
            return dialog.commit_message()
        return None

    def append_text(self, text: str) -> None:
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
