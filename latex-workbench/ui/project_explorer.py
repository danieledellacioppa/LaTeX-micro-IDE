"""Project explorer tree for navigating project files."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QLabel

HIDDEN_SUFFIXES = {".aux", ".log", ".fls", ".fdb_latexmk", ".xdv", ".toc", ".out"}


class ProjectExplorer(QWidget):
    tex_file_requested = Signal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._root: Path | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Project Explorer"))
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.tree)

    def set_root(self, root: Path) -> None:
        self._root = root
        self.tree.clear()
        root_item = QTreeWidgetItem([root.name or str(root)])
        root_item.setData(0, Qt.UserRole, str(root))
        self.tree.addTopLevelItem(root_item)
        self._populate(root_item, root)
        root_item.setExpanded(True)

    def _populate(self, parent_item: QTreeWidgetItem, directory: Path) -> None:
        for path in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if self._is_hidden(path):
                continue
            item = QTreeWidgetItem([path.name])
            item.setData(0, Qt.UserRole, str(path))
            parent_item.addChild(item)
            if path.is_dir():
                self._populate(item, path)

    def _is_hidden(self, path: Path) -> bool:
        if path.name.startswith("."):
            return True
        if path.is_file() and path.suffix in HIDDEN_SUFFIXES:
            return True
        if path.is_file() and ".mtc" in path.suffixes:
            return True
        return False

    def _on_item_activated(self, item: QTreeWidgetItem) -> None:
        raw_path = item.data(0, Qt.UserRole)
        if not raw_path:
            return
        path = Path(raw_path)
        if path.is_file() and path.suffix == ".tex":
            self.tex_file_requested.emit(path)
