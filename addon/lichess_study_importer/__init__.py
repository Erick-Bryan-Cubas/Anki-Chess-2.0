"""
AnkiChess - Lichess Study Importer.
Creates one AnkiChess note per chapter of a Lichess study.
"""

from aqt import gui_hooks, mw
from aqt.qt import QAction

from .dialog import show_import_dialog

ACTION_TEXT = "Importar estudo do Lichess..."


def _find_ankichess_menu():
    # Menu created by the AnkiChess Companion add-on, if installed
    for action in mw.form.menubar.actions():
        if action.menu() and action.text().replace("&", "") == "AnkiChess":
            return action.menu()
    return None


def setup_menu():
    action = QAction(ACTION_TEXT, mw)
    action.triggered.connect(show_import_dialog)
    mw.form.menuTools.addAction(action)

    chess_menu = _find_ankichess_menu()
    if chess_menu:
        chess_menu.addSeparator()
        chess_menu.addAction(action)


# Runs after all add-ons are loaded, so the Companion menu already exists
gui_hooks.main_window_did_init.append(setup_menu)
