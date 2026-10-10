"""
Qt pieces shared by the import windows: config, language, window layout kept in the
Anki profile, the "Paste PGN" dialog and the board preview.
"""

from __future__ import annotations

import anki.lang
from aqt import mw
from aqt.qt import (
    QByteArray,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QMenu,
    QPlainTextEdit,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import restoreGeom, restoreHeader, saveGeom, saveHeader

from .chess_lib import chess
from .i18n import resolve_language, set_language, tr

try:  # Anki ships PyQt6 with the SVG module; without it there is no board preview
    from PyQt6.QtSvgWidgets import QSvgWidget
except ImportError:
    QSvgWidget = None


def get_config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def write_config(config: dict) -> None:
    mw.addonManager.writeConfig(__name__, config)


def apply_language() -> None:
    # "en" (default), "pt-BR", or "auto" to follow Anki's interface language
    setting = get_config().get("language")
    set_language(resolve_language(setting, getattr(anki.lang, "current_lang", None)))


def error_text(e: Exception) -> str:
    """Errors raised with an i18n key (Lichess, Chess.com, Stockfish), translated."""
    key = getattr(e, "key", None)
    if not key:
        return str(e)
    params = dict(getattr(e, "params", {}))
    if "hint" in params:
        params["hint"] = tr(params["hint"])
    return tr(key, **params)


# --- Window layout ---


def restore_layout(dialog: QDialog, table: QTableWidget, key: str, size: tuple[int, int]):
    """
    Maximize button, columns resized by dragging (the last one fills the width) and
    hidden or shown from the header's context menu; all kept from the last time.
    """
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
    restoreGeom(dialog, key, default_size=size)

    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(True)
    header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    header.customContextMenuRequested.connect(lambda pos: _column_menu(table, pos))
    restoreHeader(header, key)


def save_layout(dialog: QDialog, table: QTableWidget, key: str):
    saveGeom(dialog, key)
    saveHeader(table.horizontalHeader(), key)


def _column_menu(table: QTableWidget, pos):
    header = table.horizontalHeader()
    menu = QMenu(table)
    for col in range(1, table.columnCount()):  # the check column always stays
        action = menu.addAction(table.horizontalHeaderItem(col).text())
        action.setCheckable(True)
        action.setChecked(not header.isSectionHidden(col))
        action.toggled.connect(lambda shown, c=col: header.setSectionHidden(c, not shown))
    menu.exec(header.mapToGlobal(pos))


def readonly_item(text: str, tip: str = "") -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    if tip:
        item.setToolTip(tip)
    return item


# --- Dialogs and widgets ---


class PasteDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("cc.paste_title"))
        self.resize(640, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("cc.paste_label")))
        self.edit = QPlainTextEdit()
        layout.addWidget(self.edit, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("button.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def ask_pgn(parent) -> str:
    """PGN pasted by the user, or "" if cancelled."""
    dialog = PasteDialog(parent)
    return dialog.edit.toPlainText().strip() if dialog.exec() else ""


class BoardPreview(QWidget):
    """The board where you start playing a card, with a caption under it."""

    SIZE = 260

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 0, 0, 0)
        self.board = QSvgWidget() if QSvgWidget else None
        if self.board:
            self.board.setFixedSize(self.SIZE, self.SIZE)
            layout.addWidget(self.board, 0, Qt.AlignmentFlag.AlignHCenter)
        self.caption = QLabel(tr("preview.none"))
        self.caption.setWordWrap(True)
        self.caption.setMaximumWidth(self.SIZE + 20)
        self.caption.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.caption, 1)
        self.show_board(None)

    def show_board(
        self,
        board: chess.Board | None,
        white_below: bool = True,
        lastmove: chess.Move | None = None,
        caption: str = "",
    ):
        if self.board:
            svg = chess.svg.board(
                board if board is not None else chess.Board(None),
                orientation=chess.WHITE if white_below else chess.BLACK,
                lastmove=lastmove,
                size=self.SIZE,
            )
            self.board.load(QByteArray(svg.encode("utf-8")))
        self.caption.setText(caption or tr("preview.none"))
