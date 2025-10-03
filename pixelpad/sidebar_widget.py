from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from PySide6.QtCore import QItemSelectionModel, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QPushButton,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SidebarWidget(QWidget):
    """Sidebar listing notes and notebooks with search-driven filtering."""

    note_selected = Signal(Path)
    open_repository_requested = Signal()
    change_repository_requested = Signal()
    selection_changed = Signal()

    NOTE_ROLE = Qt.UserRole
    TYPE_ROLE = Qt.UserRole + 1

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo_path: Optional[Path] = None
        self._notes: List[Path] = []
        self._notebooks: List[Path] = []
        self._folder_items: Dict[Path, QTreeWidgetItem] = {}
        self._note_items: Dict[Path, QTreeWidgetItem] = {}
        self._root_item: Optional[QTreeWidgetItem] = None

        style = self.style()
        self._root_icon = style.standardIcon(QStyle.SP_DriveHDIcon)
        self._folder_icon = style.standardIcon(QStyle.SP_DirIcon)
        self._note_icon = style.standardIcon(QStyle.SP_FileIcon)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search notes or notebooks...")
        self._tree = QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._emit_selection)
        self._tree.itemActivated.connect(self._handle_item_activation)
        self._tree.itemSelectionChanged.connect(self.selection_changed)
        self._search.textChanged.connect(self._apply_filter)

        self._open_button = QPushButton("Open Repository", self)
        self._open_button.clicked.connect(self.open_repository_requested)
        self._change_repo_button = QPushButton("Change Repository", self)
        self._change_repo_button.clicked.connect(self.change_repository_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._search)
        layout.addWidget(self._tree, 1)
        layout.addWidget(self._open_button)
        layout.addWidget(self._change_repo_button)
    # ------------------------------------------------------------------
    # Public API methods ------------------------------------------------
    def set_repository_path(self, repo: Optional[Path]) -> None:
        self._repo_path = repo.resolve() if repo else None
        self._rebuild_tree()

    def set_content(self, *, notes: Iterable[Path], notebooks: Iterable[Path]) -> None:
        note_set = {path.resolve() for path in notes}
        notebook_set = {path.resolve() for path in notebooks}
        self._notes = sorted(note_set, key=lambda path: path.as_posix())
        self._notebooks = sorted(notebook_set, key=lambda path: path.as_posix())
        self._rebuild_tree()

    def set_current_note_path(self, note: Optional[Path]) -> None:
        if note is None:
            self._tree.clearSelection()
            return
        target = self._note_items.get(note.resolve())
        if not target:
            return
        self._expand_ancestors(target)
        self._tree.setCurrentItem(target, 0, QItemSelectionModel.ClearAndSelect)

    def set_current_notebook_path(self, notebook: Optional[Path]) -> None:
        if notebook is None:
            return
        repo = self._repo_path.resolve() if self._repo_path else None
        target_path = notebook.resolve()
        if repo and target_path == repo:
            self.select_repository_root()
            return
        target = self._folder_items.get(target_path)
        if not target:
            return
        self._expand_ancestors(target)
        self._tree.setCurrentItem(target, 0, QItemSelectionModel.ClearAndSelect)

    def select_repository_root(self) -> None:
        if not self._root_item:
            return
        self._expand_ancestors(self._root_item)
        self._tree.setCurrentItem(self._root_item, 0, QItemSelectionModel.ClearAndSelect)
        self._tree.scrollToItem(self._root_item)

    def current_notebook_path(self) -> Optional[Path]:
        item = self._tree.currentItem()
        if not item:
            return None
        if item.data(0, self.TYPE_ROLE) != "folder":
            return None
        data = item.data(0, self.NOTE_ROLE)
        if data is None:
            return None
        return Path(data)

    def current_note_path(self) -> Optional[Path]:
        item = self._tree.currentItem()
        if not item or item.data(0, self.TYPE_ROLE) != "note":
            return None
        data = item.data(0, self.NOTE_ROLE)
        if data is None:
            return None
        return Path(data)

    def current_container_path(self) -> Optional[Path]:
        item = self._tree.currentItem()
        if not item:
            return self._repo_path
        item_type = item.data(0, self.TYPE_ROLE)
        if item_type == "folder":
            data = item.data(0, self.NOTE_ROLE)
            return Path(data) if data else None
        if item_type == "root":
            return self._repo_path
        note_path = self.current_note_path()
        if note_path:
            return note_path.parent
        return self._repo_path

    def focus_search(self) -> None:
        self._search.setFocus(Qt.ShortcutFocusReason)
        self._search.selectAll()

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    def _rebuild_tree(self) -> None:
        repo = self._repo_path
        self._tree.blockSignals(True)
        expanded = self._capture_expanded_paths()
        selected = self._capture_selection()
        self._tree.clear()
        self._folder_items.clear()
        self._note_items.clear()
        self._root_item = None

        if repo is None:
            self._tree.blockSignals(False)
            return

        root = self._tree.invisibleRootItem()
        repo_label = repo.name or repo.as_posix()
        repo_item = QTreeWidgetItem(root, [repo_label])
        repo_item.setData(0, self.NOTE_ROLE, str(repo))
        repo_item.setData(0, self.TYPE_ROLE, "root")
        repo_item.setToolTip(0, str(repo))
        repo_item.setIcon(0, self._root_icon)
        repo_item.setExpanded(True)
        self._root_item = repo_item
        self._folder_items[repo] = repo_item

        for folder in self._notebooks:
            try:
                relative_parts = folder.relative_to(repo).parts
            except ValueError:
                continue
            current_item = self._root_item
            current_path = repo
            for part in relative_parts:
                current_path = current_path / part
                if current_item is None:
                    break
                current_item = self._ensure_folder_item(current_item, current_path)

        for note in self._notes:
            try:
                relative = note.relative_to(repo)
            except ValueError:
                continue
            parent_item = self._root_item
            current_path = repo
            for part in relative.parts[:-1]:
                current_path = current_path / part
                if parent_item is None:
                    break
                parent_item = self._ensure_folder_item(parent_item, current_path)
            if parent_item is None:
                continue
            item = QTreeWidgetItem(parent_item, [note.name])
            item.setData(0, self.NOTE_ROLE, str(note))
            item.setData(0, self.TYPE_ROLE, "note")
            item.setToolTip(0, note.name)
            item.setIcon(0, self._note_icon)
            self._note_items[note] = item

        if self._root_item:
            self._sort_children(self._root_item)

        self._restore_expanded_paths(expanded)
        self._restore_selection(selected)
        if not self._tree.currentItem() and self._root_item:
            self._tree.setCurrentItem(self._root_item, 0, QItemSelectionModel.ClearAndSelect)
        self._tree.blockSignals(False)
        self._apply_filter(self._search.text())
        if self._root_item:
            self._root_item.setExpanded(True)

    def _ensure_folder_item(self, parent: QTreeWidgetItem, folder_path: Path) -> QTreeWidgetItem:
        repo = self._repo_path
        if repo is None or parent is None:
            return parent
        folder_path = folder_path.resolve()
        if folder_path == repo:
            return self._root_item or parent
        existing = self._folder_items.get(folder_path)
        if existing:
            return existing
        try:
            relative = folder_path.relative_to(repo)
        except ValueError:
            return parent
        item = QTreeWidgetItem(parent, [relative.name])
        item.setData(0, self.NOTE_ROLE, str(folder_path))
        item.setData(0, self.TYPE_ROLE, "folder")
        item.setToolTip(0, relative.as_posix())
        item.setIcon(0, self._folder_icon)
        self._folder_items[folder_path] = item
        return item

    def _handle_item_activation(self, item: QTreeWidgetItem) -> None:
        item_type = item.data(0, self.TYPE_ROLE)
        if item_type in {"folder", "root"}:
            item.setExpanded(not item.isExpanded())
        else:
            self._emit_selection(item)

    def _emit_selection(self, item: QTreeWidgetItem) -> None:
        if item.data(0, self.TYPE_ROLE) != "note":
            return
        data = item.data(0, self.NOTE_ROLE)
        if data is None:
            return
        self.note_selected.emit(Path(data))

    def _apply_filter(self, query: str) -> None:
        lowered = query.strip().lower()
        self._tree.setUpdatesEnabled(False)

        def filter_item(item: QTreeWidgetItem) -> bool:
            item_type = item.data(0, self.TYPE_ROLE)
            match = not lowered or lowered in item.text(0).lower()
            child_match = False
            for index in range(item.childCount()):
                child = item.child(index)
                if filter_item(child):
                    child_match = True
            if item_type == "root":
                item.setHidden(False)
                item.setExpanded(True)
                return True
            visible = match or child_match
            item.setHidden(not visible)
            if item_type == "folder" and lowered and visible:
                item.setExpanded(True)
            return visible

        if self._root_item:
            filter_item(self._root_item)

        self._tree.setUpdatesEnabled(True)

    def _capture_selection(self) -> Optional[Tuple[str, str]]:
        item = self._tree.currentItem()
        if not item:
            return None
        data = item.data(0, self.NOTE_ROLE)
        kind = item.data(0, self.TYPE_ROLE)
        if data is None or kind is None:
            return None
        return str(data), str(kind)

    def _capture_expanded_paths(self) -> Set[str]:
        expanded: Set[str] = set()

        def collect(item: QTreeWidgetItem) -> None:
            item_type = item.data(0, self.TYPE_ROLE)
            data = item.data(0, self.NOTE_ROLE)
            if item_type in {"folder", "root"} and item.isExpanded() and data is not None:
                expanded.add(str(data))
            for index in range(item.childCount()):
                collect(item.child(index))

        if self._root_item:
            collect(self._root_item)
        return expanded

    def _restore_selection(self, selection: Optional[Tuple[str, str]]) -> None:
        if not selection:
            return
        path_str, kind = selection
        if kind == "root" and self._root_item:
            target = self._root_item
        else:
            path = Path(path_str).resolve()
            if kind == "note":
                target = self._note_items.get(path)
            else:
                target = self._folder_items.get(path)
        if not target:
            return
        self._expand_ancestors(target)
        self._tree.setCurrentItem(target, 0, QItemSelectionModel.ClearAndSelect)

    def _restore_expanded_paths(self, expanded: Set[str]) -> None:
        for path_str in expanded:
            path = Path(path_str)
            if self._repo_path and path.resolve() == self._repo_path.resolve():
                target = self._root_item
            else:
                target = self._folder_items.get(path.resolve())
            if not target:
                continue
            self._expand_ancestors(target)
            target.setExpanded(True)

    @staticmethod
    def _expand_ancestors(item: QTreeWidgetItem) -> None:
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    def _sort_children(self, item: QTreeWidgetItem) -> None:
        if item is None:
            return
        children: List[QTreeWidgetItem] = [item.takeChild(0) for _ in range(item.childCount())]
        children.sort(
            key=lambda child: (
                0 if child.data(0, self.TYPE_ROLE) in {"folder", "root"} else 1,
                child.text(0).lower(),
            )
        )
        for child in children:
            item.addChild(child)
            self._sort_children(child)
