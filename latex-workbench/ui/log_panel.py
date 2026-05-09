"""Simple read-only build log panel."""

from PySide6.QtWidgets import QPlainTextEdit


class LogPanel(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Build output will appear here...")

    def append_text(self, text: str) -> None:
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(self.textCursor().MoveOperation.End)
