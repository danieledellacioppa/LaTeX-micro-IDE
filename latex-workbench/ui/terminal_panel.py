"""Simple command console panel (non-PTY)."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


class TerminalPanel(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Simple shell console (non-PTY). No TAB autocomplete, arrow history, or fullscreen terminal apps."
        )

        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Enter shell command and press Enter...")
        self.run_button = QPushButton("Run", self)

        controls = QHBoxLayout()
        controls.addWidget(self.command_input)
        controls.addWidget(self.run_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.output)
        layout.addLayout(controls)

        self.command_input.returnPressed.connect(self._emit_command)
        self.run_button.clicked.connect(self._emit_command)

    def _emit_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        self.command_submitted.emit(command)
        self.command_input.clear()

    def append_text(self, text: str) -> None:
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
