from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from pixelpad.main_window import PixelPadMainWindow
from pixelpad.note_manager import NoteManager
from pixelpad.qss_styles import apply_theme


def _load_embedded_fonts() -> None:
    fonts_dir = Path(__file__).resolve().parent / "fonts"
    if not fonts_dir.exists() or not fonts_dir.is_dir():
        return
    for font_path in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font_path))
    for font_path in fonts_dir.glob("*.otf"):
        QFontDatabase.addApplicationFont(str(font_path))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PixelPad")
    app.setOrganizationName("PixelPad")
    _load_embedded_fonts()
    apply_theme(app, "dark")
    note_manager = NoteManager()
    window = PixelPadMainWindow(note_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
