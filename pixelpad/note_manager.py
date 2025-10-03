from __future__ import annotations

import os
import platform
import subprocess
from configparser import ConfigParser
from pathlib import Path
from typing import List, Optional, Sequence


class NotesRepositoryNotConfiguredError(RuntimeError):
    """Raised when repository-dependent operations run without a configured repo."""


class UnsupportedNoteExtensionError(ValueError):
    """Raised when attempting to operate on a file with an unsupported extension."""


class NoteManager:
    """File-system centric manager for PixelPad notes and configuration.

    Phase 1 focuses purely on repository and note file operations so the GUI can
    rely on a stable API once it arrives in later phases.
    """

    CONFIG_DIR_NAME = ".pixelpad"
    CONFIG_FILENAME = "config.ini"
    CONFIG_SECTION = "pixelpad"
    REPO_KEY = "repository_path"
    SUPPORTED_EXTENSIONS: Sequence[str] = (".txt", ".md")
    RECENT_LIMIT = 10

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else Path.home() / self.CONFIG_DIR_NAME
        self._config_file = self._config_dir / self.CONFIG_FILENAME
        self._config = ConfigParser()
        self._repository_path: Optional[Path] = None
        self._load_repository_path()

    # ------------------------------------------------------------------
    # Configuration helpers
    def _load_repository_path(self) -> None:
        if not self._config_file.exists():
            return
        self._config.read(self._config_file, encoding="utf-8")
        if not self._config.has_section(self.CONFIG_SECTION):
            return
        repo_value = self._config.get(self.CONFIG_SECTION, self.REPO_KEY, fallback=None)
        if not repo_value:
            return
        path = Path(repo_value).expanduser()
        self._repository_path = path.resolve()

    def get_repository_path(self) -> Optional[Path]:
        return self._repository_path

    def require_repository(self) -> Path:
        return self._ensure_repository()

    def set_repository_path(self, path: Path | str) -> Path:
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Repository path does not exist: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {resolved}")

        if not self._config.has_section(self.CONFIG_SECTION):
            self._config.add_section(self.CONFIG_SECTION)
        self._config.set(self.CONFIG_SECTION, self.REPO_KEY, str(resolved))
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with self._config_file.open("w", encoding="utf-8") as config_stream:
            self._config.write(config_stream)

        self._repository_path = resolved
        return resolved

    # ------------------------------------------------------------------
    # Note helpers
    def _ensure_repository(self) -> Path:
        if not self._repository_path:
            raise NotesRepositoryNotConfiguredError("Notes repository has not been configured yet.")
        if not self._repository_path.exists():
            raise NotesRepositoryNotConfiguredError(
                f"Configured repository path is missing: {self._repository_path}"
            )
        if not self._repository_path.is_dir():
            raise NotesRepositoryNotConfiguredError(
                f"Configured repository path is not a directory: {self._repository_path}"
            )
        return self._repository_path

    def _ensure_supported_extension(self, note_path: Path) -> None:
        if note_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedNoteExtensionError(f"Unsupported note extension: {note_path.suffix}")

    def _resolve_note_path(self, note: Path | str) -> Path:
        repo = self._ensure_repository().resolve()
        note_path = Path(note)
        if not note_path.is_absolute():
            note_path = repo / note_path
        note_path = note_path.expanduser().resolve()
        try:
            note_path.relative_to(repo)
        except ValueError as exc:
            raise ValueError("Note path must reside within the configured repository.") from exc
        self._ensure_supported_extension(note_path)
        return note_path

    def load_note(self, note: Path | str) -> str:
        note_path = self._resolve_note_path(note)
        if not note_path.exists():
            raise FileNotFoundError(f"Cannot load missing note: {note_path}")
        return note_path.read_text(encoding="utf-8")

    def save_note(self, note: Path | str, content: str) -> Path:
        note_path = self._resolve_note_path(note)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(content, encoding="utf-8")
        return note_path

    def get_all_notes(self) -> List[Path]:
        repo = self._ensure_repository()
        notes = [
            path
            for path in repo.rglob("*")
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        return sorted(notes, key=lambda p: p.name.lower())

    def get_recent_notes(self) -> List[Path]:
        notes = self.get_all_notes()
        notes.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return notes[: self.RECENT_LIMIT]

    def create_note(
        self,
        filename: str,
        extension: str = ".txt",
        *,
        directory: Path | str | None = None,
        overwrite: bool = False,
    ) -> Path:
        repo = self._ensure_repository()
        target_dir = self._resolve_directory(directory)
        candidate = Path(filename)
        base_name = candidate.stem if candidate.suffix else candidate.name
        ext = candidate.suffix.lower() if candidate.suffix else extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedNoteExtensionError(f"Unsupported note extension: {ext}")
        safe_name = Path(base_name).name
        if not safe_name:
            raise ValueError("Filename must not be empty.")
        note_path = (target_dir / safe_name).with_suffix(ext)
        note_path = note_path.resolve()
        try:
            note_path.relative_to(repo.resolve())
        except ValueError as exc:
            raise ValueError("Generated note path escapes the repository.") from exc
        if note_path.exists() and not overwrite:
            raise FileExistsError(f"Note already exists: {note_path}")
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.touch(exist_ok=overwrite)
        return note_path

    def create_notebook(
        self,
        name: str,
        parent: Path | str | None = None,
        *,
        exist_ok: bool = False,
    ) -> Path:
        repo = self._ensure_repository()
        parent_dir = self._resolve_directory(parent)
        if parent_dir == repo and parent is None:
            parent_dir = repo
        folder_name = Path(name).name.strip()
        if not folder_name:
            raise ValueError("Notebook name must not be empty.")
        notebook_path = (parent_dir / folder_name).resolve()
        try:
            notebook_path.relative_to(repo.resolve())
        except ValueError as exc:
            raise ValueError("Notebook must reside within the configured repository.") from exc
        if notebook_path.exists():
            if not notebook_path.is_dir():
                raise FileExistsError(f"A file with that name already exists: {notebook_path}")
            if not exist_ok:
                raise FileExistsError(f"Notebook already exists: {notebook_path}")
            return notebook_path
        notebook_path.mkdir(parents=True, exist_ok=False)
        return notebook_path

    def delete_notebook(
        self,
        notebook: Path | str,
        *,
        recursive: bool = False,
    ) -> None:
        repo = self._ensure_repository().resolve()
        notebook_path = self._resolve_directory_path(notebook)
        if notebook_path == repo:
            raise ValueError("Cannot delete the repository root as a notebook.")
        if not notebook_path.exists():
            raise FileNotFoundError(f"Notebook does not exist: {notebook_path}")
        if not notebook_path.is_dir():
            raise NotADirectoryError(f"Target is not a notebook directory: {notebook_path}")

        contents = list(notebook_path.iterdir())
        if contents and not recursive:
            raise OSError("Notebook is not empty. Pass recursive=True to delete its contents.")

        if recursive:
            # Remove files and nested directories first.
            for child in sorted(contents, reverse=True):
                if child.is_dir():
                    self.delete_notebook(child, recursive=True)
                else:
                    child.unlink()

        notebook_path.rmdir()
        parent = notebook_path.parent
        while parent != repo and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    def rename_note(
        self,
        note: Path | str,
        new_name: Path | str,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Rename an existing note within the configured repository."""
        note_path = self._resolve_note_path(note)
        if not note_path.exists():
            raise FileNotFoundError(f"Cannot rename missing note: {note_path}")
        repo = self._ensure_repository().resolve()
        target = Path(new_name)
        if not target.is_absolute():
            target = repo / target
        target = target.expanduser().resolve(strict=False)
        try:
            target.relative_to(repo)
        except ValueError as exc:
            raise ValueError("Renamed note must remain within the configured repository.") from exc
        if target.is_dir():
            raise IsADirectoryError(f"Cannot rename note to a directory: {target}")
        if not target.suffix:
            target = target.with_suffix(note_path.suffix)
        extension = target.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedNoteExtensionError(f"Unsupported note extension: {extension}")
        if target == note_path:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if overwrite:
                target.unlink()
            else:
                raise FileExistsError(f"Target note already exists: {target}")
        note_path.rename(target)
        return target

    def delete_note(self, note: Path | str) -> None:
        note_path = self._resolve_note_path(note)
        if not note_path.exists():
            raise FileNotFoundError(f"Cannot delete missing note: {note_path}")
        note_path.unlink()

    def open_repository(self) -> None:
        repo = self._ensure_repository()
        system = platform.system()
        repo_str = str(repo)
        if system == "Windows":
            os.startfile(repo_str)  # type: ignore[attr-defined]
            return
        if system == "Darwin":
            subprocess.run(["open", repo_str], check=False)
            return
        subprocess.run(["xdg-open", repo_str], check=False)

    def get_all_notebooks(self) -> List[Path]:
        repo = self._ensure_repository()
        notebooks = [path for path in repo.rglob("*") if path.is_dir()]
        notebooks_sorted = sorted(
            notebooks,
            key=lambda path: path.relative_to(repo).as_posix(),
        )
        return notebooks_sorted

    def _resolve_directory(self, directory: Path | str | None) -> Path:
        repo = self._ensure_repository().resolve()
        if directory is None:
            return repo
        directory_path = Path(directory)
        if not directory_path.is_absolute():
            directory_path = repo / directory_path
        directory_path = directory_path.expanduser().resolve()
        try:
            directory_path.relative_to(repo)
        except ValueError as exc:
            raise ValueError("Directory must reside within the configured repository.") from exc
        if directory_path.exists() and not directory_path.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {directory_path}")
        directory_path.mkdir(parents=True, exist_ok=True)
        return directory_path

    def _resolve_directory_path(self, directory: Path | str) -> Path:
        repo = self._ensure_repository().resolve()
        directory_path = Path(directory)
        if not directory_path.is_absolute():
            directory_path = repo / directory_path
        directory_path = directory_path.expanduser().resolve()
        try:
            directory_path.relative_to(repo)
        except ValueError as exc:
            raise ValueError("Directory must reside within the configured repository.") from exc
        if directory_path.exists() and not directory_path.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {directory_path}")
        return directory_path
