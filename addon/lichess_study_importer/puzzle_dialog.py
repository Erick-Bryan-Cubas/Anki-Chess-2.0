"""
Qt dialog: import Lichess puzzles, from your puzzle activity (the ones you failed, by
default) or from puzzle links, as cards in <root>::Lichess puzzles.
"""

from __future__ import annotations

import time

from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from aqt.utils import showWarning, tooltip

from . import anki_ops, decks
from .i18n import tr
from .lichess_api import LichessError, fetch_puzzle, fetch_puzzle_activity, parse_puzzle_ids
from .puzzles import PuzzleCard, puzzle_card
from .ui_common import (
    apply_language,
    error_text,
    get_config,
    readonly_item,
    restore_layout,
    save_layout,
    write_config,
)

COL_CHECK, COL_PUZZLE, COL_RATING, COL_THEMES, COL_RESULT, COL_STATUS = range(6)
COLUMN_WIDTHS = {COL_CHECK: 28, COL_PUZZLE: 110, COL_RATING: 70, COL_THEMES: 360, COL_RESULT: 90}
LAYOUT_KEY = "lichessPuzzleImport"
REQUEST_PAUSE = 0.3  # seconds between puzzle requests, to stay under Lichess' rate limit


def load_puzzles(entries: list[tuple[str, bool | None, dict | None]], progress) -> list[PuzzleCard]:
    """
    Cards for (puzzle id, your result, activity entry) items. Each puzzle is fetched
    with its game, to start the card before the opponent's last move; an activity
    entry without it still gives a card from the puzzle position.
    """
    cards = []
    for done, (puzzle_id, win, entry) in enumerate(entries):
        progress(done, len(entries))
        try:
            data = fetch_puzzle(puzzle_id)
        except LichessError:
            if entry is None:
                raise
            data = entry
        cards.append(puzzle_card(data, win))
        time.sleep(REQUEST_PAUSE)
    return cards


class PuzzleImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("puzzle.title"))
        self.config = get_config()
        self.cards: list[PuzzleCard] = []
        self.statuses: list[str] = []
        self.base = anki_ops.default_base(self.config.get("base_note_type", ""))
        self.root = decks.root_name(self.config.get("deck_root"))
        self.deck = f"{self.root}::{tr('deck.puzzles')}"

        layout = QVBoxLayout(self)

        # --- Your puzzle activity ---
        activity = QHBoxLayout()
        self.token_edit = QLineEdit(self.config.get("lichess_token", ""))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(tr("puzzle.token_placeholder"))
        self.token_edit.setToolTip(tr("puzzle.token_tip"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 500)
        self.max_spin.setValue(int(self.config.get("puzzle_max", 50)))
        self.failed_only = QCheckBox(tr("puzzle.failed_only"))
        self.failed_only.setChecked(bool(self.config.get("puzzle_failed_only", True)))
        btn_activity = QPushButton(tr("puzzle.load_activity"))
        btn_activity.clicked.connect(self.on_load_activity)
        activity.addWidget(QLabel(tr("token.label")))
        activity.addWidget(self.token_edit, 1)
        activity.addWidget(QLabel(tr("puzzle.last")))
        activity.addWidget(self.max_spin)
        activity.addWidget(self.failed_only)
        activity.addWidget(btn_activity)
        layout.addLayout(activity)

        # --- Puzzle links ---
        links = QHBoxLayout()
        self.links_edit = QLineEdit()
        self.links_edit.setPlaceholderText(tr("puzzle.links_placeholder"))
        self.links_edit.returnPressed.connect(self.on_load_links)
        btn_links = QPushButton(tr("source.load_url"))
        btn_links.clicked.connect(self.on_load_links)
        links.addWidget(self.links_edit, 1)
        links.addWidget(btn_links)
        layout.addLayout(links)

        self.summary = QLabel(tr("puzzle.none"))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                tr("puzzle.table.puzzle"),
                tr("puzzle.table.rating"),
                tr("puzzle.table.themes"),
                tr("puzzle.table.result"),
                tr("table.status"),
            ]
        )
        for col, width in COLUMN_WIDTHS.items():
            self.table.setColumnWidth(col, width)
        self.table.itemChanged.connect(lambda item: self.update_import_button())
        layout.addWidget(self.table, 1)
        restore_layout(self, self.table, LAYOUT_KEY, (900, 600))

        deck_label = QLabel(tr("puzzle.deck", deck=self.deck))
        layout.addWidget(deck_label)
        self.update_existing = QCheckBox(tr("form.update_existing"))
        self.update_existing.setChecked(bool(self.config.get("update_existing", False)))
        layout.addWidget(self.update_existing)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close
        )
        self.import_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_btn.setText(tr("button.import"))
        self.import_btn.setEnabled(False)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr("button.close"))
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if not self.base:
            self.summary.setText(tr("warn.no_note_types"))

    def done(self, result: int):
        save_layout(self, self.table, LAYOUT_KEY)
        super().done(result)

    # --- Loading ---

    def run_loading(self, entries_op):
        """entries_op() -> [(puzzle id, win, activity entry)], then each puzzle is fetched."""

        def progress(done, total):
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=tr("puzzle.loading", done=done, total=total), value=done, max=total
                )
            )

        QueryOp(
            parent=self,
            op=lambda col: load_puzzles(entries_op(), progress),
            success=self.show_cards,
        ).failure(lambda e: showWarning(error_text(e), parent=self)).with_progress(
            tr("puzzle.loading", done=0, total="?")
        ).without_collection().run_in_background()

    def on_load_activity(self):
        token = self.token_edit.text().strip()
        if not token:
            showWarning(tr("puzzle.token_needed"), parent=self)
            return
        failed_only = self.failed_only.isChecked()
        max_entries = self.max_spin.value()

        def entries():
            activity = fetch_puzzle_activity(token, max_entries)
            return [
                (e["puzzle"]["id"], e.get("win"), e)
                for e in activity
                if not (failed_only and e.get("win"))
            ]

        self.run_loading(entries)

    def on_load_links(self):
        ids = parse_puzzle_ids(self.links_edit.text())
        if not ids:
            showWarning(tr("puzzle.invalid_links"), parent=self)
            return
        self.run_loading(lambda: [(i, None, None) for i in ids])

    def show_cards(self, cards: list[PuzzleCard]):
        self.cards = cards
        self.statuses = [anki_ops.card_status(mw.col, c, True)[0] for c in cards]
        self.table.blockSignals(True)
        self.table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checked = self.statuses[row] != "same"
            check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, COL_CHECK, check)
            result = {True: tr("puzzle.solved"), False: tr("puzzle.failed")}.get(card.win, "")
            for col, value, tip in (
                (COL_PUZZLE, card.puzzle_id, card.chapter_url),
                (COL_RATING, str(card.rating), ""),
                (COL_THEMES, ", ".join(card.themes), ", ".join(card.themes)),
                (COL_RESULT, result, ""),
                (COL_STATUS, tr(f"status.{self.statuses[row]}"), ""),
            ):
                self.table.setItem(row, col, readonly_item(value, tip))
        self.table.blockSignals(False)
        failed = sum(c.win is False for c in cards)
        self.summary.setText(tr("puzzle.summary", count=len(cards), failed=failed))
        self.update_import_button()
        if not cards:
            tooltip(tr("puzzle.no_cards"), parent=self)

    # --- Import ---

    def checked_cards(self) -> list[PuzzleCard]:
        return [
            card
            for row, card in enumerate(self.cards)
            if self.table.item(row, COL_CHECK).checkState() == Qt.CheckState.Checked
        ]

    def update_import_button(self):
        count = len(self.checked_cards()) if self.cards else 0
        self.import_btn.setText(tr("button.import_count", count=count) if count else tr("button.import"))
        self.import_btn.setEnabled(bool(count) and self.base is not None)

    def on_import(self):
        selected = self.checked_cards()
        if not selected or not self.base:
            return
        try:
            models = {
                mode: anki_ops.ensure_mode_note_type(self.base, mode) for mode in {c.mode for c in selected}
            }
        except anki_ops.ChessImportError as e:
            showWarning(str(e), parent=self)
            return
        placement = decks.Placement(self.deck)
        rows = [(card, models[card.mode], placement) for card in selected]
        update_existing = self.update_existing.isChecked()
        self.config.update(
            {
                "lichess_token": self.token_edit.text().strip(),
                "puzzle_max": self.max_spin.value(),
                "puzzle_failed_only": self.failed_only.isChecked(),
                "update_existing": update_existing,
            }
        )
        write_config(self.config)
        stats = {}

        def on_success(_changes):
            tooltip(tr("puzzle.result", **stats), parent=mw)
            self.show_cards(self.cards)  # statuses now "imported"

        CollectionOp(
            parent=self,
            op=lambda col: anki_ops.import_chapters(
                col, rows, update_existing, True, stats, tr("puzzle.undo")
            ),
        ).success(on_success).run_in_background()


def show_puzzle_dialog():
    if not mw.col:
        return
    apply_language()
    PuzzleImportDialog(mw).exec()
