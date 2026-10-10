"""
AnkiChess - Lichess Study Importer.
Creates one AnkiChess note per chapter of a Lichess study, puzzle cards from analysed
Chess.com and Lichess games, and cards from Lichess puzzles.
"""

from aqt import gui_hooks, mw
from aqt.qt import QAction

from .anki_ops import fix_pgn_line_breaks, show_pgn_line_breaks
from .chesscom_dialog import show_chesscom_dialog
from .dialog import show_import_dialog
from .i18n import tr
from .puzzle_dialog import show_puzzle_dialog
from .study_updater import update_imported_studies
from .ui_common import apply_language


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
        ("menu.import", lambda: show_import_dialog()),
        ("menu.update_studies", update_imported_studies),
        ("menu.import_chesscom", show_chesscom_dialog),
        ("menu.import_puzzles", show_puzzle_dialog),
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

# PGNs pasted in the editor with wrapped lines: shown with their line breaks right
# away, and fixed in the collection before syncing so AnkiDroid reads them too
gui_hooks.card_will_show.append(show_pgn_line_breaks)
gui_hooks.profile_did_open.append(lambda: fix_pgn_line_breaks(mw.col))
gui_hooks.sync_will_start.append(lambda: fix_pgn_line_breaks(mw.col))
