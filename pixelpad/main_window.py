from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from .editor_widget import EditorWidget
from .note_manager import (
    NoteManager,
    NotesRepositoryNotConfiguredError,
    UnsupportedNoteExtensionError,
)
from .sidebar_widget import SidebarWidget


class PixelPadMainWindow(QMainWindow):
    """Main window connecting the NoteManager with the GUI widgets."""

    def __init__(self, note_manager: NoteManager) -> None:
        super().__init__()
        self._note_manager = note_manager
        self._current_note: Optional[Path] = None

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

        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
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
        self._line_numbers_action = QAction("Line Numbers", self)
        self._line_numbers_action.setCheckable(True)
        self._line_numbers_action.setChecked(True)
        toolbar.addAction(self._line_numbers_action)

        self._sidebar.note_selected.connect(self._handle_note_selected)
        self._sidebar.open_repository_requested.connect(self._open_repository)
        self._new_note_action.triggered.connect(self._create_new_note)
        self._rename_note_action.triggered.connect(self._rename_current_note)
        self._delete_note_action.triggered.connect(self._delete_current_note)
        self._line_numbers_action.toggled.connect(self._toggle_line_numbers)
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
                self._note_manager.require_repository()
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
                self._note_manager.set_repository_path(selected)
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
            notes = self._note_manager.get_recent_notes()
        except NotesRepositoryNotConfiguredError as error:
            QMessageBox.warning(self, "Repository Error", str(error))
            if self._ensure_repository_configured():
                self._refresh_recent_notes()
            return
        self._sidebar.set_notes(notes)
        if self._current_note:
            self._sidebar.set_current_note_path(self._current_note)
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        has_note = self._current_note is not None
        self._delete_note_action.setEnabled(has_note)
        self._rename_note_action.setEnabled(has_note)
        blocker = QSignalBlocker(self._line_numbers_action)
        self._line_numbers_action.setChecked(self._editor.line_numbers_visible())
        del blocker

    def _toggle_line_numbers(self, checked: bool) -> None:
        self._editor.set_line_numbers_visible(checked)

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
        try:
            path = self._note_manager.create_note(cleaned, extension)
        except (UnsupportedNoteExtensionError, ValueError, FileExistsError) as error:
            QMessageBox.warning(self, "Cannot Create Note", str(error))
            return
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
