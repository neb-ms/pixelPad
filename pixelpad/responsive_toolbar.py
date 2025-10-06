from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame,
    QLayout,
    QLayoutItem,
    QSizePolicy,
    QStyle,
    QToolButton,
    QWidget,
)


class FlowLayout(QLayout):
    """A layout that arranges child widgets like words on a page."""

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        h_spacing: int = 4,
        v_spacing: int = 4,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: D401 - Qt signature
        self._items.append(item)

    def count(self) -> int:  # noqa: D401 - Qt signature
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: D401 - Qt signature
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: D401 - Qt signature
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:  # noqa: D401 - Qt signature
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # noqa: D401 - Qt signature
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: D401 - Qt signature
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: D401 - Qt signature
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: D401 - Qt signature
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: D401 - Qt signature
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _horizontal_spacing(self) -> int:
        if self._h_spacing >= 0:
            return self._h_spacing
        return self._smart_spacing(QStyle.PM_LayoutHorizontalSpacing)

    def _vertical_spacing(self) -> int:
        if self._v_spacing >= 0:
            return self._v_spacing
        return self._smart_spacing(QStyle.PM_LayoutVerticalSpacing)

    def _smart_spacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if parent is None:
            return self.style().pixelMetric(pm)
        if isinstance(parent, QWidget):
            return parent.style().pixelMetric(pm, None, parent)
        return 0

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        space_x = self._horizontal_spacing()
        space_y = self._vertical_spacing()
        right_edge = effective_rect.right()

        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue

            hint = item.sizeHint()
            next_x = x + hint.width() + space_x
            if line_height > 0 and next_x - space_x > right_edge:
                x = effective_rect.x()
                y += line_height + space_y
                next_x = x + hint.width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            line_height = max(line_height, hint.height())

        total_height = y + line_height - rect.y() + top + bottom
        return total_height


class ResponsiveToolBar(QWidget):
    """Toolbar that wraps its actions into additional rows when space is limited."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("responsiveToolBar")
        self._layout = FlowLayout(self, margin=4, h_spacing=4, v_spacing=4)
        self._buttons: Dict[QAction, QToolButton] = {}
        self._tool_button_style = Qt.ToolButtonTextOnly
        self._icon_size = QSize(16, 16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def addAction(self, action: QAction) -> QAction:  # noqa: D401 - signature parity
        button = QToolButton(self)
        button.setDefaultAction(action)
        button.setToolButtonStyle(self._tool_button_style)
        button.setIconSize(self._icon_size)
        button.setFocusPolicy(Qt.NoFocus)
        button.setAutoRaise(False)
        self._layout.addWidget(button)
        self._buttons[action] = button
        return action

    def addWidget(self, widget: QWidget) -> QWidget:  # noqa: D401 - signature parity
        widget.setParent(self)
        self._layout.addWidget(widget)
        return widget

    def addSeparator(self) -> None:  # noqa: D401 - signature parity
        separator = QFrame(self)
        separator.setObjectName("toolbarSeparator")
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(1)
        separator.setMidLineWidth(0)
        separator.setFixedSize(2, 28)
        self._layout.addWidget(separator)

    def setToolButtonStyle(self, style: Qt.ToolButtonStyle) -> None:  # noqa: D401
        self._tool_button_style = style
        for button in self._buttons.values():
            button.setToolButtonStyle(style)

    def setIconSize(self, size: QSize) -> None:  # noqa: D401
        self._icon_size = QSize(size)
        for button in self._buttons.values():
            button.setIconSize(size)

    def iconSize(self) -> QSize:  # noqa: D401 - Qt signature
        return QSize(self._icon_size)

    def actions(self) -> list[QAction]:  # noqa: D401 - Qt compatibility
        return list(self._buttons.keys())

    def sizeHint(self) -> QSize:  # noqa: D401 - Qt signature
        return self._layout.sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: D401 - Qt signature
        return self._layout.minimumSize()
