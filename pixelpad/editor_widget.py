from __future__ import annotations

from PySide6.QtGui import QFont, QTextOption
from PySide6.QtWidgets import QPlainTextEdit


class EditorWidget(QPlainTextEdit):
    """Plain text editor tailored for PixelPad notes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        font = QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Start typing your note...")
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
