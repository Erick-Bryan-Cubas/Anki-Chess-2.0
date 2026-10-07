"""
Qt dialog: load a Lichess study (file or URL), pick chapters/modes and import.
"""

from __future__ import annotations

import os

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
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from aqt.utils import askUser, showWarning, tooltip

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


class StudyImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("dialog.title"))
        self.resize(900, 620)
        self.config = get_config()
        self.chapters: list[Chapter] = []
        self.kinds: list[str] = []
        self._openings: dict[int, str | None] = {}  # row -> catalog opening name

        layout = QVBoxLayout(self)

        # --- Source ---
        src = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(tr("source.url_placeholder"))
        self.url_edit.returnPressed.connect(self.on_load_url)
        btn_url = QPushButton(tr("source.load_url"))
        btn_url.clicked.connect(self.on_load_url)
        btn_file = QPushButton(tr("source.open_file"))
        btn_file.clicked.connect(self.on_open_file)
        src.addWidget(self.url_edit, 1)
        src.addWidget(btn_url)
        src.addWidget(btn_file)
        layout.addLayout(src)

        token_row = QHBoxLayout()
        self.token_edit = QLineEdit(self.config.get("lichess_token", ""))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(tr("token.placeholder"))
        self.token_edit.setToolTip(tr("token.tooltip"))
        token_row.addWidget(QLabel(tr("token.label")))
        token_row.addWidget(self.token_edit, 1)
        layout.addLayout(token_row)

        self.study_label = QLabel(tr("study.none"))
        self.study_label.setWordWrap(True)
        layout.addWidget(self.study_label)

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
        header = self.table.horizontalHeader()
        for col in (COL_CHECK, COL_KIND, COL_SIDE, COL_NOTE_TYPE):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for col in (COL_NAME, COL_DECK, COL_PREVIEW):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        # --- Destination ---
        form = QFormLayout()
        self.model_combo = QComboBox()
        for m in anki_ops.find_chess_note_types():
            self.model_combo.addItem(m["name"], m["id"])
        preferred = self.config.get("base_note_type", "")
        idx = self.model_combo.findText(preferred) if preferred else -1
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentIndexChanged.connect(self.on_base_changed)
        form.addRow(tr("form.base_note_type"), self.model_combo)
        # Note types a chapter can use: (name, mode, exists)
        self.choices: list[tuple[str, str, bool]] = []
        self.choice_modes: dict[str, str] = {}
        self.update_choices()

        self.root_edit = QLineEdit(decks.root_name(self.config.get("deck_root")))
        self.root_edit.setToolTip(tr("form.deck_root_tip"))
        self.root_edit.textChanged.connect(self.refresh_decks)
        form.addRow(tr("form.deck_root"), self.root_edit)

        self.update_existing = QCheckBox(tr("form.update_existing"))
        self.update_existing.setChecked(bool(self.config.get("update_existing", False)))
        form.addRow("", self.update_existing)
        layout.addLayout(form)

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

        if self.model_combo.count() == 0:
            self.study_label.setText(tr("warn.no_note_types"))

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

        def on_done(fut):
            try:
                text = fut.result()
            except LichessError as e:
                self.study_label.setText(tr("study.download_failed"))
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

        study = next((c.study_name for c in self.chapters if c.study_name), "") or source
        counts = {k: self.kinds.count(k) for k in KIND_KEYS}
        self.study_label.setText(
            tr(
                "study.summary",
                study=study,
                total=len(self.chapters),
                exercises=counts[KIND_EXERCISE],
                lines=counts[KIND_LINE],
                games=counts[KIND_GAME],
                empty=counts[KIND_EMPTY],
            )
        )
        self._openings = {}
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(len(self.chapters))
        include_games = self.include_games.isChecked()
        for row, ch in enumerate(self.chapters):
            kind = self.kinds[row]
            check = QTableWidgetItem()
            flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            if kind == KIND_EMPTY:
                flags = Qt.ItemFlag.NoItemFlags
            check.setFlags(flags)
            checked = kind in (KIND_EXERCISE, KIND_LINE) or (kind == KIND_GAME and include_games)
            check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, COL_CHECK, check)

            for col, value in (
                (COL_NAME, ch.name),
                (COL_DECK, ""),
                (COL_PREVIEW, ch.preview),
            ):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if col == COL_NAME and ch.chapter_url:
                    item.setToolTip(ch.chapter_url)
                self.table.setItem(row, col, item)

            if kind == KIND_EMPTY:
                item = QTableWidgetItem(tr(KIND_KEYS[kind]))
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.table.setItem(row, COL_KIND, item)
            else:
                kind_combo = QComboBox()
                for key in CHAPTER_KINDS:
                    kind_combo.addItem(tr(KIND_KEYS[key]), key)
                kind_combo.setCurrentIndex(CHAPTER_KINDS.index(kind))
                kind_combo.currentIndexChanged.connect(lambda _, r=row: self.refresh_deck(r))
                self.table.setCellWidget(row, COL_KIND, kind_combo)

            side_combo = QComboBox()
            for side, label_key in SIDES:
                side_combo.addItem(tr(label_key), side)
            side_combo.setCurrentIndex([s for s, _ in SIDES].index(ch.player))
            side_combo.setToolTip(tr("side.tooltip", side=tr(f"side.to_move.{ch.side_to_move}")))
            side_combo.setEnabled(kind != KIND_EMPTY)
            side_combo.currentIndexChanged.connect(lambda _, r=row: self.on_side_changed(r))
            self.table.setCellWidget(row, COL_SIDE, side_combo)

            note_type_combo = QComboBox()
            note_type_combo.setEnabled(kind != KIND_EMPTY)
            note_type_combo.currentIndexChanged.connect(
                lambda _, r=row: self.on_note_type_changed(r)
            )
            self.table.setCellWidget(row, COL_NOTE_TYPE, note_type_combo)
            self.fill_note_types(row)

        self.refresh_decks()
        self.import_btn.setEnabled(self.model_combo.count() > 0)

    # --- Side and note type ---

    def update_choices(self):
        base = mw.col.models.get(self.model_combo.currentData()) if self.model_combo.count() else None
        self.choices = anki_ops.note_type_choices(base) if base else []
        self.choice_modes = {name: mode for name, mode, _ in self.choices}
        self.hint.setText(tr("modes.hint", base=base["name"] if base else "AnkiChess"))

    def on_base_changed(self):
        self.update_choices()
        for row in range(len(self.chapters)):
            self.fill_note_types(row)

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
        self.on_side_changed(row)

    def on_side_changed(self, row: int):
        """Puzzle when you make the first move, Flipped when the opponent does, Study for both."""
        mode = mode_for(self.row_side(row), self.chapters[row].side_to_move)
        combo = self.table.cellWidget(row, COL_NOTE_TYPE)
        index = next((i for i, (_, m, _) in enumerate(self.choices) if m == mode), -1)
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def on_note_type_changed(self, row: int):
        """Show the side a note type makes you play, without changing the note type back."""
        mode = self.choice_modes.get(self.table.cellWidget(row, COL_NOTE_TYPE).currentData())
        if not mode:
            return
        stm = self.chapters[row].side_to_move
        side = None if mode == MODE_STUDY else OTHER_SIDE[stm] if mode == MODE_FLIPPED else stm
        side_combo = self.table.cellWidget(row, COL_SIDE)
        side_combo.blockSignals(True)
        side_combo.setCurrentIndex([s for s, _ in SIDES].index(side))
        side_combo.blockSignals(False)

    # --- Decks ---

    def row_kind(self, row: int) -> str:
        combo = self.table.cellWidget(row, COL_KIND)
        return combo.currentData() if combo else KIND_EMPTY

    def placement(self, row: int) -> decks.Placement:
        kind = self.row_kind(row)
        if kind == KIND_LINE and row not in self._openings:
            self._openings[row] = decks.chapter_opening(self.chapters[row])
        return decks.place_chapter(
            self.chapters[row],
            decks.root_name(self.root_edit.text()),
            kind=kind,
            opening=self._openings.get(row),
        )

    def refresh_deck(self, row: int):
        if self.row_kind(row) == KIND_EMPTY:
            return
        placement = self.placement(row)
        item = self.table.item(row, COL_DECK)
        item.setText(placement.deck)
        item.setToolTip("\n".join([placement.deck, *placement.tags]))

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

    def selected_rows(self) -> list[tuple[Chapter, str, decks.Placement]]:
        """(chapter, note type name, placement) of the checked chapters."""
        rows = []
        for row, ch in enumerate(self.chapters):
            if self.row_kind(row) == KIND_EMPTY:
                continue
            if self.table.item(row, COL_CHECK).checkState() != Qt.CheckState.Checked:
                continue
            name = self.table.cellWidget(row, COL_NOTE_TYPE).currentData()
            rows.append((ch, name, self.placement(row)))
        return rows

    # --- Import ---

    def on_import(self):
        selected = self.selected_rows()
        if not selected:
            showWarning(tr("warn.no_selection"), parent=self)
            return
        base = mw.col.models.get(self.model_combo.currentData())
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
                "base_note_type": base["name"],
                "lichess_token": self.token_edit.text().strip(),
                "deck_root": self.root_edit.text().strip(),
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
