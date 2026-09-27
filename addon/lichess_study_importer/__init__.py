"""
AnkiChess - Lichess Study Importer.
Creates one AnkiChess note per chapter of a Lichess study, and puzzle cards
from analysed Chess.com games.
"""

from aqt import gui_hooks, mw
from aqt.qt import QAction

from .chesscom_dialog import show_chesscom_dialog
from .dialog import apply_language, show_import_dialog
from .i18n import tr


def _find_ankichess_menu():
    # Menu created by the AnkiChess Companion add-on, if installed
    for action in mw.form.menubar.actions():
        if action.menu() and action.text().replace("&", "") == "AnkiChess":
            return action.menu()
    return None


def setup_menu():
    apply_language()
    actions = []
    for key, handler in (
        ("menu.import", show_import_dialog),
        ("menu.import_chesscom", show_chesscom_dialog),
    ):
        action = QAction(tr(key), mw)
        action.triggered.connect(handler)
        mw.form.menuTools.addAction(action)
        actions.append(action)

    chess_menu = _find_ankichess_menu()
    if chess_menu:
        chess_menu.addSeparator()
        for action in actions:
            chess_menu.addAction(action)


# Runs after all add-ons are loaded, so the Companion menu already exists
gui_hooks.main_window_did_init.append(setup_menu)
