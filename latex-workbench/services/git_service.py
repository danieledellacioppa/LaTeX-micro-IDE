"""Git service for project-scoped git commands."""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class GitService(QObject):
    output_received = Signal(str)
    branches_received = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_dir: Path | None = None
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._pending_action: str | None = None
        self._stdout_buffer: str = ""

    def set_project_dir(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def run_pull(self) -> None:
        self._run_git(["pull"], action="pull")

    def run_status(self) -> None:
        self._run_git(["status"], action="status")

    def run_push(self) -> None:
        self._run_git(["push"], action="push")

    def refresh_branches(self) -> None:
        self._run_git(["branch", "--all"], action="branches")

    def checkout_branch(self, branch_name: str) -> None:
        if branch_name.startswith("remotes/"):
            branch_name = branch_name.replace("remotes/", "", 1)
        self._run_git(["checkout", branch_name], action="checkout")

    def _run_git(self, args: list[str], action: str) -> None:
        if self._project_dir is None:
            self.output_received.emit("[git] Open a .tex file first to set project directory.\n")
            return
        if self._process.state() != QProcess.NotRunning:
            self.output_received.emit("[git] Another git command is running. Please wait.\n")
            return

        self._stdout_buffer = ""
        self._pending_action = action
        self._process.setWorkingDirectory(str(self._project_dir))
        self.output_received.emit(f"\n[git] git {' '.join(args)}\n[git] cwd: {self._project_dir}\n")
        self._process.start("git", args)

    def _on_stdout(self) -> None:
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self._stdout_buffer += data
            self.output_received.emit(data)

    def _on_stderr(self) -> None:
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self._pending_action == "branches" and exit_code == 0:
            branches = self._parse_branches(self._stdout_buffer)
            self.branches_received.emit(branches)
        elif self._pending_action == "checkout" and exit_code == 0:
            self.refresh_branches()
        self._pending_action = None

    @staticmethod
    def _parse_branches(branch_output: str) -> list[str]:
        branches: list[str] = []
        for raw_line in branch_output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "->" in line:
                continue
            line = line.lstrip("* ").strip()
            if line not in branches:
                branches.append(line)
        return branches
