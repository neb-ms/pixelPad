from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from pixelpad.main_window import PixelPadMainWindow, find_logo_path
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
    logo_path = find_logo_path()
    if logo_path is not None:
        app.setWindowIcon(QIcon(str(logo_path)))
    note_manager = NoteManager()
    apply_theme(app, note_manager.get_theme())
    window = PixelPadMainWindow(note_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
