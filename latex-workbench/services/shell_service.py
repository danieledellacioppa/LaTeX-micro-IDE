"""Shell service for running simple shell commands in a project directory.

This is intentionally a non-PTY console based on QProcess.
It does not support real terminal features like TAB completion,
arrow-key history, or fullscreen terminal applications.
"""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class ShellService(QObject):
    output_received = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._project_dir: Path | None = None
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)

    def set_project_dir(self, project_dir: Path) -> None:
        self._project_dir = project_dir
        self.output_received.emit(f"[shell] Project directory set to: {project_dir}\n")

    def run_command(self, command: str) -> None:
        if not command.strip():
            return
        if self._project_dir is None:
            self.output_received.emit("[shell] Open a .tex file first to set project directory.\n")
            return
        if self._process.state() != QProcess.NotRunning:
            self.output_received.emit("[shell] Command already running. Please wait.\n")
            return

        shell_program = "/bin/zsh" if Path("/bin/zsh").exists() else "sh"
        self._process.setWorkingDirectory(str(self._project_dir))
        self.output_received.emit(
            f"\n[shell] {shell_program} -lc \"{command}\"\n[shell] cwd: {self._project_dir}\n"
        )
        self._process.start(shell_program, ["-lc", command])

    def _on_stdout(self) -> None:
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _on_stderr(self) -> None:
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)
