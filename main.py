from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from pixelpad.note_manager import NoteManager, NotesRepositoryNotConfiguredError


class PixelPadWindow(QMainWindow):
    """Minimal shell window used during early development phases."""

    def __init__(self, notes: NoteManager) -> None:
        super().__init__()
        self._notes = notes
        self.setWindowTitle("PixelPad")
        self.resize(960, 600)
        self._sync_status_bar()

    def _sync_status_bar(self) -> None:
        status_bar = self.statusBar()
        try:
            repo = self._notes.get_repository_path()
            message = f"Repository: {repo}" if repo else "Repository not configured"
        except NotesRepositoryNotConfiguredError as error:
            message = str(error)
        status_bar.showMessage(message)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PixelPad")
    app.setOrganizationName("PixelPad")
    note_manager = NoteManager()
    window = PixelPadWindow(note_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
