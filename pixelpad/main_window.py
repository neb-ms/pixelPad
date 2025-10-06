from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSignalBlocker, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QPixmap, QShortcut, QColor
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
)

from .editor_widget import EditorWidget
from .note_manager import (
    NoteManager,
    NotesRepositoryNotConfiguredError,
    UnsupportedNoteExtensionError,
)
from .sidebar_widget import SidebarWidget
from .qss_styles import apply_theme
from .responsive_toolbar import ResponsiveToolBar


def find_logo_path() -> Optional[Path]:
    """Return the first available logo path that exists, or None if missing."""

    candidates = [
        Path(__file__).resolve().parent.parent / "pics" / "pixelPad-logo.png",
        Path.cwd() / "pics" / "pixelPad-logo.png",
        Path.home() / "pics" / "pixelPad-logo.png",
    ]
    for logo_path in candidates:
        if logo_path.exists():
            return logo_path
    return None


class PixelPadMainWindow(QMainWindow):
    """Main window connecting the NoteManager with the GUI widgets."""

    def __init__(self, note_manager: NoteManager) -> None:
        super().__init__()
        self._note_manager = note_manager
        self._current_note: Optional[Path] = None
        self._current_theme = self._note_manager.get_theme()
        self._last_note_color = "#5E9CFF"
        self._last_notebook_color = "#FFB74D"

        self.setWindowTitle("PixelPad")
        self.resize(1024, 640)
        self.setStatusBar(QStatusBar(self))

        self._sidebar = SidebarWidget(self)
        self._editor = EditorWidget(self)

        splitter = QSplitter(self)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        toolbar = ResponsiveToolBar(self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        toolbar.setIconSize(QSize(16, 16))
        self.setMenuWidget(toolbar)
        self._logo_label: Optional[QLabel] = None
        logo_pixmap = self._load_logo_pixmap()
        if not logo_pixmap.isNull():
            self.setWindowIcon(QIcon(logo_pixmap))
            self._logo_label = QLabel(self)
            self._logo_label.setObjectName("toolbarLogo")
            target_height = max(toolbar.iconSize().height(), 32)
            scaled = logo_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            self._logo_label.setPixmap(scaled)
            self._logo_label.setToolTip("PixelPad")
            toolbar.addWidget(self._logo_label)
            toolbar.addSeparator()
        self._new_note_action = QAction("New Note", self)
        self._new_note_action.setShortcut("Ctrl+N")
        toolbar.addAction(self._new_note_action)
        self._rename_note_action = QAction("Rename Note", self)
        self._rename_note_action.setShortcut("F2")
        self._rename_note_action.setEnabled(False)
        toolbar.addAction(self._rename_note_action)
        self._delete_note_action = QAction("Delete Note", self)
        self._delete_note_action.setShortcut("Ctrl+Shift+D")
        self._delete_note_action.setEnabled(False)
        toolbar.addAction(self._delete_note_action)
        self._new_notebook_action = QAction("New Notebook", self)
        self._new_notebook_action.setShortcut("Ctrl+Shift+N")
        toolbar.addAction(self._new_notebook_action)
        self._rename_notebook_action = QAction("Rename Notebook", self)
        self._rename_notebook_action.setShortcut("Ctrl+Shift+R")
        toolbar.addAction(self._rename_notebook_action)
        self._delete_notebook_action = QAction("Delete Notebook", self)
        self._delete_notebook_action.setShortcut("Ctrl+Shift+Delete")
        self._delete_notebook_action.setEnabled(False)
        toolbar.addAction(self._delete_notebook_action)

        toolbar.addSeparator()
        self._line_numbers_action = QAction("Line Numbers", self)
        self._line_numbers_action.setCheckable(True)
        self._line_numbers_action.setChecked(True)
        toolbar.addAction(self._line_numbers_action)
        self._light_mode_action = QAction("Light Mode", self)
        self._light_mode_action.setCheckable(True)
        self._light_mode_action.setChecked(False)
        toolbar.addAction(self._light_mode_action)

        self._focus_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._focus_search_shortcut.activated.connect(self._focus_sidebar_search)

        self._sidebar.note_selected.connect(self._handle_note_selected)
        self._sidebar.note_move_requested.connect(self._handle_note_move_requested)
        self._sidebar.notebook_move_requested.connect(self._handle_notebook_move_requested)
        self._sidebar.open_repository_requested.connect(self._open_repository)
        self._sidebar.change_repository_requested.connect(self._change_repository)
        self._sidebar.selection_changed.connect(self._refresh_actions)
        self._new_note_action.triggered.connect(self._create_new_note)
        self._rename_note_action.triggered.connect(self._rename_current_note)
        self._delete_note_action.triggered.connect(self._delete_current_note)
        self._line_numbers_action.toggled.connect(self._toggle_line_numbers)
        self._light_mode_action.toggled.connect(self._toggle_theme)
        self._new_notebook_action.triggered.connect(self._create_new_notebook)
        self._rename_notebook_action.triggered.connect(self._rename_current_notebook)
        self._delete_notebook_action.triggered.connect(self._delete_current_notebook)
        self._editor.document().modificationChanged.connect(self._update_window_title)

        if not self._ensure_repository_configured():
            QTimer.singleShot(0, self.close)
            return

        self._refresh_recent_notes()
        self._update_window_title()
        self._update_status_message()
        self._refresh_actions()
        QTimer.singleShot(0, self._open_initial_note)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._auto_save_current_note():
            super().closeEvent(event)
        else:
            event.ignore()

    def _ensure_repository_configured(self) -> bool:
        while True:
            try:
                repo = self._note_manager.require_repository()
                self._sidebar.set_repository_path(repo)
                self._sidebar.select_repository_root()
                return True
            except NotesRepositoryNotConfiguredError as error:
                QMessageBox.information(
                    self,
                    "Configure Repository",
                    f"{error}\n\nPlease select a notes repository to continue.",
                )
            selected = self._prompt_for_repository_path()
            if selected is None:
                choice = QMessageBox.question(
                    self,
                    "Repository Required",
                    "PixelPad needs a notes repository. Exit the application?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if choice == QMessageBox.Yes:
                    return False
                continue
            try:
                resolved = self._note_manager.set_repository_path(selected)
                self._sidebar.set_repository_path(resolved)
                self._sidebar.select_repository_root()
            except (FileNotFoundError, NotADirectoryError) as file_error:
                QMessageBox.warning(self, "Invalid Repository", str(file_error))
                continue
            return True

    def _prompt_for_repository_path(self) -> Optional[Path]:
        directory = QFileDialog.getExistingDirectory(self, "Select Notes Repository")
        if not directory:
            return None
        return Path(directory)

    def _refresh_recent_notes(self) -> None:
        try:
            notes = self._note_manager.get_all_notes()
            notebooks = self._note_manager.get_all_notebooks()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Error", str(error))
            if self._ensure_repository_configured():
                self._refresh_recent_notes()
            return


        repo = self._note_manager.get_repository_path()
        note_colors = self._note_manager.get_note_colors()
        notebook_colors = self._note_manager.get_notebook_colors()
        self._sidebar.set_repository_path(repo)
        self._sidebar.set_content(
            notes=notes,
            notebooks=notebooks,
            note_colors=note_colors,
            notebook_colors=notebook_colors,
        )
        if self._current_note:
            self._sidebar.set_current_note_path(self._current_note)
        else:
            self._sidebar.select_repository_root()
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        has_note = self._current_note is not None
        self._delete_note_action.setEnabled(has_note)
        self._rename_note_action.setEnabled(has_note)
        repo_configured = self._note_manager.get_repository_path() is not None
        self._new_notebook_action.setEnabled(repo_configured)
        self._rename_notebook_action.setEnabled(self._can_rename_current_notebook())
        self._delete_notebook_action.setEnabled(self._can_delete_current_notebook())
        blocker = QSignalBlocker(self._line_numbers_action)
        self._line_numbers_action.setChecked(self._editor.line_numbers_visible())
        del blocker
        theme_blocker = QSignalBlocker(self._light_mode_action)
        self._light_mode_action.setChecked(self._current_theme == "light")
        del theme_blocker
        self._light_mode_action.setText("Dark Mode" if self._current_theme == "light" else "Light Mode")

    def _toggle_line_numbers(self, checked: bool) -> None:
        self._editor.set_line_numbers_visible(checked)

    def _toggle_theme(self, light_mode: bool) -> None:
        app = QApplication.instance()
        if not app:
            return
        requested_theme = "light" if light_mode else "dark"
        self._current_theme = self._note_manager.set_theme(requested_theme)
        apply_theme(app, self._current_theme)
        self._editor.refresh_line_numbers()
        self._refresh_actions()

    def _can_delete_current_notebook(self) -> bool:
        notebook = self._sidebar.current_notebook_path()
        if notebook is None:
            return False
        repo = self._note_manager.get_repository_path()
        if repo is None:
            return False
        try:
            return notebook.resolve() != repo.resolve()
        except FileNotFoundError:
            return False

    def _can_rename_current_notebook(self) -> bool:
        notebook = self._sidebar.current_notebook_path()
        if notebook is None:
            return False
        repo = self._note_manager.get_repository_path()
        if repo is None:
            return False
        try:
            return notebook.resolve() != repo.resolve()
        except FileNotFoundError:
            return False

    def _create_new_notebook(self) -> None:
        try:
            repo = self._note_manager.require_repository()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Not Configured", str(error))
            return
        parent_directory = self._sidebar.current_container_path() or repo
        name, ok = QInputDialog.getText(self, "New Notebook", "Notebook name:")
        if not ok:
            return
        cleaned = name.strip()
        if not cleaned:
            QMessageBox.warning(self, "Invalid Name", "Notebook name cannot be empty.")
            return
        color = QColorDialog.getColor(QColor(self._last_notebook_color), self, "Notebook Color")
        if not color.isValid():
            return
        color_hex = color.name(QColor.HexRgb).upper()
        try:
            notebook_path = self._note_manager.create_notebook(
                cleaned,
                parent_directory,
                color=color_hex,
            )
        except (ValueError, FileExistsError, NotADirectoryError) as error:
            QMessageBox.warning(self, "Cannot Create Notebook", str(error))
            return
        self._last_notebook_color = color_hex
        self.statusBar().showMessage(f"Notebook created: {notebook_path.relative_to(repo)}")
        self._refresh_recent_notes()
        self._sidebar.set_current_notebook_path(notebook_path)

    def _rename_current_notebook(self) -> None:
        notebook_path = self._sidebar.current_notebook_path()
        if notebook_path is None:
            QMessageBox.information(self, "Rename Notebook", "Select a notebook in the sidebar to rename.")
            return
        try:
            repo = self._note_manager.require_repository()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Not Configured", str(error))
            return
        repo = repo.resolve()
        notebook_path = notebook_path.resolve()
        if notebook_path == repo:
            QMessageBox.warning(self, "Cannot Rename", "The repository root cannot be renamed from here.")
            return
        default_name = notebook_path.name
        name, ok = QInputDialog.getText(self, "Rename Notebook", "New notebook name:", text=default_name)
        if not ok:
            return
        cleaned = name.strip()
        if not cleaned:
            QMessageBox.warning(self, "Invalid Name", "Notebook name cannot be empty.")
            return
        if cleaned == notebook_path.name:
            return
        current_note_relative = None
        if self._current_note is not None:
            try:
                current_note_relative = self._current_note.relative_to(notebook_path)
            except ValueError:
                current_note_relative = None
        try:
            target = self._note_manager.rename_notebook(notebook_path, cleaned)
        except FileExistsError:
            QMessageBox.warning(self, "Cannot Rename", f"A folder named '{cleaned}' already exists.")
            return
        except ValueError as error:
            QMessageBox.warning(self, "Cannot Rename", str(error))
            return
        except OSError as error:
            QMessageBox.critical(self, "Unable to Rename Notebook", str(error))
            return
        if current_note_relative is not None:
            self._current_note = (target / current_note_relative).resolve()
            self._load_note(self._current_note)
        else:
            self._refresh_recent_notes()
            self._sidebar.set_current_notebook_path(target)
        self.statusBar().showMessage(f"Notebook renamed to: {target.relative_to(repo)}")

    def _delete_current_notebook(self) -> None:
        notebook_path = self._sidebar.current_notebook_path()
        if notebook_path is None:
            QMessageBox.information(self, "Delete Notebook", "Select a notebook in the sidebar to delete.")
            return
        notebook_path = notebook_path.resolve()
        try:
            repo = self._note_manager.require_repository()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Not Configured", str(error))
            return
        repo = repo.resolve()
        if notebook_path == repo:
            QMessageBox.warning(self, "Cannot Delete", "The repository root cannot be deleted.")
            return

        contents = list(notebook_path.iterdir()) if notebook_path.exists() else []
        if not notebook_path.exists():
            QMessageBox.warning(self, "Notebook Missing", "The selected notebook no longer exists.")
            self._refresh_recent_notes()
            return

        if contents:
            confirm = QMessageBox.question(
                self,
                "Delete Notebook",
                f"'{notebook_path.relative_to(repo)}' contains files or subfolders. Delete everything?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        else:
            confirm = QMessageBox.question(
                self,
                "Delete Notebook",
                f"Delete empty notebook '{notebook_path.relative_to(repo)}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if confirm != QMessageBox.Yes:
                return

        try:
            self._note_manager.delete_notebook(notebook_path, recursive=bool(contents))
        except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as error:
            QMessageBox.critical(self, "Unable to Delete Notebook", str(error))
            return

        if self._current_note is not None:
            try:
                self._current_note.resolve().relative_to(notebook_path)
            except (ValueError, FileNotFoundError):
                pass
            else:
                blocker = QSignalBlocker(self._editor)
                self._editor.clear()
                self._editor.document().setModified(False)
                del blocker
                self._current_note = None

        self._refresh_recent_notes()
        self._sidebar.select_repository_root()
        self._update_window_title()
        self._update_status_message()
        self._refresh_actions()
        self.statusBar().showMessage(f"Notebook deleted: {notebook_path.relative_to(repo)}")

    def _load_logo_pixmap(self) -> QPixmap:
        """Locate and load the PixelPad logo asset, returning an empty pixmap on failure."""

        logo_path = find_logo_path()
        if logo_path is not None:
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                return pixmap
        return QPixmap()

    def _focus_sidebar_search(self) -> None:
        self._sidebar.focus_search()

    def _change_repository(self) -> None:
        if not self._auto_save_current_note():
            return
        new_path = self._prompt_for_repository_path()
        if new_path is None:
            return
        try:
            resolved = self._note_manager.set_repository_path(new_path)
        except (FileNotFoundError, NotADirectoryError) as error:
            QMessageBox.warning(self, "Invalid Repository", str(error))
            return
        self._current_note = None
        self._sidebar.set_repository_path(resolved)
        self._sidebar.select_repository_root()
        self._refresh_recent_notes()
        self._update_window_title()
        self._update_status_message()

    def _open_initial_note(self) -> None:
        if self._current_note:
            return
        try:
            notes = self._note_manager.get_recent_notes()
        except NotesRepositoryNotConfiguredError:
            return
        if notes:
            self._load_note(notes[0])
        else:
            self._prompt_create_initial_note()

    def _prompt_create_initial_note(self) -> None:
        response = QMessageBox.question(
            self,
            "Create First Note",
            "No notes found in the repository. Create one now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if response == QMessageBox.Yes:
            previous_note = self._current_note
            self._create_new_note()
            if self._current_note is None or self._current_note == previous_note:
                QTimer.singleShot(0, self._prompt_create_initial_note)
        else:
            self.statusBar().showMessage("Use New Note to start writing.")

    def _handle_note_selected(self, note: Path) -> None:
        note = note.resolve()
        if self._current_note and note == self._current_note.resolve():
            return
        if not self._auto_save_current_note():
            self._sidebar.set_current_note_path(self._current_note)
            return
        self._load_note(note)

    def _handle_note_move_requested(self, note: Path, target_dir: Path) -> None:
        repo = self._note_manager.get_repository_path()
        if repo is None:
            return
        try:
            repo = repo.resolve()
        except FileNotFoundError:
            pass
        try:
            note_path = Path(note).resolve()
        except FileNotFoundError:
            note_path = Path(note)
        try:
            target_path = Path(target_dir).resolve()
        except FileNotFoundError:
            target_path = Path(target_dir)
        if note_path.parent == target_path:
            return
        try:
            note_path.relative_to(repo)
            target_path.relative_to(repo)
        except ValueError:
            QMessageBox.warning(self, "Cannot Move Note", "Target notebook is outside the repository.")
            return
        is_current = False
        if self._current_note is not None:
            try:
                is_current = note_path.resolve() == self._current_note.resolve()
            except FileNotFoundError:
                is_current = note_path == self._current_note
        if is_current:
            if not self._auto_save_current_note():
                self._sidebar.set_current_note_path(self._current_note)
                return
            note_path = self._current_note
        destination = target_path / note_path.name
        try:
            moved_path = self._note_manager.rename_note(note_path, destination)
        except (UnsupportedNoteExtensionError, ValueError, FileExistsError, FileNotFoundError, IsADirectoryError) as error:
            QMessageBox.warning(self, "Cannot Move Note", str(error))
            self._refresh_recent_notes()
            return
        if is_current:
            self._current_note = moved_path
            self._editor.document().setModified(False)
            self._update_window_title()
            self._update_status_message()

        try:
            message_path = moved_path.relative_to(repo).as_posix()
        except ValueError:
            message_path = moved_path.as_posix()

        def finalize_move() -> None:
            self._refresh_recent_notes()
            self._sidebar.set_current_note_path(moved_path)
            self.statusBar().showMessage(f"Moved note to {message_path}", 4000)

        QTimer.singleShot(0, finalize_move)

    def _handle_notebook_move_requested(self, notebook: Path, target_dir: Path) -> None:
        repo = self._note_manager.get_repository_path()
        if repo is None:
            return
        try:
            repo_resolved = repo.resolve()
        except FileNotFoundError:
            repo_resolved = repo

        try:
            notebook_path = Path(notebook).resolve()
        except FileNotFoundError:
            notebook_path = Path(notebook)
        try:
            target_path = Path(target_dir).resolve()
        except FileNotFoundError:
            target_path = Path(target_dir)

        try:
            notebook_path.relative_to(repo_resolved)
            target_path.relative_to(repo_resolved)
        except ValueError:
            QMessageBox.warning(self, "Cannot Move Notebook", "Target notebook is outside the repository.")
            return

        if notebook_path == repo_resolved:
            QMessageBox.warning(self, "Cannot Move Notebook", "The repository root cannot be moved.")
            return
        if target_path == notebook_path or target_path == notebook_path.parent:
            return
        try:
            target_path.relative_to(notebook_path)
        except ValueError:
            pass
        else:
            QMessageBox.warning(self, "Cannot Move Notebook", "Cannot move a notebook into one of its descendants.")
            return

        old_notebook_path = notebook_path

        try:
            moved_path = self._note_manager.move_notebook(notebook_path, target_path)
        except (ValueError, FileExistsError, FileNotFoundError, NotADirectoryError, PermissionError, OSError) as error:
            QMessageBox.warning(self, "Cannot Move Notebook", str(error))
            self._refresh_recent_notes()
            return

        current_note = self._current_note
        if current_note is not None:
            try:
                current_resolved = current_note.resolve()
            except FileNotFoundError:
                current_resolved = current_note
            try:
                relative_note_path = current_resolved.relative_to(old_notebook_path)
            except ValueError:
                relative_note_path = None
            if relative_note_path is not None:
                new_note_path = moved_path / relative_note_path
                self._current_note = new_note_path
                self._update_window_title()
                self._update_status_message()

        try:
            message_path = moved_path.relative_to(repo_resolved).as_posix()
        except ValueError:
            message_path = moved_path.as_posix()

        def finalize_move() -> None:
            self._refresh_recent_notes()
            self._sidebar.set_current_notebook_path(moved_path)
            if self._current_note and moved_path in self._current_note.parents:
                self._sidebar.set_current_note_path(self._current_note)
            self.statusBar().showMessage(f"Moved notebook to {message_path}", 4000)

        QTimer.singleShot(0, finalize_move)

    def _load_note(self, note: Path) -> None:
        try:
            content = self._note_manager.load_note(note)
        except FileNotFoundError as error:
            QMessageBox.warning(self, "Missing Note", str(error))
            self._refresh_recent_notes()
            return
        blocker = QSignalBlocker(self._editor)
        self._editor.setPlainText(content)
        self._current_note = note
        self._editor.document().setModified(False)
        del blocker
        self._editor.refresh_line_numbers()
        self._refresh_recent_notes()
        self._sidebar.set_current_note_path(note)
        self._update_window_title()
        self._update_status_message()

    def _auto_save_current_note(self) -> bool:
        if not self._current_note:
            return True
        if not self._editor.document().isModified():
            return True
        try:
            saved_path = self._note_manager.save_note(self._current_note, self._editor.toPlainText())
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Auto-Save Failed", str(error))
            return False
        self._current_note = saved_path
        self._editor.document().setModified(False)
        self._update_window_title()
        self._update_status_message()
        self._refresh_recent_notes()
        return True

    def _create_new_note(self) -> None:
        name, ok = QInputDialog.getText(self, "New Note", "File name:", text="Untitled")
        if not ok:
            return
        cleaned = name.strip()
        if not cleaned:
            QMessageBox.warning(self, "Invalid Name", "File name cannot be empty.")
            return
        extension, ok = QInputDialog.getItem(
            self,
            "Note Format",
            "Choose a file format:",
            list(self._note_manager.SUPPORTED_EXTENSIONS),
            0,
            False,
        )
        if not ok:
            return
        if not self._auto_save_current_note():
            return
        color = QColorDialog.getColor(QColor(self._last_note_color), self, "Note Color")
        if not color.isValid():
            return
        color_hex = color.name(QColor.HexRgb).upper()
        container = self._sidebar.current_container_path()
        try:
            path = self._note_manager.create_note(
                cleaned,
                extension,
                directory=container,
                color=color_hex,
            )
        except (UnsupportedNoteExtensionError, ValueError, FileExistsError) as error:
            QMessageBox.warning(self, "Cannot Create Note", str(error))
            return
        self._last_note_color = color_hex
        self._load_note(path)
        self._editor.setFocus()

    def _rename_current_note(self) -> None:
        if not self._current_note:
            QMessageBox.information(self, "Rename Note", "No note is currently open.")
            return
        default_name = self._current_note.stem or self._current_note.name
        name, ok = QInputDialog.getText(self, "Rename Note", "File name:", text=default_name)
        if not ok:
            return
        cleaned = name.strip()
        if not cleaned:
            QMessageBox.warning(self, "Invalid Name", "File name cannot be empty.")
            return
        extensions = list(self._note_manager.SUPPORTED_EXTENSIONS)
        current_suffix = self._current_note.suffix.lower()
        try:
            default_index = extensions.index(current_suffix)
        except ValueError:
            default_index = 0
        extension, ok = QInputDialog.getItem(
            self,
            "Note Format",
            "Choose a file format:",
            extensions,
            default_index,
            False,
        )
        if not ok:
            return
        if not self._auto_save_current_note():
            return
        try:
            new_path = self._note_manager.rename_note(self._current_note, f"{cleaned}{extension}")
        except (UnsupportedNoteExtensionError, ValueError, FileExistsError, FileNotFoundError, IsADirectoryError) as error:
            QMessageBox.warning(self, "Cannot Rename Note", str(error))
            self._refresh_recent_notes()
            return
        self._current_note = new_path
        self._editor.document().setModified(False)
        self._refresh_recent_notes()
        self._sidebar.set_current_note_path(new_path)
        self._update_window_title()
        self._update_status_message()
        self._refresh_actions()
        self._editor.setFocus()

    def _open_repository(self) -> None:
        try:
            self._note_manager.open_repository()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Not Configured", str(error))
        except OSError as error:
            QMessageBox.critical(self, "Unable to Open Repository", str(error))

    def _update_window_title(self) -> None:
        title = "PixelPad"
        if self._current_note:
            title = f"PixelPad - {self._current_note.stem or self._current_note.name}"
        if self._editor.document().isModified():
            title += " *"
        self.setWindowTitle(title)

    def _update_status_message(self) -> None:
        parts = []
        repo = self._note_manager.get_repository_path()
        if repo:
            parts.append(f"Repository: {repo}")
        if self._current_note:
            parts.append(f"Current note: {self._current_note.name}")
        self.statusBar().showMessage(" | ".join(parts))

    def _delete_current_note(self) -> None:
        if not self._current_note:
            QMessageBox.information(self, "Delete Note", "No note is currently open.")
            return
        note_name = self._current_note.name
        confirm = QMessageBox.question(
            self,
            "Delete Note",
            f"Delete '{note_name}' permanently?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._note_manager.delete_note(self._current_note)
        except (FileNotFoundError, OSError, ValueError) as error:
            QMessageBox.critical(self, "Unable to Delete", str(error))
            self._refresh_recent_notes()
            return
        blocker = QSignalBlocker(self._editor)
        self._editor.clear()
        self._editor.document().setModified(False)
        del blocker
        self._editor.refresh_line_numbers()
        self._current_note = None
        self._refresh_recent_notes()
        self._update_window_title()
        self._update_status_message()
        self._refresh_actions()
        QTimer.singleShot(0, self._open_initial_note)
