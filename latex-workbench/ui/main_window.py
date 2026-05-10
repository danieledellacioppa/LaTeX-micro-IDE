"""Main window for latex-workbench MVP."""

from pathlib import Path
from fnmatch import fnmatch

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter, QTabWidget, QWidget, QVBoxLayout

from services.build_service import BuildService
from services.file_service import FileService
from services.git_service import GitService
from services.shell_service import ShellService
from ui.editor_panel import EditorPanel
from ui.git_panel import GitPanel
from ui.log_panel import LogPanel
from ui.project_explorer import ProjectExplorer
from ui.terminal_panel import TerminalPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("latex-workbench")
        self.resize(1280, 840)

        self.current_file: Path | None = None
        self.current_project_dir: Path | None = None
        self._active_build_file: Path | None = None
        self._last_build_status = "idle"
        self._pending_local_delete_branch: str | None = None
        self._pending_remote_prune = False

        self.editor = EditorPanel()
        self.log_panel = LogPanel()
        self.build_service = BuildService(self)
        self.shell_service = ShellService(self)
        self.git_service = GitService(self)

        self._setup_ui()
        self._setup_toolbar()
        self._setup_git_toolbar()
        self._connect_signals()
        self._update_status_bar("unknown", False)

    def _setup_ui(self) -> None:
        self.terminal_panel = TerminalPanel()
        self.git_panel = GitPanel()
        self.project_explorer = ProjectExplorer()

        bottom_tabs = QTabWidget()
        bottom_tabs.addTab(self.log_panel, "Build Log")
        bottom_tabs.addTab(self.terminal_panel, "Shell")
        bottom_tabs.addTab(self.git_panel, "Git")

        vertical_split = QSplitter(Qt.Orientation.Vertical)
        vertical_split.addWidget(self.editor)
        vertical_split.addWidget(bottom_tabs)
        vertical_split.setSizes([560, 250])

        horizontal_split = QSplitter(Qt.Orientation.Horizontal)
        horizontal_split.addWidget(self.project_explorer)
        horizontal_split.addWidget(vertical_split)
        horizontal_split.setSizes([300, 960])

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(horizontal_split)
        self.setCentralWidget(container)

    def _setup_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        self.open_action = QAction("Open TeX", self)
        self.save_action = QAction("Save", self)
        self.build_action = QAction("Build", self)

        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.build_action)

    def _setup_git_toolbar(self) -> None:
        git_toolbar = self.addToolBar("Git")
        git_toolbar.addAction(QAction("Pull", self, triggered=self.git_service.run_pull))
        git_toolbar.addAction(QAction("Status", self, triggered=self.git_service.run_status))
        git_toolbar.addAction(QAction("Refresh Branches", self, triggered=self.git_service.refresh_branches))

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
        self.git_panel.refresh_branches_requested.connect(self.git_service.refresh_branches)
        self.git_panel.checkout_requested.connect(self.git_service.checkout_branch)
        self.git_panel.delete_local_requested.connect(self._delete_local_branch)
        self.git_panel.delete_remote_requested.connect(self._delete_remote_branch)
        self.git_panel.ignore_pattern_requested.connect(self._handle_ignore_pattern)
        self.git_panel.auto_push_button.clicked.connect(self._handle_auto_push)

        self.git_service.output_received.connect(self.git_panel.append_text)
        self.git_service.output_received.connect(self.log_panel.append_text)
        self.git_service.branches_received.connect(self.git_panel.set_branches)
        self.git_service.repo_status_received.connect(self._on_repo_status)
        self.git_service.action_finished.connect(self._on_git_action_finished)

        self.project_explorer.tex_file_requested.connect(self.open_file_path)

    def open_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open LaTeX file", "", "TeX files (*.tex);;All files (*)")
        if file_name:
            self.open_file_path(Path(file_name))

    def open_file_path(self, path: Path) -> None:
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
        self.current_project_dir = project_dir
        self.shell_service.set_project_dir(project_dir)
        self.git_service.set_project_dir(project_dir)
        self.project_explorer.set_root(project_dir)
        self.git_service.refresh_branches()
        self.git_service.refresh_repo_status()

    def _handle_auto_push(self) -> None:
        if self.current_project_dir is None:
            QMessageBox.information(self, "Open project", "Open a .tex file first.")
            return
        changes = self.git_service._parse_repo_status(self._capture_git_status_short())
        status_lines = [line for line in self._capture_git_status_short().splitlines() if line and not line.startswith("##")]
        if not status_lines:
            QMessageBox.information(self, "Auto Push", "No changes detected. Nothing to push.")
            return
        message = self.git_panel.ask_autopush_confirmation(status_lines)
        if message:
            self.git_service.run_autopush(message)

    def _capture_git_status_short(self) -> str:
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=str(self.current_project_dir),
                check=False,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except Exception as exc:
            self.log_panel.append_text(f"[git] Could not inspect status: {exc}\n")
            return ""

    def _on_repo_status(self, status: dict) -> None:
        branch = status.get("branch", "unknown")
        self.git_panel.set_current_branch(branch)
        self._update_status_bar(branch, bool(status.get("dirty", False)))

    def _on_git_action_finished(self, _action: str, _exit_code: int) -> None:
        if _action == "delete_local" and _exit_code != 0:
            failed_branch = self._pending_local_delete_branch
            force = QMessageBox.question(
                self,
                "Force delete branch?",
                "Git refused safe delete (branch may be unmerged). Force delete with possible local commit loss?",
            )
            if force == QMessageBox.Yes and failed_branch:
                self.git_service.delete_local_branch(failed_branch, force=True)
            self._pending_local_delete_branch = None
        if _action == "delete_local" and _exit_code == 0:
            self._pending_local_delete_branch = None
        if _action == "delete_remote" and _exit_code == 0:
            self._pending_remote_prune = True
            self.git_service.fetch_prune()
        elif _action == "fetch_prune" and _exit_code == 0:
            self._pending_remote_prune = False
        if self.current_project_dir is not None:
            self.project_explorer.set_root(self.current_project_dir)

    def _delete_local_branch(self, branch: str, _force: bool) -> None:
        current = self.git_panel.current_branch_label.text().replace("Current Branch:", "").strip()
        if branch == current:
            QMessageBox.warning(self, "Delete local branch", "Cannot delete the currently checked out branch.")
            return
        if QMessageBox.question(self, "Delete local branch", f"Delete local branch '{branch}' using safe mode?") != QMessageBox.Yes:
            return
        self._pending_local_delete_branch = branch
        self.git_service.delete_local_branch(branch, force=False)

    def _delete_remote_branch(self, branch: str) -> None:
        protected = {"origin/main", "origin/master", "origin/develop"}
        if branch in protected:
            QMessageBox.warning(self, "Protected branch", f"Cannot delete protected branch '{branch}'.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete remote branch",
            f"You are about to delete remote branch '{branch}' from origin. Continue?",
        )
        if confirm != QMessageBox.Yes:
            return
        self.git_service.delete_remote_branch(branch)

    def _handle_ignore_pattern(self) -> None:
        if self.current_project_dir is None:
            QMessageBox.information(self, "Open project", "Open a .tex file first.")
            return
        repo_root = self._git_root()
        if repo_root is None:
            QMessageBox.warning(self, "Git", "Not inside a git repository.")
            return
        tracked = self._tracked_files(repo_root)
        result = self.git_panel.ask_ignore_pattern(repo_root, tracked)
        if result is None:
            return
        pattern, remove_cached = result
        matches = [f for f in tracked if self._pattern_matches(pattern, f)]
        if remove_cached and matches:
            confirm = QMessageBox.question(
                self,
                "Remove tracked files from index",
                f"Remove {len(matches)} tracked file(s) from Git index only? Files stay on disk.",
            )
            if confirm == QMessageBox.Yes:
                import subprocess
                subprocess.run(["git", "rm", "--cached", "--", *matches], cwd=repo_root, check=False)
        self._update_gitignore(repo_root, pattern)
        self.git_service.refresh_repo_status()
        self.git_service.refresh_branches()

    def _update_status_bar(self, branch: str, dirty: bool) -> None:
        project = str(self.current_project_dir) if self.current_project_dir else "(none)"
        git_state = "dirty" if dirty else "clean"
        self.statusBar().showMessage(
            f"Project: {project} | Branch: {branch} | Git: {git_state} | Build: {self._last_build_status}"
        )

    def _git_root(self) -> Path | None:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(self.current_project_dir),
                check=True,
                capture_output=True,
                text=True,
            )
            return Path(result.stdout.strip())
        except Exception:
            return None

    def _tracked_files(self, repo_root: Path) -> list[str]:
        import subprocess
        result = subprocess.run(["git", "ls-files"], cwd=repo_root, check=False, capture_output=True, text=True)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _update_gitignore(self, repo_root: Path, pattern: str) -> None:
        gitignore = repo_root / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
        if pattern not in lines:
            lines.append(pattern)
            gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            self.log_panel.append_text(f"[git] Added '{pattern}' to {gitignore}\n")

    @staticmethod
    def _pattern_matches(pattern: str, file_path: str) -> bool:
        p = pattern.strip()
        if p.endswith("/"):
            d = p.rstrip("/")
            return file_path == d or file_path.startswith(f"{d}/") or f"/{d}/" in file_path
        return fnmatch(file_path, p) or fnmatch(Path(file_path).name, p)

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
        self._active_build_file = self.current_file
        self.build_service.build(self.current_file)

    def _on_build_finished(self, success: bool, message: str) -> None:
        self._last_build_status = "success" if success else "failed"
        self.log_panel.append_text(f"\n=== {message} ===\n")
        build_file = self._active_build_file
        self._active_build_file = None
        self.git_service.refresh_repo_status()

        if not success or build_file is None:
            return
        pdf_path = build_file.with_suffix(".pdf")
        if not pdf_path.exists():
            self.log_panel.append_text(f"Expected PDF not found: {pdf_path}\n")
            return
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf_path)))
        self.log_panel.append_text((f"Opened PDF: {pdf_path}\n") if opened else (f"Could not open PDF: {pdf_path}\n"))
