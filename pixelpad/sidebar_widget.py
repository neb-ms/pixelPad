from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

from PySide6.QtCore import QItemSelectionModel, QMimeData, QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPalette, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QPushButton,
    QStyledItemDelegate,
    QStyle,
    QProxyStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QStyleOptionViewItem,
)



class _SidebarTreeWidget(QTreeWidget):
    """Tree widget with drag-and-drop support for moving notes and notebooks."""

    note_drop_requested = Signal(Path, Path)
    notebook_drop_requested = Signal(Path, Path)
    _NOTE_MIME_TYPE = "application/x-pixelpad-note"
    _NOTEBOOK_MIME_TYPE = "application/x-pixelpad-notebook"

    def __init__(self, owner: "SidebarWidget") -> None:
        super().__init__(owner)
        self._owner = owner
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)

    def supportedDropActions(self) -> Qt.DropActions:  # noqa: D401 - Qt override
        return Qt.MoveAction

    def mimeData(self, items: List[QTreeWidgetItem]) -> Optional[QMimeData]:  # type: ignore[override]
        if not items:
            return None
        item = items[0]
        item_type = item.data(0, self._owner.TYPE_ROLE)
        if item_type not in {"note", "folder"}:
            return None
        if item_type == "folder" and item is self._owner._root_item:
            return None
        data = item.data(0, self._owner.NOTE_ROLE)
        if data is None:
            return None
        mime = super().mimeData(items)
        if mime is None:
            mime = QMimeData()
        if item_type == "note":
            mime.setData(self._NOTE_MIME_TYPE, str(data).encode("utf-8"))
        else:
            mime.setData(self._NOTEBOOK_MIME_TYPE, str(data).encode("utf-8"))
        return mime

    def mimeTypes(self) -> List[str]:  # type: ignore[override]
        types = super().mimeTypes()
        if self._NOTE_MIME_TYPE not in types:
            types.append(self._NOTE_MIME_TYPE)
        if self._NOTEBOOK_MIME_TYPE not in types:
            types.append(self._NOTEBOOK_MIME_TYPE)
        return types

    def dragEnterEvent(self, event):  # noqa: N802 (Qt API)
        if self._can_accept_event(event):
            event.setDropAction(Qt.MoveAction)
            super().dragEnterEvent(event)
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)
        event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802 (Qt API)
        if self._can_accept_event(event):
            event.setDropAction(Qt.MoveAction)
            super().dragMoveEvent(event)
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)
        event.ignore()

    def dropEvent(self, event):  # noqa: N802 (Qt API)
        mime = event.mimeData()
        note_path = self._note_path_from_mime(mime)
        target_dir = self._target_directory_for_event(event)
        if note_path is not None:
            if target_dir is None or note_path.parent == target_dir:
                event.ignore()
                return
            event.setDropAction(Qt.MoveAction)
            self.note_drop_requested.emit(note_path, target_dir)
            event.acceptProposedAction()
            return

        notebook_path = self._notebook_path_from_mime(mime)
        if notebook_path is not None:
            if target_dir is None or not self._is_valid_notebook_drop(notebook_path, target_dir):
                event.ignore()
                return
            event.setDropAction(Qt.MoveAction)
            self.notebook_drop_requested.emit(notebook_path, target_dir)
            event.acceptProposedAction()
            return

        event.ignore()

    def _can_accept_event(self, event) -> bool:
        mime = event.mimeData()
        if not mime:
            return False
        target_dir = self._target_directory_for_event(event)
        if target_dir is None:
            return False
        note_path = self._note_path_from_mime(mime)
        if note_path is not None:
            return True
        notebook_path = self._notebook_path_from_mime(mime)
        if notebook_path is not None:
            return True
        return False

    def _event_position(self, event) -> QPoint:
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def _target_directory_for_event(self, event) -> Optional[Path]:
        pos = self._event_position(event)
        item = self.itemAt(pos)
        if item is None:
            item = self._owner._root_item
            if item is None:
                return None
        position = self.dropIndicatorPosition()
        if position in {QAbstractItemView.AboveItem, QAbstractItemView.BelowItem}:
            item_type = item.data(0, self._owner.TYPE_ROLE)
            if item_type not in {"folder", "root"}:
                parent = item.parent()
                if parent is not None:
                    item = parent
                else:
                    item = self._owner._root_item
                    if item is None:
                        return None
        elif position == QAbstractItemView.OnViewport:
            item = self._owner._root_item
            if item is None:
                return None
        item_type = item.data(0, self._owner.TYPE_ROLE)
        data = item.data(0, self._owner.NOTE_ROLE)
        if data is None:
            return None
        if item_type in {"folder", "root"}:
            return Path(str(data))
        if item_type == "note":
            return Path(str(data)).parent
        return None

    def _note_path_from_mime(self, mime: QMimeData) -> Optional[Path]:
        if not mime.hasFormat(self._NOTE_MIME_TYPE):
            return None
        payload = bytes(mime.data(self._NOTE_MIME_TYPE)).decode("utf-8")
        path = Path(payload)
        try:
            return path.resolve()
        except FileNotFoundError:
            return path

    def _notebook_path_from_mime(self, mime: QMimeData) -> Optional[Path]:
        if not mime.hasFormat(self._NOTEBOOK_MIME_TYPE):
            return None
        payload = bytes(mime.data(self._NOTEBOOK_MIME_TYPE)).decode("utf-8")
        path = Path(payload)
        try:
            return path.resolve()
        except FileNotFoundError:
            return path

    def _is_valid_notebook_drop(self, notebook_path: Path, target_dir: Path) -> bool:
        try:
            notebook_resolved = notebook_path.resolve()
        except FileNotFoundError:
            notebook_resolved = notebook_path
        try:
            target_resolved = target_dir.resolve()
        except FileNotFoundError:
            target_resolved = target_dir
        if notebook_resolved == target_resolved:
            return False
        if notebook_resolved.parent == target_resolved:
            return False
        repo_candidate = self._owner._repo_path
        if repo_candidate is not None:
            try:
                repo_candidate = repo_candidate.resolve()
            except FileNotFoundError:
                pass
        if repo_candidate and notebook_resolved == repo_candidate:
            return False
        try:
            target_resolved.relative_to(notebook_resolved)
        except ValueError:
            return True
        return False


class _SidebarTreeDelegate(QStyledItemDelegate):
    '''Custom delegate that suppresses the dotted focus rectangle.'''

    def paint(self, painter, option, index):
        clean_option = QStyleOptionViewItem(option)
        clean_option.state &= ~QStyle.State_HasFocus
        super().paint(painter, clean_option, index)


class _SidebarTreeStyle(QProxyStyle):
    """Draw expand/collapse indicators with themed chevron strokes."""

    def drawPrimitive(self, element, option, painter, widget=None):  # noqa: N802 (Qt API)
        if element == QStyle.PE_IndicatorBranch and widget and widget.objectName() == "sidebarTree":
            if not (option.state & QStyle.State_Children):
                super().drawPrimitive(element, option, painter, widget)
                return

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)

            rect = option.rect
            palette = widget.palette()
            color = palette.color(QPalette.Text)
            if option.state & QStyle.State_MouseOver:
                color = palette.color(QPalette.Highlight)

            pen = QPen(color)
            pen.setWidthF(1.1)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            center = rect.center()
            size = float(min(rect.width(), rect.height()))
            primary = size * 0.28
            secondary = primary * 0.7

            if option.state & QStyle.State_Open:
                points = [
                    QPointF(center.x() - primary, center.y() - secondary),
                    QPointF(center.x(), center.y() + primary),
                    QPointF(center.x() + primary, center.y() - secondary),
                ]
            else:
                points = [
                    QPointF(center.x() - secondary, center.y() - primary),
                    QPointF(center.x() + primary, center.y()),
                    QPointF(center.x() - secondary, center.y() + primary),
                ]
            painter.drawPolyline(QPolygonF(points))
            painter.restore()
            return

        super().drawPrimitive(element, option, painter, widget)


class SidebarWidget(QWidget):
    """Sidebar listing notes and notebooks with search-driven filtering."""

    note_selected = Signal(Path)
    note_move_requested = Signal(Path, Path)
    notebook_move_requested = Signal(Path, Path)
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
        self._note_colors: Dict[Path, str] = {}
        self._notebook_colors: Dict[Path, str] = {}
        self._icon_cache: Dict[Tuple[str, int], QIcon] = {}
        self._default_note_color = "#5E9CFF"
        self._default_notebook_color = "#FFB74D"
        self._root_color = "#90A4AE"
        self._note_dot_size = 10
        self._notebook_dot_size = 14
        self._root_dot_size = 16

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search notes or notebooks...")
        self._tree = _SidebarTreeWidget(self)
        self._tree.setObjectName("sidebarTree")
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        self._tree.setItemDelegate(_SidebarTreeDelegate(self._tree))
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setStyle(_SidebarTreeStyle(self._tree.style()))
        self._tree.itemClicked.connect(self._emit_selection)
        self._tree.itemActivated.connect(self._handle_item_activation)
        self._tree.itemSelectionChanged.connect(self.selection_changed)
        self._search.textChanged.connect(self._apply_filter)
        self._tree.note_drop_requested.connect(self._handle_note_drop_request)
        self._tree.notebook_drop_requested.connect(self._handle_notebook_drop_request)

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

    def set_content(
        self,
        *,
        notes: Iterable[Path],
        notebooks: Iterable[Path],
        note_colors: Optional[Mapping[Path, str]] = None,
        notebook_colors: Optional[Mapping[Path, str]] = None,
    ) -> None:
        note_set = {path.resolve() for path in notes}
        notebook_set = {path.resolve() for path in notebooks}
        self._note_colors = self._build_color_map(note_colors, note_set, self._default_note_color)
        self._notebook_colors = self._build_color_map(
            notebook_colors,
            notebook_set,
            self._default_notebook_color,
        )
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

    def _build_color_map(
        self,
        colors: Optional[Mapping[Path, str]],
        allowed: Set[Path],
        fallback: str,
    ) -> Dict[Path, str]:
        if not colors:
            return {}
        mapping: Dict[Path, str] = {}
        for raw_path, color in colors.items():
            path = Path(raw_path).resolve()
            if path not in allowed:
                continue
            normalized = self._normalize_color_value(color, fallback)
            mapping[path] = normalized
        return mapping

    def _normalize_color_value(self, color: str, fallback: str) -> str:
        candidate = QColor(color)
        if not candidate.isValid():
            candidate = QColor(fallback)
        return candidate.name(QColor.HexRgb).upper()

    def _color_for_notebook(self, path: Path) -> str:
        resolved = path.resolve()
        return self._notebook_colors.get(resolved, self._default_notebook_color)

    def _color_for_note(self, path: Path) -> str:
        resolved = path.resolve()
        return self._note_colors.get(resolved, self._default_note_color)

    def _dot_icon(self, color: str, size: int, fallback: str) -> QIcon:
        normalized = self._normalize_color_value(color, fallback)
        cache_key = (normalized, size)
        icon = self._icon_cache.get(cache_key)
        if icon is not None:
            return icon
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.Antialiasing, False)
        fill = QColor(normalized)
        border = QColor(fill)
        border = border.darker(140)
        painter.setPen(border)
        painter.setBrush(fill)
        painter.drawRect(0, 0, size - 1, size - 1)
        painter.end()
        icon = QIcon(pixmap)
        self._icon_cache[cache_key] = icon
        return icon


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
        repo_item.setIcon(0, self._dot_icon(self._root_color, self._root_dot_size, self._root_color))
        repo_item.setFlags((repo_item.flags() | Qt.ItemIsDropEnabled) & ~Qt.ItemIsDragEnabled)
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
            item.setIcon(0, self._dot_icon(self._color_for_note(note), self._note_dot_size, self._default_note_color))
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled)
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
        item.setIcon(0, self._dot_icon(self._color_for_notebook(folder_path), self._notebook_dot_size, self._default_notebook_color))
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
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

    def _handle_note_drop_request(self, note_path: Path, target_dir: Path) -> None:
        repo = self._repo_path
        if repo is None:
            return
        repo = repo.resolve()
        try:
            note_path = Path(note_path).resolve()
        except FileNotFoundError:
            note_path = Path(note_path)
        try:
            target_dir = Path(target_dir).resolve()
        except FileNotFoundError:
            target_dir = Path(target_dir)
        try:
            note_path.relative_to(repo)
            target_dir.relative_to(repo)
        except ValueError:
            return
        if note_path.parent == target_dir:
            return
        self.note_move_requested.emit(note_path, target_dir)

    def _handle_notebook_drop_request(self, notebook_path: Path, target_dir: Path) -> None:
        repo = self._repo_path
        if repo is None:
            return
        repo = repo.resolve()
        try:
            notebook_path = Path(notebook_path).resolve()
        except FileNotFoundError:
            notebook_path = Path(notebook_path)
        try:
            target_dir = Path(target_dir).resolve()
        except FileNotFoundError:
            target_dir = Path(target_dir)
        try:
            notebook_path.relative_to(repo)
            target_dir.relative_to(repo)
        except ValueError:
            return
        if notebook_path == repo:
            return
        if target_dir == notebook_path or target_dir == notebook_path.parent:
            return
        try:
            target_dir.relative_to(notebook_path)
        except ValueError:
            self.notebook_move_requested.emit(notebook_path, target_dir)
            return
        # target is inside the notebook being moved; ignore
        return

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
