"""Git service for project-scoped git commands."""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class GitService(QObject):
    output_received = Signal(str)
    branches_received = Signal(list)
    repo_status_received = Signal(dict)

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
        self._refresh_status_after_branches = False

    def set_project_dir(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def run_pull(self) -> None:
        self._run_git(["pull"], action="pull")

    def run_status(self) -> None:
        self._run_git(["status"], action="status")

    def run_push(self) -> None:
        self._run_git(["push"], action="push")

    def refresh_branches(self) -> None:
        self._run_git(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short)|%(committerdate:iso8601)",
                "refs/heads",
                "refs/remotes",
            ],
            action="branches",
        )

    def refresh_repo_status(self) -> None:
        self._run_git(["status", "--porcelain", "--branch"], action="repo_status")

    def checkout_branch(self, branch_name: str) -> None:
        normalized = branch_name.strip()

        if normalized.startswith("origin/"):
            local_branch = normalized.replace("origin/", "", 1)
            self.output_received.emit(
                f"[git] Remote branch '{normalized}' selected. Creating local tracking branch '{local_branch}'.\n"
            )
            self._run_git(["checkout", "-B", local_branch, "--track", normalized], action="checkout")
            return

        self._run_git(["checkout", normalized], action="checkout")

    def run_autopush(self, commit_message: str) -> None:
        msg = commit_message.strip()
        if not msg:
            self.output_received.emit("[git] Commit message cannot be empty.\n")
            return

        self._run_git(["add", "-A"], action="autopush_add", chain=["commit", msg])

    def _run_git(self, args: list[str], action: str, chain: list[str] | None = None) -> None:
        if self._project_dir is None:
            self.output_received.emit("[git] Open a .tex file first to set project directory.\n")
            return
        if self._process.state() != QProcess.NotRunning:
            self.output_received.emit("[git] Another git command is running. Please wait.\n")
            return

        self._stdout_buffer = ""
        self._pending_action = action if not chain else f"{action}:{'|'.join(chain)}"
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
        action = self._pending_action or ""

        if action.startswith("autopush_add:") and exit_code == 0:
            _, tail = action.split(":", 1)
            _, msg = tail.split("|", 1)
            self._pending_action = None
            self._run_git(["commit", "-m", msg], action="autopush_commit")
            return

        if action == "autopush_commit" and exit_code == 0:
            self._pending_action = None
            self._run_git(["push"], action="autopush_push")
            return

        if action in {"autopush_push", "pull", "push", "checkout"} and exit_code == 0:
            self.refresh_branches()
            self.refresh_repo_status()

        if action == "branches" and exit_code == 0:
            self.branches_received.emit(self._parse_branches(self._stdout_buffer))

        if action == "repo_status" and exit_code == 0:
            self.repo_status_received.emit(self._parse_repo_status(self._stdout_buffer))

        if action == "repo_status" and exit_code == 0:
            self.repo_status_received.emit(self._parse_repo_status(self._stdout_buffer))

    @staticmethod
    def _parse_branches(branch_output: str) -> list[dict]:
        branches: list[dict] = []
        for raw_line in branch_output.splitlines():
            line = raw_line.strip()
            if not line or "->" in line or "|" not in line:
                continue
            name, date = line.split("|", 1)
            branches.append({"name": name.strip(), "date": date.strip()})
        return branches

    @staticmethod
    def _parse_repo_status(status_output: str) -> dict:
        branch = "unknown"
        dirty = False
        for idx, line in enumerate(status_output.splitlines()):
            if idx == 0 and line.startswith("##"):
                branch = line.replace("##", "").strip().split("...", 1)[0]
                continue
            if line.strip():
                dirty = True
        return {"branch": branch, "dirty": dirty}
