"""Editor panel based on QPlainTextEdit."""

from PySide6.QtWidgets import QPlainTextEdit


class EditorPanel(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Open a .tex file to start editing...")
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
