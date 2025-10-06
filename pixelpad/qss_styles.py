"""Centralized Qt stylesheet definitions for PixelPad."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ThemePalette:
    """Palette configuration used to generate QSS and QPalette objects."""

    name: str
    background: str
    surface: str
    surface_alt: str
    border: str
    divider: str
    text: str
    text_muted: str
    accent: str
    accent_alt: str
    highlight: str
    highlight_text: str
    tree_selection_border: str


def _build_stylesheet(palette: ThemePalette) -> str:
    font_stack = "'Space Mono', 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace"
    return f"""
    * {{
        border-radius: 0px;
    }}

    QWidget {{
        background-color: {palette.background};
        color: {palette.text};
        selection-background-color: {palette.highlight};
        selection-color: {palette.highlight_text};
        font-family: {font_stack};
        font-size: 14px;
    }}

    QToolBar {{
        background-color: {palette.surface_alt};
        border-bottom: 2px solid {palette.border};
        padding: 4px;
        spacing: 4px;
    }}
    QToolBar QToolButton {{
        background-color: {palette.surface};
        border: 2px solid {palette.border};
        padding: 2px 6px;
        color: {palette.text};
        font-size: 12px;
        font-weight: 500;
        text-transform: none;
        letter-spacing: 0;
    }}
    QLabel#toolbarLogo {{
        background-color: transparent;
        border: none;
        padding: 0px;
        margin-right: 8px;
    }}
    QToolBar QToolButton:hover {{
        background-color: {palette.accent_alt};
        border-color: {palette.accent};
        color: {palette.highlight_text};
    }}
    QToolBar QToolButton:checked {{
        background-color: {palette.accent};
        color: {palette.highlight_text};
        border-color: {palette.accent_alt};
    }}

    QStatusBar {{
        background-color: {palette.surface_alt};
        border-top: 2px solid {palette.border};
    }}
    QStatusBar QLabel {{
        color: {palette.text_muted};
    }}

    QListWidget,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit {{
        background-color: {palette.surface};
        border: 2px solid {palette.border};
        color: {palette.text};
        selection-background-color: {palette.accent};
        selection-color: {palette.highlight_text};
        padding: 4px;
    }}

    QLineEdit {{
        selection-background-color: {palette.accent_alt};
    }}
    QLineEdit::placeholder {{
        color: {palette.text_muted};
    }}

    QTreeWidget#sidebarTree {{
        background-color: transparent;
        border: none;
    }}
    QTreeWidget#sidebarTree::item {{
        margin: 2px 6px 2px 2px;
        padding: 4px 6px;
        border: 2px solid transparent;
        border-radius: 4px;
        outline: none;
    }}
    QTreeWidget#sidebarTree::item:selected,
    QTreeWidget#sidebarTree::item:selected:active,
    QTreeWidget#sidebarTree::item:selected:!active {{
        background-color: transparent;
        border-color: {palette.tree_selection_border};
        color: {palette.text};
        outline: none;
    }}
    QTreeWidget#sidebarTree::item:hover {{
        border-color: {palette.tree_selection_border};
        background-color: rgba(255, 255, 255, 0.04);
        outline: none;
    }}
    QTreeWidget#sidebarTree::item:focus {{
        outline: none;
    }}

    QListWidget::item {{
        padding: 6px 8px;
    }}
    QListWidget::item:selected {{
        background-color: {palette.accent};
        color: {palette.highlight_text};
        border: 2px solid {palette.accent_alt};
    }}
    QListWidget::item:hover {{
        background-color: {palette.accent_alt};
        color: {palette.highlight_text};
    }}

    QPushButton {{
        background-color: {palette.surface_alt};
        border: 2px solid {palette.border};
        padding: 6px 10px;
        color: {palette.text};
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {palette.accent_alt};
        border-color: {palette.accent};
        color: {palette.highlight_text};
    }}
    QPushButton:pressed {{
        background-color: {palette.accent};
    }}

    QScrollBar:vertical {{
        background: {palette.surface_alt};
        width: 16px;
        margin: 0px;
        border: 2px solid {palette.border};
    }}
    QScrollBar::handle:vertical {{
        background: {palette.accent};
        min-height: 24px;
        border: 2px solid {palette.accent_alt};
    }}
    QScrollBar::handle:vertical:hover {{
        background: {palette.accent_alt};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        background: {palette.surface};
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {palette.surface_alt};
        height: 16px;
        margin: 0px;
        border: 2px solid {palette.border};
    }}
    QScrollBar::handle:horizontal {{
        background: {palette.accent};
        min-width: 24px;
        border: 2px solid {palette.accent_alt};
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {palette.accent_alt};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        background: {palette.surface};
        width: 0px;
    }}

    QSplitter::handle {{
        background-color: {palette.divider};
    }}

    QMenu {{
        background-color: {palette.surface};
        border: 2px solid {palette.border};
    }}
    QMenu::item:selected {{
        background-color: {palette.accent};
        color: {palette.highlight_text};
    }}
    QMenu::separator {{
        height: 2px;
        background: {palette.border};
        margin: 4px 0;
    }}

    QTabWidget::pane {{
        border: 2px solid {palette.border};
        background: {palette.surface};
    }}
    """.strip()


def _build_qpalette(palette: ThemePalette) -> QPalette:
    qpalette = QPalette()
    background = QColor(palette.background)
    surface = QColor(palette.surface)
    accent = QColor(palette.accent)
    text = QColor(palette.text)
    muted = QColor(palette.text_muted)
    highlight = QColor(palette.highlight)
    highlight_text = QColor(palette.highlight_text)

    qpalette.setColor(QPalette.Window, background)
    qpalette.setColor(QPalette.WindowText, text)
    qpalette.setColor(QPalette.Base, surface)
    qpalette.setColor(QPalette.AlternateBase, QColor(palette.surface_alt))
    qpalette.setColor(QPalette.ToolTipBase, surface)
    qpalette.setColor(QPalette.ToolTipText, text)
    qpalette.setColor(QPalette.Text, text)
    qpalette.setColor(QPalette.Button, QColor(palette.surface_alt))
    qpalette.setColor(QPalette.ButtonText, text)
    qpalette.setColor(QPalette.Highlight, highlight)
    qpalette.setColor(QPalette.HighlightedText, highlight_text)
    qpalette.setColor(QPalette.PlaceholderText, muted)
    qpalette.setColor(QPalette.Disabled, QPalette.Text, muted)

    return qpalette


THEMES: Dict[str, ThemePalette] = {
    "dark": ThemePalette(
        name="dark",
        background="#000000",
        surface="#000000",
        surface_alt="#000000",
        border="#000000",
        divider="#2a2a2a",
        text="#ccffd7",
        text_muted="#5c8b84",
        accent="#00ff90",
        accent_alt="#00cfff",
        highlight="#00ff90",
        highlight_text="#02110a",
        tree_selection_border="#2a2a2a",
    ),
    "light": ThemePalette(
        name="light",
        background="#f7fbff",
        surface="#edf3ff",
        surface_alt="#d8e4ff",
        border="#9bb2d1",
        divider="#9bb2d1",
        text="#0f1a28",
        text_muted="#4d5f78",
        accent="#1d8df0",
        accent_alt="#36d0c4",
        highlight="#1d8df0",
        highlight_text="#f4fbff",
        tree_selection_border="#7f8c8d",
    ),
}


def apply_theme(app: QApplication, theme_name: str) -> None:
    """Apply the named theme to the entire application."""

    try:
        palette = THEMES[theme_name]
    except KeyError as exc:
        raise ValueError(f"Unknown theme '{theme_name}'. Available: {', '.join(THEMES)}") from exc

    app.setPalette(_build_qpalette(palette))
    app.setStyleSheet(_build_stylesheet(palette))


def available_themes() -> Dict[str, ThemePalette]:
    """Return the registered themes keyed by identifier."""

    return THEMES.copy()
