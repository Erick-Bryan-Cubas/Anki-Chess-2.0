"""
AnkiChess - Lichess Study Importer.
Creates AnkiChess notes from Lichess studies, from analysed Chess.com and Lichess games,
and from Lichess puzzles, all in one import window (Tools > Import into AnkiChess).
"""

import os

from aqt import gui_hooks, mw
from aqt.qt import QAction

from . import analysis_note, template_preview
from .anki_ops import apply_template_preview, fix_pgn_line_breaks, show_pgn_line_breaks
from .i18n import tr
from .import_window import show_import_window
from .ui_common import apply_language, preview_enabled


def _find_ankichess_menu():
    # Menu created by the AnkiChess Companion add-on, if installed
    for action in mw.form.menubar.actions():
        if action.menu() and action.text().replace("&", "") == "AnkiChess":
            return action.menu()
    return None


def setup_menu():
    apply_language()
    action = QAction(tr("menu.import"), mw)
    action.triggered.connect(lambda: show_import_window())
    mw.form.menuTools.addAction(action)
    chess_menu = _find_ankichess_menu()
    if chess_menu:
        chess_menu.addSeparator()
        chess_menu.addAction(action)


# Runs after all add-ons are loaded, so the Companion menu already exists
gui_hooks.main_window_did_init.append(setup_menu)

def apply_preview(config: dict | None = None):
    # The template preview shipped in the add-on, or back to the official one when turned off
    if not mw.col:
        return
    try:
        apply_template_preview(mw.col, preview_enabled(config))
    except OSError as e:
        print(f"AnkiChess template preview: {e}")


def on_profile_open():
    fix_pgn_line_breaks(mw.col)
    apply_preview()


def preview_in_companion_pages(web_content, context):
    # Manage chessRs Notes (the Companion) runs the template's script: the preview's, so it
    # shows and saves the preview's settings for each note type (hints, refutation...)
    if "addon-" not in web_content.body or not mw.col or not preview_enabled():
        return
    preview = template_preview.bundled()
    # Written into the media folder on profile open; without it the page would have no script
    if preview and os.path.exists(os.path.join(mw.col.media.dir(), preview)):
        web_content.body = template_preview.companion_page(web_content.body, preview)


# PGNs pasted in the editor with wrapped lines: shown with their line breaks right
# away, and fixed in the collection before syncing so AnkiDroid reads them too
gui_hooks.card_will_show.append(show_pgn_line_breaks)
gui_hooks.profile_did_open.append(on_profile_open)
gui_hooks.sync_will_start.append(lambda: fix_pgn_line_breaks(mw.col))
# preview_template changed in Tools > Add-ons > Config
mw.addonManager.setConfigUpdatedAction(__name__, apply_preview)

# "New card from this position" on the back of a card: the Add window with that PGN
gui_hooks.webview_will_set_content.append(analysis_note.add_flag)
gui_hooks.webview_did_receive_js_message.append(analysis_note.on_js_message)
gui_hooks.webview_will_set_content.append(preview_in_companion_pages)
