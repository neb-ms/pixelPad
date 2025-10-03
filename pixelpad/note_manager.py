from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, List, Optional, Sequence


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
    THEME_KEY = "theme"
    DEFAULT_THEME = "dark"
    VALID_THEMES = {"dark", "light"}
    SUPPORTED_EXTENSIONS: Sequence[str] = (".txt", ".md")
    RECENT_LIMIT = 10
    METADATA_DIR_NAME = "metadata"
    COLOR_METADATA_FILENAME = "colors.json"
    NOTE_COLORS_KEY = "notes"
    NOTEBOOK_COLORS_KEY = "notebooks"
    LEGACY_METADATA_DIR_NAME = ".pixelpad"

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else Path.home() / self.CONFIG_DIR_NAME
        self._config_file = self._config_dir / self.CONFIG_FILENAME
        self._config = ConfigParser()
        self._repository_path: Optional[Path] = None
        self._preferred_theme = self.DEFAULT_THEME
        self._load_repository_path()
        self._metadata: Dict[str, Dict[str, str]] = {self.NOTE_COLORS_KEY: {}, self.NOTEBOOK_COLORS_KEY: {}}
        self._metadata_loaded_for: Optional[Path] = None
        if self._repository_path:
            try:
                self._ensure_metadata_loaded()
            except NotesRepositoryNotConfiguredError:
                self._metadata_loaded_for = None

    # ------------------------------------------------------------------
    # Configuration helpers
    def _load_repository_path(self) -> None:
        if not self._config_file.exists():
            return
        self._config.read(self._config_file, encoding="utf-8")
        if not self._config.has_section(self.CONFIG_SECTION):
            return
        theme_value = self._config.get(self.CONFIG_SECTION, self.THEME_KEY, fallback=None)
        self._preferred_theme = self._normalize_theme(theme_value)
        repo_value = self._config.get(self.CONFIG_SECTION, self.REPO_KEY, fallback=None)
        if not repo_value:
            return
        path = Path(repo_value).expanduser()
        self._repository_path = path.resolve()


    @classmethod
    def _normalize_theme(cls, theme: object) -> str:
        if theme is None:
            return cls.DEFAULT_THEME
        candidate = str(theme).strip().lower()
        if not candidate:
            return cls.DEFAULT_THEME
        if candidate not in cls.VALID_THEMES:
            return cls.DEFAULT_THEME
        return candidate

    def get_theme(self) -> str:
        return self._preferred_theme

    def set_theme(self, theme: str) -> str:
        normalized = self._normalize_theme(theme)
        if normalized == self._preferred_theme and self._config.has_section(self.CONFIG_SECTION):
            existing = self._config.get(self.CONFIG_SECTION, self.THEME_KEY, fallback=normalized)
            if self._normalize_theme(existing) == normalized:
                return normalized
        self._preferred_theme = normalized
        if not self._config.has_section(self.CONFIG_SECTION):
            self._config.add_section(self.CONFIG_SECTION)
        self._config.set(self.CONFIG_SECTION, self.THEME_KEY, normalized)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with self._config_file.open("w", encoding="utf-8") as config_stream:
            self._config.write(config_stream)
        return normalized


    def _metadata_dir(self) -> Path:
        repo = self._ensure_repository().resolve()
        digest = hashlib.sha1(str(repo).encode("utf-8")).hexdigest()
        return self._config_dir / self.METADATA_DIR_NAME / digest

    def _metadata_file(self) -> Path:
        return self._metadata_dir() / self.COLOR_METADATA_FILENAME

    def _legacy_metadata_file(self, repo: Path) -> Path:
        return repo / self.LEGACY_METADATA_DIR_NAME / self.COLOR_METADATA_FILENAME

    def _ensure_metadata_loaded(self) -> None:
        repo = self._ensure_repository().resolve()
        if self._metadata_loaded_for and self._metadata_loaded_for == repo:
            return
        metadata: Dict[str, Dict[str, str]] = {
            self.NOTE_COLORS_KEY: {},
            self.NOTEBOOK_COLORS_KEY: {},
        }
        metadata_file = self._metadata_file()
        if not metadata_file.exists():
            legacy_file = self._legacy_metadata_file(repo)
            if legacy_file.exists():
                try:
                    contents = legacy_file.read_text(encoding="utf-8")
                except OSError:
                    contents = None
                else:
                    metadata_file.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        metadata_file.write_text(contents, encoding="utf-8")
                    except OSError:
                        pass
                    try:
                        legacy_file.unlink()
                        legacy_dir = legacy_file.parent
                        if legacy_dir.exists() and legacy_dir != repo and not any(legacy_dir.iterdir()):
                            legacy_dir.rmdir()
                    except OSError:
                        pass
        if metadata_file.exists():
            try:
                raw = json.loads(metadata_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = {}
            if isinstance(raw, dict):
                for key in (self.NOTE_COLORS_KEY, self.NOTEBOOK_COLORS_KEY):
                    section = raw.get(key, {})
                    if not isinstance(section, dict):
                        continue
                    sanitized: Dict[str, str] = {}
                    for rel_path, color in section.items():
                        if not isinstance(rel_path, str):
                            continue
                        normalized = self._sanitize_color(color)
                        if normalized:
                            sanitized[rel_path] = normalized
                    metadata[key] = sanitized
        self._metadata = metadata
        self._metadata_loaded_for = repo
        self._prune_missing_metadata()

    def _prune_missing_metadata(self) -> None:
        if not self._repository_path:
            return
        repo = self._repository_path.resolve()
        changed = False
        for key in (self.NOTE_COLORS_KEY, self.NOTEBOOK_COLORS_KEY):
            mapping = self._metadata.get(key, {})
            for rel_path in list(mapping.keys()):
                absolute = (repo / Path(rel_path)).resolve()
                if not absolute.exists():
                    mapping.pop(rel_path, None)
                    changed = True
        if changed:
            self._save_metadata()

    def _save_metadata(self) -> None:
        metadata_file = self._metadata_file()
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            self.NOTE_COLORS_KEY: dict(self._metadata.get(self.NOTE_COLORS_KEY, {})),
            self.NOTEBOOK_COLORS_KEY: dict(self._metadata.get(self.NOTEBOOK_COLORS_KEY, {})),
        }
        metadata_file.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    def _sanitize_color(self, color: object) -> str | None:
        if not isinstance(color, str):
            return None
        candidate = color.strip()
        if not candidate:
            return None
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", candidate):
            return None
        if not candidate.startswith("#"):
            candidate = f"#{candidate}"
        return candidate.upper()

    def _ensure_relative_key(self, path: Path) -> str:
        repo = self._ensure_repository().resolve()
        absolute = Path(path).resolve()
        try:
            relative = absolute.relative_to(repo).as_posix()
        except ValueError as exc:
            raise ValueError("Target path must reside within the configured repository.") from exc
        return relative

    def _set_color_entry(self, key: str, target_path: Path, color: str | None) -> None:
        self._ensure_metadata_loaded()
        relative = self._ensure_relative_key(target_path)
        mapping = self._metadata.setdefault(key, {})
        if color is None:
            if relative in mapping:
                mapping.pop(relative, None)
                self._save_metadata()
            return
        normalized = self._sanitize_color(color)
        if normalized is None:
            raise ValueError("Color must be a hex value in the form #RRGGBB.")
        if mapping.get(relative) == normalized:
            return
        mapping[relative] = normalized
        self._save_metadata()

    def _remove_color_subtree(self, key: str, target_path: Path) -> None:
        self._ensure_metadata_loaded()
        relative = self._ensure_relative_key(target_path)
        mapping = self._metadata.setdefault(key, {})
        prefix = f"{relative}/"
        removed = False
        for entry in list(mapping.keys()):
            if entry == relative or entry.startswith(prefix):
                mapping.pop(entry, None)
                removed = True
        if removed:
            self._save_metadata()

    def _reassign_color_subtree(self, key: str, old_path: Path, new_path: Path) -> None:
        self._ensure_metadata_loaded()
        old_rel = self._ensure_relative_key(old_path)
        new_rel = self._ensure_relative_key(new_path)
        if old_rel == new_rel:
            return
        mapping = self._metadata.setdefault(key, {})
        prefix = f"{old_rel}/"
        updates: Dict[str, str] = {}
        changed = False
        for entry in list(mapping.keys()):
            if entry == old_rel or entry.startswith(prefix):
                suffix = entry[len(old_rel):].lstrip("/")
                replacement = new_rel if not suffix else f"{new_rel}/{suffix}"
                updates[replacement] = mapping.pop(entry)
                changed = True
        if changed:
            mapping.update(updates)
            self._save_metadata()

    def _set_note_color(self, note_path: Path, color: str | None) -> None:
        self._set_color_entry(self.NOTE_COLORS_KEY, note_path, color)

    def _set_notebook_color(self, notebook_path: Path, color: str | None) -> None:
        self._set_color_entry(self.NOTEBOOK_COLORS_KEY, notebook_path, color)

    def _remove_note_color(self, note_path: Path) -> None:
        self._set_color_entry(self.NOTE_COLORS_KEY, note_path, None)

    def _remove_notebook_tree_colors(self, notebook_path: Path) -> None:
        self._remove_color_subtree(self.NOTEBOOK_COLORS_KEY, notebook_path)
        self._remove_color_subtree(self.NOTE_COLORS_KEY, notebook_path)

    def _reassign_note_color(self, old_path: Path, new_path: Path) -> None:
        self._reassign_color_subtree(self.NOTE_COLORS_KEY, old_path, new_path)

    def _reassign_notebook_tree_colors(self, old_path: Path, new_path: Path) -> None:
        self._reassign_color_subtree(self.NOTEBOOK_COLORS_KEY, old_path, new_path)
        self._reassign_color_subtree(self.NOTE_COLORS_KEY, old_path, new_path)

    def get_note_colors(self) -> Dict[Path, str]:
        self._ensure_metadata_loaded()
        repo = self._ensure_repository().resolve()
        mapping = self._metadata.get(self.NOTE_COLORS_KEY, {})
        results: Dict[Path, str] = {}
        missing = False
        for rel_path, color in list(mapping.items()):
            absolute = (repo / Path(rel_path)).resolve()
            if not absolute.exists():
                mapping.pop(rel_path, None)
                missing = True
                continue
            results[absolute] = color
        if missing:
            self._save_metadata()
        return results

    def get_notebook_colors(self) -> Dict[Path, str]:
        self._ensure_metadata_loaded()
        repo = self._ensure_repository().resolve()
        mapping = self._metadata.get(self.NOTEBOOK_COLORS_KEY, {})
        results: Dict[Path, str] = {}
        missing = False
        for rel_path, color in list(mapping.items()):
            absolute = (repo / Path(rel_path)).resolve()
            if not absolute.exists():
                mapping.pop(rel_path, None)
                missing = True
                continue
            results[absolute] = color
        if missing:
            self._save_metadata()
        return results

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
        self._config.set(self.CONFIG_SECTION, self.THEME_KEY, self._preferred_theme)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with self._config_file.open("w", encoding="utf-8") as config_stream:
            self._config.write(config_stream)

        self._repository_path = resolved
        self._metadata = {self.NOTE_COLORS_KEY: {}, self.NOTEBOOK_COLORS_KEY: {}}
        self._metadata_loaded_for = None
        self._ensure_metadata_loaded()
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
        color: str | None = None,
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
        if color is not None:
            self._set_note_color(note_path, color)
        elif overwrite:
            self._set_note_color(note_path, None)
        return note_path

    def create_notebook(
        self,
        name: str,
        parent: Path | str | None = None,
        *,
        exist_ok: bool = False,
        color: str | None = None,
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
            if color is not None:
                self._set_notebook_color(notebook_path, color)
            return notebook_path
        notebook_path.mkdir(parents=True, exist_ok=False)
        if color is not None:
            self._set_notebook_color(notebook_path, color)
        return notebook_path


    def rename_notebook(
        self,
        notebook: Path | str,
        new_name: str,
    ) -> Path:
        repo = self._ensure_repository().resolve()
        notebook_path = self._resolve_directory_path(notebook).resolve()
        if notebook_path == repo:
            raise ValueError("Cannot rename the repository root notebook.")
        cleaned = Path(new_name).name.strip()
        if not cleaned:
            raise ValueError("Notebook name must not be empty.")
        target = (notebook_path.parent / cleaned).resolve()
        try:
            target.relative_to(repo)
        except ValueError as exc:
            raise ValueError("Renamed notebook must remain within the configured repository.") from exc
        if target.exists():
            raise FileExistsError(f"Target notebook already exists: {target}")
        notebook_path.rename(target)
        self._reassign_notebook_tree_colors(notebook_path, target)
        return target

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
                    self._remove_note_color(child)
                    child.unlink()

        notebook_path.rmdir()
        self._remove_notebook_tree_colors(notebook_path)
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
        self._reassign_note_color(note_path, target)
        return target

    def delete_note(self, note: Path | str) -> None:
        note_path = self._resolve_note_path(note)
        if not note_path.exists():
            raise FileNotFoundError(f"Cannot delete missing note: {note_path}")
        note_path.unlink()
        self._remove_note_color(note_path)

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
