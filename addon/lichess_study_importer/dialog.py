"""
Qt dialog: load a Lichess study (file or URL), pick chapters/modes and import.
"""

from __future__ import annotations

import os
import textwrap

import anki.lang
import aqt
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import (
    askUser,
    openLink,
    restoreGeom,
    restoreHeader,
    saveGeom,
    saveHeader,
    showWarning,
    tooltip,
)

from . import anki_ops, decks
from .i18n import resolve_language, set_language, tr
from .lichess_api import LichessError, fetch_study_pgn, parse_study_url
from .pgn_split import (
    KIND_EMPTY,
    KIND_EXERCISE,
    KIND_GAME,
    KIND_LINE,
    MODE_FLIPPED,
    MODE_STUDY,
    Chapter,
    mode_for,
    split_games,
)

KIND_KEYS = {
    KIND_EXERCISE: "kind.exercise",
    KIND_LINE: "kind.line",
    KIND_GAME: "kind.game",
    KIND_EMPTY: "kind.empty",
}
CHAPTER_KINDS = (KIND_EXERCISE, KIND_LINE, KIND_GAME)  # the kind decides the deck
SIDES = (("w", "side.white"), ("b", "side.black"), (None, "side.both"))  # None: Study
OTHER_SIDE = {"w": "b", "b": "w"}
COL_CHECK, COL_NAME, COL_KIND, COL_SIDE, COL_NOTE_TYPE, COL_DECK, COL_PREVIEW = range(7)
COLUMN_WIDTHS = {
    COL_CHECK: 28,
    COL_NAME: 260,
    COL_KIND: 140,
    COL_SIDE: 110,
    COL_NOTE_TYPE: 190,
    COL_DECK: 160,
}
LAYOUT_KEY = "lichessStudyImport"  # window size and columns, kept in the Anki profile


def lichess_error_text(e: LichessError) -> str:
    params = dict(e.params)
    if "hint" in params:
        params["hint"] = tr(params["hint"])
    return tr(e.key, **params)


def get_config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def apply_language() -> None:
    # "en" (default), "pt-BR", or "auto" to follow Anki's interface language
    setting = get_config().get("language")
    set_language(resolve_language(setting, getattr(anki.lang, "current_lang", None)))


def write_config(config: dict) -> None:
    mw.addonManager.writeConfig(__name__, config)


# --- Layout shared with the Chess.com dialog ---


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


class DeckItem(QTableWidgetItem):
    """Deck cell; an empty subdeck (the chapter goes to the study deck) says so when shown."""

    def data(self, role):
        value = super().data(role)
        editable = self.flags() & Qt.ItemFlag.ItemIsEditable
        if role == Qt.ItemDataRole.DisplayRole and not value and editable:
            return tr("deck.study_itself")
        return value


class StudyImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("dialog.title"))
        self.config = get_config()
        self.chapters: list[Chapter] = []
        self.kinds: list[str] = []
        self._openings: dict[int, str | None] = {}  # row -> catalog opening name
        self.study_fallback = ""  # deck name for PGNs without StudyName: the file name
        self._spreading = False  # a change being copied to the other selected rows
        # Deck names edited in the dialog, kept per study/chapter in the config so that
        # importing the study again (e.g. to update it) keeps them
        self.study_key: str | None = None
        self.default_study_deck = ""
        self.custom_subdecks: dict[int, str] = {}  # row -> subdeck typed in the Deck column
        self._refreshing = False  # deck cells being filled by the dialog, not typed

        # Flipped/Study note types are cloned from the base one; the root deck and the
        # base are config settings (deck_root, base_note_type), not asked every time
        self.base = anki_ops.default_base(self.config.get("base_note_type", ""))
        self.root = decks.root_name(self.config.get("deck_root"))
        # Note types a chapter can use: (name, mode, exists)
        self.choices = anki_ops.note_type_choices(self.base) if self.base else []
        self.choice_modes = {name: mode for name, mode, _ in self.choices}
        base_name = self.base["name"] if self.base else "AnkiChess"

        layout = QVBoxLayout(self)

        # --- Source ---
        src = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(tr("source.url_placeholder"))
        self.url_edit.returnPressed.connect(self.on_load_url)
        self.url_btn = QPushButton(tr("source.load_url"))
        self.url_btn.clicked.connect(self.on_load_url)
        btn_file = QPushButton(tr("source.open_file"))
        btn_file.clicked.connect(self.on_open_file)
        self.token_btn = QPushButton(tr("token.show"))
        self.token_btn.setFlat(True)
        self.token_btn.setToolTip(tr("token.tooltip"))
        self.token_btn.clicked.connect(lambda: self.show_token(True))
        src.addWidget(self.url_edit, 1)
        src.addWidget(self.url_btn)
        src.addWidget(btn_file)
        src.addWidget(self.token_btn)
        layout.addLayout(src)

        # Only needed for private studies: hidden until asked for, or a token is saved
        self.token_row = QWidget()
        token_layout = QHBoxLayout(self.token_row)
        token_layout.setContentsMargins(0, 0, 0, 0)
        self.token_edit = QLineEdit(self.config.get("lichess_token", ""))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(tr("token.placeholder"))
        self.token_edit.setToolTip(tr("token.tooltip"))
        token_layout.addWidget(QLabel(tr("token.label")))
        token_layout.addWidget(self.token_edit, 1)
        layout.addWidget(self.token_row)
        self.show_token(bool(self.token_edit.text()))

        self.study_label = QLabel(tr("study.none"))
        self.study_label.setWordWrap(True)
        self.study_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.study_label)

        # Study deck, editable once a study is loaded
        self.deck_row = QWidget()
        deck_layout = QHBoxLayout(self.deck_row)
        deck_layout.setContentsMargins(0, 0, 0, 0)
        self.deck_edit = QLineEdit()
        self.deck_edit.setToolTip(tr("form.study_deck_tip"))
        self.deck_edit.textEdited.connect(lambda _: self.refresh_decks())
        self.deck_edit.editingFinished.connect(self.on_study_deck_edited)
        deck_reset = QPushButton(tr("form.study_deck_reset"))
        deck_reset.setToolTip(tr("form.study_deck_reset_tip"))
        deck_reset.clicked.connect(self.reset_decks)
        deck_layout.addWidget(QLabel(tr("form.study_deck")))
        deck_layout.addWidget(self.deck_edit, 1)
        deck_layout.addWidget(deck_reset)
        layout.addWidget(self.deck_row)
        self.deck_row.setVisible(False)

        # --- Chapter table ---
        filters = QHBoxLayout()
        self.include_games = QCheckBox(tr("filter.include_games"))
        self.include_games.setChecked(bool(self.config.get("include_games", False)))
        self.include_games.toggled.connect(self.on_toggle_games)
        btn_all = QPushButton(tr("filter.check_exercises"))
        btn_all.clicked.connect(self.check_exercises_and_lines)
        btn_none = QPushButton(tr("filter.uncheck_all"))
        btn_none.clicked.connect(self.uncheck_all)
        filters.addWidget(self.include_games)
        filters.addStretch(1)
        filters.addWidget(btn_all)
        filters.addWidget(btn_none)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                tr("table.chapter"),
                tr("table.kind"),
                tr("table.side"),
                tr("table.note_type"),
                tr("table.deck"),
                tr("table.moves"),
            ]
        )
        for col, tip in (
            (COL_KIND, tr("table.kind_tip")),
            (COL_SIDE, tr("table.side_tip")),
            (COL_NOTE_TYPE, tr("table.note_type_tip", base=base_name)),
            (COL_DECK, tr("table.deck_tip")),
        ):
            self.table.horizontalHeaderItem(col).setToolTip(tip)
        for col, width in COLUMN_WIDTHS.items():
            self.table.setColumnWidth(col, width)
        # Several rows (Ctrl/Shift+click) are changed together, see spread()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellDoubleClicked.connect(self.on_double_click)
        layout.addWidget(self.table, 1)
        restore_layout(self, self.table, LAYOUT_KEY, (1100, 680))

        hint = QLabel(tr("table.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.update_existing = QCheckBox(tr("form.update_existing"))
        self.update_existing.setChecked(bool(self.config.get("update_existing", False)))
        layout.addWidget(self.update_existing)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.import_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_btn.setText(tr("button.import"))
        self.import_btn.setEnabled(False)
        # Standard buttons follow Anki's language; keep them in the add-on's language
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("button.cancel"))
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if not self.base:
            self.study_label.setText(tr("warn.no_note_types"))

    def done(self, result: int):
        save_layout(self, self.table, LAYOUT_KEY)
        super().done(result)

    def show_token(self, visible: bool):
        self.token_row.setVisible(visible)
        self.token_btn.setVisible(not visible)

    # --- Loading ---

    def on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("source.file_dialog_title"),
            self.config.get("last_dir", ""),
            tr("source.file_filter"),
        )
        if not path:
            return
        self.config["last_dir"] = os.path.dirname(path)
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            showWarning(tr("warn.read_file", error=e), parent=self)
            return
        self.load_pgn(text, os.path.basename(path))

    def on_load_url(self):
        parsed = parse_study_url(self.url_edit.text())
        if not parsed:
            showWarning(tr("warn.invalid_url"), parent=self)
            return
        study_id, chapter_id = parsed
        token = self.token_edit.text()
        self.study_label.setText(tr("study.downloading"))
        self.url_btn.setEnabled(False)

        def on_done(fut):
            self.url_btn.setEnabled(True)
            try:
                text = fut.result()
            except LichessError as e:
                self.study_label.setText(tr("study.download_failed"))
                if e.key == "error.no_access":
                    self.show_token(True)  # private study: the token is the way in
                showWarning(lichess_error_text(e), parent=self)
                return
            self.load_pgn(text, f"lichess.org/study/{study_id}")

        mw.taskman.run_in_background(
            lambda: fetch_study_pgn(study_id, chapter_id, token=token), on_done
        )

    def load_pgn(self, text: str, source: str):
        self.chapters = split_games(text)
        # Suggested kinds: exercises starting from a book position are opening lines
        self.kinds = [decks.suggest_kind(ch) for ch in self.chapters]
        if not self.chapters:
            showWarning(tr("warn.no_chapters"), parent=self)
            return

        self._openings = {}
        self.study_fallback = os.path.splitext(source)[0]
        study = next((c.study_name for c in self.chapters if c.study_name), "") or source
        counts = {k: self.kinds.count(k) for k in KIND_KEYS}
        summary = tr(
            "study.summary",
            study=study,
            total=len(self.chapters),
            exercises=counts[KIND_EXERCISE],
            lines=counts[KIND_LINE],
            games=counts[KIND_GAME],
            empty=counts[KIND_EMPTY],
        )
        self.study_label.setText(summary)

        # Deck names renamed the last time this study was imported
        self.study_key = next((c.study_id for c in self.chapters if c.study_id), None)
        self.default_study_deck = decks.study_deck(self.chapters[0], self.root, self.study_fallback)
        saved = self.config.get("study_decks", {}).get(self.study_key) if self.study_key else None
        self.deck_edit.setText(saved or self.default_study_deck)
        self.deck_row.setVisible(True)
        chapter_decks = self.config.get("chapter_decks", {})
        self.custom_subdecks = {
            row: chapter_decks[ch.dedupe_key]
            for row, ch in enumerate(self.chapters)
            if ch.dedupe_key in chapter_decks
        }
        self.populate_table()

    def populate_table(self):
        include_games = self.include_games.isChecked()
        self.table.blockSignals(True)
        self.table.setRowCount(0)  # drops the combos of the previous study
        self.table.setRowCount(len(self.chapters))
        for row, ch in enumerate(self.chapters):
            kind = self.kinds[row]
            check = QTableWidgetItem()
            flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            if kind == KIND_EMPTY:
                flags = Qt.ItemFlag.NoItemFlags
            check.setFlags(flags | Qt.ItemFlag.ItemIsSelectable)
            checked = kind in (KIND_EXERCISE, KIND_LINE) or (kind == KIND_GAME and include_games)
            check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, COL_CHECK, check)

            name_tip = "\n".join(filter(None, [ch.name, ch.chapter_url, ch.chapter_url and tr("table.open_tip")]))
            self.table.setItem(row, COL_NAME, readonly_item(ch.name, name_tip))
            deck_item = DeckItem("")
            deck_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if kind != KIND_EMPTY:
                # Renamed with a double-click or F2, see on_item_changed
                deck_item.setFlags(deck_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, COL_DECK, deck_item)
            moves = textwrap.fill(ch.moves_preview(600), 80)
            self.table.setItem(row, COL_PREVIEW, readonly_item(ch.moves_preview(200), moves))

            if kind == KIND_EMPTY:
                # Nothing to import: plain text instead of combos
                for col, text in ((COL_KIND, tr(KIND_KEYS[kind])), (COL_SIDE, "—"), (COL_NOTE_TYPE, "—")):
                    item = QTableWidgetItem(text)
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.table.setItem(row, col, item)
                continue

            kind_combo = QComboBox()
            for key in CHAPTER_KINDS:
                kind_combo.addItem(tr(KIND_KEYS[key]), key)
            kind_combo.setCurrentIndex(CHAPTER_KINDS.index(kind))
            kind_combo.currentIndexChanged.connect(lambda _, r=row: self.on_kind_changed(r))
            self.table.setCellWidget(row, COL_KIND, kind_combo)

            side_combo = QComboBox()
            for side, label_key in SIDES:
                side_combo.addItem(tr(label_key), side)
            side_combo.setCurrentIndex([s for s, _ in SIDES].index(ch.player))
            side_combo.setToolTip(tr("side.tooltip", side=tr(f"side.to_move.{ch.side_to_move}")))
            side_combo.currentIndexChanged.connect(lambda _, r=row: self.on_side_changed(r))
            self.table.setCellWidget(row, COL_SIDE, side_combo)

            note_type_combo = QComboBox()
            note_type_combo.currentIndexChanged.connect(
                lambda _, r=row: self.on_note_type_changed(r)
            )
            self.table.setCellWidget(row, COL_NOTE_TYPE, note_type_combo)
            self.fill_note_types(row)
        self.table.blockSignals(False)

        self.refresh_decks()
        self.update_import_button()

    # --- Several rows at once ---

    def spread(self, row: int, col: int):
        """
        Copy a combo change to the other selected rows (Ctrl/Shift+click on the chapter
        names selects several; the combos don't change the selection).
        """
        if self._spreading:
            return
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if row not in rows or len(rows) < 2:
            return
        self._spreading = True
        try:
            # Same list in every row, so the same index means the same choice
            index = self.table.cellWidget(row, col).currentIndex()
            for other in rows - {row}:
                combo = self.table.cellWidget(other, col)
                if combo:
                    combo.setCurrentIndex(index)
        finally:
            self._spreading = False

    def on_item_changed(self, item: QTableWidgetItem):
        if item.column() == COL_CHECK:
            self.update_import_button()
        elif item.column() == COL_DECK and not self._refreshing:
            self.on_subdeck_edited(item.row(), item.data(Qt.ItemDataRole.EditRole) or "")

    def on_subdeck_edited(self, row: int, text: str):
        """A subdeck typed in the Deck column; the same name goes to the other selected rows."""
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if row not in rows:
            rows = {row}
        subdeck = decks.clean_deck_name(text)
        for r in rows:
            if self.row_kind(r) == KIND_EMPTY:
                continue
            if subdeck == decks.section_name(self.row_kind(r)):
                self.custom_subdecks.pop(r, None)  # back to the default
            else:
                self.custom_subdecks[r] = subdeck
            self.refresh_deck(r)

    def on_double_click(self, row: int, col: int):
        url = self.chapters[row].chapter_url if row < len(self.chapters) else ""
        if col == COL_NAME and url:
            openLink(url)

    # --- Side and note type ---

    def row_side(self, row: int) -> str | None:
        return self.table.cellWidget(row, COL_SIDE).currentData()

    def fill_note_types(self, row: int):
        """Note type list of a row, on the default for the side played."""
        combo = self.table.cellWidget(row, COL_NOTE_TYPE)
        combo.blockSignals(True)
        combo.clear()
        for name, mode, exists in self.choices:
            label = name if exists else f"{name} {tr('note_type.new')}"
            combo.addItem(label, name)
            if not exists:
                combo.setItemData(combo.count() - 1, tr("note_type.new_tip"), Qt.ItemDataRole.ToolTipRole)
        combo.blockSignals(False)
        self.select_note_type_for_side(row)

    def select_note_type_for_side(self, row: int):
        """Puzzle when you make the first move, Flipped when the opponent does, Study for both."""
        mode = mode_for(self.row_side(row), self.chapters[row].side_to_move)
        combo = self.table.cellWidget(row, COL_NOTE_TYPE)
        index = next((i for i, (_, m, _) in enumerate(self.choices) if m == mode), -1)
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def on_side_changed(self, row: int):
        self.select_note_type_for_side(row)
        self.spread(row, COL_SIDE)

    def on_note_type_changed(self, row: int):
        """Show the side a note type makes you play, without changing the note type back."""
        mode = self.choice_modes.get(self.table.cellWidget(row, COL_NOTE_TYPE).currentData())
        if mode:
            stm = self.chapters[row].side_to_move
            side = None if mode == MODE_STUDY else OTHER_SIDE[stm] if mode == MODE_FLIPPED else stm
            side_combo = self.table.cellWidget(row, COL_SIDE)
            side_combo.blockSignals(True)
            side_combo.setCurrentIndex([s for s, _ in SIDES].index(side))
            side_combo.blockSignals(False)
        self.spread(row, COL_NOTE_TYPE)

    # --- Decks ---

    def row_kind(self, row: int) -> str:
        combo = self.table.cellWidget(row, COL_KIND)
        return combo.currentData() if combo else KIND_EMPTY

    def on_kind_changed(self, row: int):
        self.refresh_deck(row)
        self.spread(row, COL_KIND)

    def placement(self, row: int) -> decks.Placement:
        kind = self.row_kind(row)
        if kind == KIND_LINE and row not in self._openings:
            self._openings[row] = decks.chapter_opening(self.chapters[row])
        return decks.place_chapter(
            self.chapters[row],
            self.root,
            kind=kind,
            opening=self._openings.get(row),
            fallback_study=self.study_fallback,
            deck=self.study_deck(),
            subdeck=self.custom_subdecks.get(row),
        )

    def study_deck(self) -> str:
        return decks.clean_deck_name(self.deck_edit.text()) or self.default_study_deck

    def on_study_deck_edited(self):
        """Show the name as Anki will store it (trimmed levels, no empty ones)."""
        if self.deck_edit.text() != self.study_deck():
            self.deck_edit.setText(self.study_deck())
        self.refresh_decks()

    def reset_decks(self):
        """Back to the names from Lichess: the study deck and every subdeck."""
        self.deck_edit.setText(self.default_study_deck)
        self.custom_subdecks.clear()
        self.refresh_decks()

    def refresh_deck(self, row: int):
        if self.row_kind(row) == KIND_EMPTY:
            return
        placement = self.placement(row)
        item = self.table.item(row, COL_DECK)
        # The study deck is in the field above: the cell keeps the subdeck, empty when
        # the chapter goes to the study deck itself
        subdeck = self.custom_subdecks.get(row, decks.section_name(self.row_kind(row)))
        self._refreshing = True
        try:
            item.setText(subdeck)
            item.setToolTip("\n".join([placement.deck, *placement.tags]))
        finally:
            self._refreshing = False

    def refresh_decks(self):
        for row in range(len(self.chapters)):
            self.refresh_deck(row)

    # --- Selection helpers ---

    def set_checked(self, kind: str, value: bool):
        for row in range(len(self.chapters)):
            if self.row_kind(row) == kind:
                state = Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
                self.table.item(row, COL_CHECK).setCheckState(state)

    def check_exercises_and_lines(self):
        for kind in (KIND_EXERCISE, KIND_LINE):
            self.set_checked(kind, True)

    def uncheck_all(self):
        for kind in CHAPTER_KINDS:
            self.set_checked(kind, False)

    def on_toggle_games(self, checked: bool):
        self.set_checked(KIND_GAME, checked)

    def checked_rows(self) -> list[int]:
        return [
            row
            for row in range(len(self.chapters))
            if self.row_kind(row) != KIND_EMPTY
            and self.table.item(row, COL_CHECK).checkState() == Qt.CheckState.Checked
        ]

    def update_import_button(self):
        count = len(self.checked_rows())
        self.import_btn.setText(tr("button.import_count", count=count) if count else tr("button.import"))
        self.import_btn.setEnabled(bool(count) and self.base is not None)

    def selected_rows(self) -> list[tuple[Chapter, str, decks.Placement]]:
        """(chapter, note type name, placement) of the checked chapters."""
        return [
            (
                self.chapters[row],
                self.table.cellWidget(row, COL_NOTE_TYPE).currentData(),
                self.placement(row),
            )
            for row in self.checked_rows()
        ]

    # --- Import ---

    def renamed_decks(self) -> dict:
        """Config entries keeping the deck names edited for this study (defaults removed)."""
        study_decks = dict(self.config.get("study_decks", {}))
        if self.study_key:
            if self.study_deck() != self.default_study_deck:
                study_decks[self.study_key] = self.study_deck()
            else:
                study_decks.pop(self.study_key, None)
        chapter_decks = dict(self.config.get("chapter_decks", {}))
        for row, ch in enumerate(self.chapters):
            if not ch.dedupe_key:
                continue
            if row in self.custom_subdecks:
                chapter_decks[ch.dedupe_key] = self.custom_subdecks[row]
            else:
                chapter_decks.pop(ch.dedupe_key, None)
        return {"study_decks": study_decks, "chapter_decks": chapter_decks}

    def on_import(self):
        selected = self.selected_rows()
        if not selected:
            showWarning(tr("warn.no_selection"), parent=self)
            return
        base = self.base
        if not base:
            showWarning(tr("warn.base_missing"), parent=self)
            return

        # Missing Flipped/Study note types are created up front (outside the undoable import)
        models = {}
        try:
            for name in {name for _, name, _ in selected}:
                models[name] = mw.col.models.by_name(name) or anki_ops.ensure_mode_note_type(
                    base, self.choice_modes[name]
                )
        except anki_ops.ChessImportError as e:
            showWarning(str(e), parent=self)
            return
        rows = [(ch, models[name], placement) for ch, name, placement in selected]

        update_existing = self.update_existing.isChecked()
        strip_anno = bool(self.config.get("strip_anno", True))
        stats = {"created": 0, "updated": 0, "skipped": 0}

        self.config.update(
            {
                "include_games": self.include_games.isChecked(),
                "update_existing": update_existing,
                "lichess_token": self.token_edit.text().strip(),
                **self.renamed_decks(),
            }
        )
        write_config(self.config)

        def on_success(_changes):
            tooltip(tr("result.summary", **stats), parent=mw)
            self.accept()
            offer_note_type_change(stats.get("other_type"))

        CollectionOp(
            parent=self,
            op=lambda col: anki_ops.import_chapters(
                col, rows, update_existing, strip_anno, stats
            ),
        ).success(on_success).run_in_background()


def offer_note_type_change(other: dict[str, list[int]] | None):
    """
    Chapters imported before in another note type keep it (e.g. AnkiChess for a chapter
    played as Black). Changing it needs a full sync, so the notes are shown in the
    Browser for Notes > Change Note Type.
    """
    if not other:
        return
    count = sum(len(nids) for nids in other.values())
    targets = ", ".join(f"{name} ({len(nids)})" for name, nids in other.items())
    if askUser(tr("result.other_type", count=count, targets=targets), parent=mw):
        nids = ",".join(str(nid) for nids in other.values() for nid in nids)
        aqt.dialogs.open("Browser", mw, search=(f"nid:{nids}",))


def show_import_dialog():
    if not mw.col:
        return
    apply_language()
    StudyImportDialog(mw).exec()
