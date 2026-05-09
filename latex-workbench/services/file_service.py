"""File service helpers for reading and writing .tex files."""

from pathlib import Path


class FileService:
    """Small wrapper for text file IO."""

    @staticmethod
    def read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def write_text(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
