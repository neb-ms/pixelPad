from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from PySide6.QtCore import QItemSelectionModel, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SidebarWidget(QWidget):
    """Sidebar listing recent notes with a search filter."""

    note_selected = Signal(Path)
    open_repository_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._notes: List[Path] = []
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search notes...")
        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.itemClicked.connect(self._emit_selection)
        self._list.itemActivated.connect(self._emit_selection)
        self._search.textChanged.connect(self._apply_filter)

        self._open_button = QPushButton("Open Repository", self)
        self._open_button.clicked.connect(self.open_repository_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._open_button)

    def set_notes(self, notes: Iterable[Path]) -> None:
        self._notes = list(notes)
        self._rebuild_list()

    def set_current_note_path(self, note: Optional[Path]) -> None:
        if note is None:
            self._list.clearSelection()
            return
        for index in range(self._list.count()):
            item = self._list.item(index)
            data = item.data(Qt.UserRole)
            if data is None:
                continue
            item_path = Path(data)
            if item_path == note:
                self._list.setCurrentItem(item, QItemSelectionModel.ClearAndSelect)
                self._list.scrollToItem(item)
                break

    def current_note_path(self) -> Optional[Path]:
        item = self._list.currentItem()
        if not item:
            return None
        data = item.data(Qt.UserRole)
        if data is None:
            return None
        return Path(data)

    def _rebuild_list(self) -> None:
        selected = self.current_note_path()
        self._list.blockSignals(True)
        self._list.clear()
        for note in self._notes:
            item = QListWidgetItem(note.stem or note.name)
            item.setData(Qt.UserRole, str(note))
            self._list.addItem(item)
        self._list.blockSignals(False)
        if selected:
            self.set_current_note_path(selected)
        self._apply_filter(self._search.text())

    def _apply_filter(self, query: str) -> None:
        lowered = query.strip().lower()
        for index in range(self._list.count()):
            item = self._list.item(index)
            visible = True
            if lowered:
                visible = lowered in item.text().lower()
            item.setHidden(not visible)

    def _emit_selection(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if data is None:
            return
        self.note_selected.emit(Path(data))
