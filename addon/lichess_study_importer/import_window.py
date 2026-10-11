"""
The AnkiChess import window: Studies, Games and Puzzles pages in tabs, with the update
of the imported studies a click away. One menu entry instead of one per source; the
pages share the config (token, root deck, note types) and stay open after importing.
"""

from __future__ import annotations

from aqt import mw
from aqt.qt import QDialog, QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout

from .chesscom_dialog import GameImportPage
from .dialog import StudyImportPage
from .i18n import tr
from .puzzle_dialog import PuzzleImportPage
from .study_updater import update_imported_studies
from .ui_common import apply_language, restore_window, save_window

WINDOW_KEY = "ankiChessImport"  # window size and position, kept in the Anki profile
TAB_STUDIES, TAB_GAMES, TAB_PUZZLES = range(3)


class ImportWindow(QDialog):
    def __init__(self, parent=None, tab: int = TAB_STUDIES, urls: str = ""):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("window.title"))
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.studies = StudyImportPage(self, urls)
        self.games = GameImportPage(self)
        self.puzzles = PuzzleImportPage(self)
        self.tabs.addTab(self.studies, tr("window.tab_studies"))
        self.tabs.addTab(self.games, tr("window.tab_games"))
        self.tabs.addTab(self.puzzles, tr("window.tab_puzzles"))
        self.tabs.setCurrentIndex(tab)
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        update = QPushButton(tr("menu.update_studies"))
        update.setToolTip(tr("window.update_tip"))
        update.clicked.connect(self.on_update_studies)
        close = QPushButton(tr("button.close"))
        close.clicked.connect(self.reject)
        bottom.addWidget(update)
        bottom.addStretch(1)
        bottom.addWidget(close)
        layout.addLayout(bottom)
        restore_window(self, WINDOW_KEY, (1250, 760))

    def on_update_studies(self):
        def open_studies(links: str):
            self.tabs.setCurrentIndex(TAB_STUDIES)
            self.studies.load_urls(links)

        update_imported_studies(self, open_studies)

    def done(self, result: int):
        save_window(self, WINDOW_KEY)
        for page in (self.studies, self.games, self.puzzles):
            page.save_layout()
        super().done(result)


def show_import_window(tab: int = TAB_STUDIES, urls: str = ""):
    if not mw.col:
        return
    apply_language()
    ImportWindow(mw, tab, urls).exec()
