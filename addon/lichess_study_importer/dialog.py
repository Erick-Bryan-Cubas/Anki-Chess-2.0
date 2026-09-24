"""
Qt dialog: load a Lichess study (file or URL), pick chapters/modes and import.
"""

from __future__ import annotations

import os

import anki.lang
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
from aqt.utils import showWarning, tooltip

from . import anki_ops
from .i18n import resolve_language, set_language, tr
from .lichess_api import LichessError, fetch_study_pgn, parse_study_url
from .pgn_split import (
    KIND_EMPTY,
    KIND_EXERCISE,
    KIND_GAME,
    MODE_FLIPPED,
    MODE_PUZZLE,
    MODE_STUDY,
    Chapter,
    split_games,
)

KIND_KEYS = {KIND_EXERCISE: "kind.exercise", KIND_GAME: "kind.game", KIND_EMPTY: "kind.empty"}
MODES = [(MODE_PUZZLE, "mode.puzzle"), (MODE_FLIPPED, "mode.flipped"), (MODE_STUDY, "mode.study")]
COL_CHECK, COL_NAME, COL_KIND, COL_MODE, COL_PREVIEW = range(5)


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
        btn_all.clicked.connect(lambda: self.set_checked(KIND_EXERCISE, True))
        btn_none = QPushButton(tr("filter.uncheck_all"))
        btn_none.clicked.connect(self.uncheck_all)
        filters.addWidget(self.include_games)
        filters.addStretch(1)
        filters.addWidget(btn_all)
        filters.addWidget(btn_none)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["", tr("table.chapter"), tr("table.kind"), tr("table.mode"), tr("table.moves")]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_KIND, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_MODE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PREVIEW, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        hint = QLabel(tr("modes.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # --- Destination ---
        form = QFormLayout()
        self.model_combo = QComboBox()
        for m in anki_ops.find_chess_note_types():
            self.model_combo.addItem(m["name"], m["id"])
        preferred = self.config.get("base_note_type", "")
        idx = self.model_combo.findText(preferred) if preferred else -1
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        form.addRow(tr("form.base_note_type"), self.model_combo)

        self.deck_edit = QLineEdit()
        form.addRow(tr("form.deck"), self.deck_edit)

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
        if not self.chapters:
            showWarning(tr("warn.no_chapters"), parent=self)
            return

        study = next((c.study_name for c in self.chapters if c.study_name), "") or source
        counts = {k: sum(c.kind == k for c in self.chapters) for k in KIND_KEYS}
        self.study_label.setText(
            tr(
                "study.summary",
                study=study,
                total=len(self.chapters),
                exercises=counts[KIND_EXERCISE],
                games=counts[KIND_GAME],
                empty=counts[KIND_EMPTY],
            )
        )
        prefix = self.config.get("deck_prefix", "Lichess").strip(":")
        self.deck_edit.setText(f"{prefix}::{study}" if prefix else study)
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(len(self.chapters))
        include_games = self.include_games.isChecked()
        for row, ch in enumerate(self.chapters):
            kind = ch.kind
            check = QTableWidgetItem()
            flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            if kind == KIND_EMPTY:
                flags = Qt.ItemFlag.NoItemFlags
            check.setFlags(flags)
            checked = kind == KIND_EXERCISE or (kind == KIND_GAME and include_games)
            check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, COL_CHECK, check)

            for col, value in (
                (COL_NAME, ch.name),
                (COL_KIND, tr(KIND_KEYS[kind])),
                (COL_PREVIEW, ch.preview),
            ):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if col == COL_NAME and ch.chapter_url:
                    item.setToolTip(ch.chapter_url)
                self.table.setItem(row, col, item)

            combo = QComboBox()
            for key, label_key in MODES:
                combo.addItem(tr(label_key), key)
            combo.setCurrentIndex([k for k, _ in MODES].index(ch.suggested_mode))
            combo.setEnabled(kind != KIND_EMPTY)
            self.table.setCellWidget(row, COL_MODE, combo)

        self.import_btn.setEnabled(self.model_combo.count() > 0)

    # --- Selection helpers ---

    def set_checked(self, kind: str, value: bool):
        for row, ch in enumerate(self.chapters):
            if ch.kind == kind:
                state = Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
                self.table.item(row, COL_CHECK).setCheckState(state)

    def uncheck_all(self):
        for kind in (KIND_EXERCISE, KIND_GAME):
            self.set_checked(kind, False)

    def on_toggle_games(self, checked: bool):
        self.set_checked(KIND_GAME, checked)

    def selected_rows(self) -> list[tuple[Chapter, str]]:
        rows = []
        for row, ch in enumerate(self.chapters):
            if ch.kind == KIND_EMPTY:
                continue
            if self.table.item(row, COL_CHECK).checkState() != Qt.CheckState.Checked:
                continue
            rows.append((ch, self.table.cellWidget(row, COL_MODE).currentData()))
        return rows

    # --- Import ---

    def on_import(self):
        selected = self.selected_rows()
        if not selected:
            showWarning(tr("warn.no_selection"), parent=self)
            return
        deck_name = self.deck_edit.text().strip()
        if not deck_name:
            showWarning(tr("warn.no_deck"), parent=self)
            return
        base = mw.col.models.get(self.model_combo.currentData())
        if not base:
            showWarning(tr("warn.base_missing"), parent=self)
            return

        # Note types are created up front (outside the undoable note import)
        try:
            models = {
                mode: anki_ops.ensure_mode_note_type(base, mode)
                for mode in {mode for _, mode in selected}
            }
        except anki_ops.ChessImportError as e:
            showWarning(str(e), parent=self)
            return
        rows = [(ch, models[mode]) for ch, mode in selected]

        update_existing = self.update_existing.isChecked()
        strip_anno = bool(self.config.get("strip_anno", True))
        stats = {"created": 0, "updated": 0, "skipped": 0}

        self.config.update(
            {
                "include_games": self.include_games.isChecked(),
                "update_existing": update_existing,
                "base_note_type": base["name"],
                "lichess_token": self.token_edit.text().strip(),
            }
        )
        write_config(self.config)

        def on_success(_changes):
            tooltip(tr("result.summary", **stats), parent=mw)
            self.accept()

        CollectionOp(
            parent=self,
            op=lambda col: anki_ops.import_chapters(
                col, rows, deck_name, update_existing, strip_anno, stats
            ),
        ).success(on_success).run_in_background()


def show_import_dialog():
    if not mw.col:
        return
    apply_language()
    StudyImportDialog(mw).exec()
