"""Build service for running latexmk in a non-blocking way."""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class BuildService(QObject):
    """Runs latexmk asynchronously and forwards process output."""

    output_received = Signal(str)
    build_finished = Signal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

    def is_running(self) -> bool:
        return self._process.state() != QProcess.NotRunning

    def build(self, tex_file: Path) -> None:
        """Start a latexmk build for the given .tex file."""
        if self.is_running():
            self.output_received.emit("Build already running. Please wait.\n")
            return

        working_dir = str(tex_file.parent)
        args = [
            "-xelatex",
            "-interaction=nonstopmode",
            "-file-line-error",
            tex_file.name,
        ]

        self.output_received.emit(
            f"\n=== Building: {tex_file.name} in {working_dir} ===\n"
            f"Command: latexmk {' '.join(args)}\n\n"
        )

        self._process.setWorkingDirectory(working_dir)
        self._process.start("latexmk", args)

    def _on_stdout(self) -> None:
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _on_stderr(self) -> None:
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        success = exit_code == 0 and exit_status == QProcess.NormalExit
        message = "Build succeeded." if success else f"Build failed (exit code {exit_code})."
        self.build_finished.emit(success, message)

    def _on_error(self, process_error: QProcess.ProcessError) -> None:
        if process_error == QProcess.FailedToStart:
            self.build_finished.emit(False, "Failed to start latexmk. Is it installed and in PATH?")
        else:
            self.build_finished.emit(False, f"Process error: {process_error}")
