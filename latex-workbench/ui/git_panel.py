"""Git controls panel for pull/status/push and branch checkout."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class GitPanel(QWidget):
    pull_requested = Signal()
    status_requested = Signal()
    push_requested = Signal()
    refresh_branches_requested = Signal()
    checkout_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.pull_button = QPushButton("Git Pull", self)
        self.status_button = QPushButton("Git Status", self)
        self.push_button = QPushButton("Git Push", self)
        self.refresh_button = QPushButton("Refresh Branches", self)

        self.branch_combo = QComboBox(self)
        self.branch_combo.setMinimumWidth(260)
        self.checkout_button = QPushButton("Checkout", self)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Git command output...")

        top = QHBoxLayout()
        top.addWidget(self.pull_button)
        top.addWidget(self.status_button)
        top.addWidget(self.push_button)
        top.addWidget(self.refresh_button)

        branch_row = QHBoxLayout()
        branch_row.addWidget(QLabel("Branch:"))
        branch_row.addWidget(self.branch_combo)
        branch_row.addWidget(self.checkout_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(branch_row)
        layout.addWidget(self.output)

        self.pull_button.clicked.connect(self.pull_requested.emit)
        self.status_button.clicked.connect(self.status_requested.emit)
        self.push_button.clicked.connect(self.push_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_branches_requested.emit)
        self.checkout_button.clicked.connect(self._emit_checkout)

    def set_branches(self, branches: list[str]) -> None:
        self.branch_combo.clear()
        self.branch_combo.addItems(branches)

    def _emit_checkout(self) -> None:
        branch = self.branch_combo.currentText().strip()
        if branch:
            self.checkout_requested.emit(branch)

    def append_text(self, text: str) -> None:
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
