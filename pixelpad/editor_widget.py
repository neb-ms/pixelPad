from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QPainter, QTextFormat, QTextOption
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


class EditorWidget(QPlainTextEdit):
    """Plain text editor tailored for PixelPad notes."""

    class _LineNumberArea(QWidget):
        def __init__(self, editor: "EditorWidget") -> None:
            super().__init__(editor)
            self._editor = editor

        def sizeHint(self) -> QSize:  # type: ignore[override]
            return QSize(self._editor._line_number_area_width(), 0)

        def paintEvent(self, event) -> None:  # noqa: N802 ANN001
            self._editor._paint_line_number_area(event)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        font = QFont("Space Mono")
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Start typing your note...")
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))

        self._line_numbers_visible = True
        self._line_number_area = self._LineNumberArea(self)
        self._line_number_area.show()

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)  # type: ignore[arg-type]
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_numbers_visible(self) -> bool:
        return self._line_numbers_visible

    def set_line_numbers_visible(self, visible: bool) -> None:
        self._line_numbers_visible = bool(visible)
        self._line_number_area.setVisible(self._line_numbers_visible)
        self.refresh_line_numbers()

    def refresh_line_numbers(self) -> None:
        self._update_line_number_area_width(0)
        self._line_number_area.update()
        self._highlight_current_line()

    # ------------------------------------------------------------------
    # Qt event overrides
    def resizeEvent(self, event) -> None:  # noqa: N802 ANN001
        super().resizeEvent(event)
        if not self._line_numbers_visible:
            self._line_number_area.setGeometry(QRect())
            return
        rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(rect.left(), rect.top(), self._line_number_area_width(), rect.height())
        )

    # ------------------------------------------------------------------
    # Line number helpers
    def _line_number_area_width(self) -> int:
        if not self._line_numbers_visible:
            return 0
        digits = len(str(max(1, self.blockCount())))
        padding = 6
        return padding + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _: int) -> None:
        width = self._line_number_area_width()
        self.setViewportMargins(width, 0, 0, 0)

    def _update_line_number_area(self, rect, dy) -> None:  # noqa: ANN001
        if not self._line_numbers_visible:
            return
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def _paint_line_number_area(self, event) -> None:  # noqa: ANN001
        if not self._line_numbers_visible:
            return
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self.palette().alternateBase())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.palette().color(self.foregroundRole()))
                painter.drawText(
                    0,
                    int(top),
                    self._line_number_area.width() - 4,
                    int(self.fontMetrics().height()),
                    Qt.AlignRight | Qt.AlignVCenter,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def _highlight_current_line(self) -> None:
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(self.palette().alternateBase())
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
