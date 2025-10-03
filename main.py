from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pixelpad.main_window import PixelPadMainWindow
from pixelpad.note_manager import NoteManager
from pixelpad.qss_styles import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PixelPad")
    app.setOrganizationName("PixelPad")
    apply_theme(app, "dark")
    note_manager = NoteManager()
    window = PixelPadMainWindow(note_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
