"""
Qt dialog: load a Chess.com game (exported analysis PGN or link), analyse it and
import the resulting cards.
"""

from __future__ import annotations

import os

from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from aqt.utils import askUser, showWarning, tooltip

from . import anki_ops, chesscom, decks, engine
from .chess_lib import chess
from .dialog import apply_language, get_config, write_config
from .game_analysis import ALL_KINDS, DEFAULT_KINDS, ENGINE_KINDS, AnalysisOptions, analyze_game
from .i18n import tr

COL_CHECK, COL_MOVE, COL_KIND, COL_SOLUTION, COL_EVAL, COL_DECK = range(6)


def error_text(e: Exception) -> str:
    if isinstance(e, (chesscom.ChessComError, engine.EngineError)):
        return tr(e.key, **e.params)
    return str(e)


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


class ChessComImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("cc.title"))
        self.resize(940, 700)
        self.config = get_config()
        self.game: chess.pgn.Game | None = None
        self.cards = []

        layout = QVBoxLayout(self)

        # --- Source ---
        src = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(tr("cc.url_placeholder"))
        self.url_edit.returnPressed.connect(self.on_load_link)
        src.addWidget(self.url_edit, 1)
        for text, slot in (
            (tr("cc.load_link"), self.on_load_link),
            (tr("cc.open_file"), self.on_open_file),
            (tr("cc.paste"), self.on_paste),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            src.addWidget(btn)
        layout.addLayout(src)

        self.summary = QLabel(tr("cc.none"))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        # --- Options ---
        opts = QFormLayout()
        self.side_combo = QComboBox()
        opts.addRow(tr("cc.side"), self.side_combo)

        kinds_box = QGridLayout()
        selected = set(self.config.get("chesscom_kinds") or DEFAULT_KINDS)
        self.kind_checks: dict[str, QCheckBox] = {}
        for i, kind in enumerate(ALL_KINDS):
            check = QCheckBox(tr(f"kind.{kind}"))
            check.setChecked(kind in selected)
            self.kind_checks[kind] = check
            kinds_box.addWidget(check, i // 4, i % 4)
        opts.addRow(tr("cc.cards"), kinds_box)

        engine_row = QHBoxLayout()
        self.engine_label = QLabel()
        self.engine_label.setWordWrap(True)
        btn_download = QPushButton(tr("cc.engine_download"))
        btn_download.clicked.connect(lambda: self.download_engine())
        btn_choose = QPushButton(tr("cc.engine_choose"))
        btn_choose.clicked.connect(self.on_choose_engine)
        engine_row.addWidget(self.engine_label, 1)
        engine_row.addWidget(btn_download)
        engine_row.addWidget(btn_choose)
        opts.addRow("Stockfish:", engine_row)

        time_row = QHBoxLayout()
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0.1, 10.0)
        self.time_spin.setSingleStep(0.1)
        self.time_spin.setValue(float(self.config.get("analysis_time", 0.5)))
        self.analyze_btn = QPushButton(tr("cc.analyze"))
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.on_analyze)
        time_row.addWidget(self.time_spin)
        time_row.addStretch(1)
        time_row.addWidget(self.analyze_btn)
        opts.addRow(tr("cc.move_time"), time_row)
        layout.addLayout(opts)

        # --- Cards ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                tr("cc.table.move"),
                tr("table.kind"),
                tr("cc.table.solution"),
                tr("cc.table.eval"),
                tr("table.deck"),
            ]
        )
        header = self.table.horizontalHeader()
        for col in (COL_CHECK, COL_MOVE, COL_KIND, COL_EVAL):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for col in (COL_SOLUTION, COL_DECK):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # --- Destination ---
        form = QFormLayout()
        self.model_combo = QComboBox()
        for m in anki_ops.find_chess_note_types():
            self.model_combo.addItem(m["name"], m["id"])
        idx = self.model_combo.findText(self.config.get("base_note_type", ""))
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        form.addRow(tr("form.base_note_type"), self.model_combo)
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
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("button.cancel"))
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self.model_combo.count() == 0:
            self.summary.setText(tr("warn.no_note_types"))
        self.refresh_engine_label()

    # --- Engine ---

    def engine_path(self) -> str | None:
        return engine.find_stockfish(self.config.get("stockfish_path", ""))

    def refresh_engine_label(self):
        path = self.engine_path()
        self.engine_label.setText(
            tr("cc.engine_found", path=path) if path else tr("cc.engine_missing")
        )

    def on_choose_engine(self):
        path, _ = QFileDialog.getOpenFileName(self, "Stockfish", "", "")
        if path:
            self.config["stockfish_path"] = path
            write_config(self.config)
            self.refresh_engine_label()

    def download_engine(self, then=None):
        def progress(done, total):
            mb = lambda n: f"{n / 1048576:.0f}"  # noqa: E731
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=tr("cc.engine_downloading", done=mb(done), total=mb(total) if total else "?"),
                    value=done // 1048576,
                    max=total // 1048576 if total else 0,
                )
            )

        def on_success(path):
            self.refresh_engine_label()
            if then:
                then()

        QueryOp(
            parent=self,
            op=lambda col: engine.download_stockfish(progress),
            success=on_success,
        ).failure(lambda e: showWarning(error_text(e), parent=self)).with_progress(
            tr("cc.engine_downloading", done=0, total="?")
        ).without_collection().run_in_background()

    # --- Loading ---

    def on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("cc.open_file"),
            self.config.get("last_dir", ""),
            tr("source.file_filter"),
        )
        if not path:
            return
        self.config["last_dir"] = os.path.dirname(path)
        try:
            with open(path, encoding="utf-8-sig") as f:
                self.load_pgn(f.read())
        except (OSError, UnicodeDecodeError) as e:
            showWarning(tr("warn.read_file", error=e), parent=self)

    def on_paste(self):
        dialog = PasteDialog(self)
        if dialog.exec() and dialog.edit.toPlainText().strip():
            self.load_pgn(dialog.edit.toPlainText())

    def on_load_link(self):
        parsed = chesscom.parse_game_url(self.url_edit.text())
        if not parsed:
            showWarning(tr("chesscom.invalid_url"), parent=self)
            return
        QueryOp(
            parent=self,
            op=lambda col: chesscom.fetch_game_pgn(*parsed),
            success=self.load_pgn,
        ).failure(lambda e: showWarning(error_text(e), parent=self)).with_progress(
            tr("cc.loading")
        ).without_collection().run_in_background()

    def load_pgn(self, text: str):
        try:
            self.game = chesscom.read_game(text)
        except chesscom.ChessComError as e:
            showWarning(error_text(e), parent=self)
            return
        h = self.game.headers
        count = sum(chesscom.move_label(n) in chesscom.ERROR_LABELS for n in self.game.mainline())
        labels = tr("cc.labels_found", count=count) if count else tr("cc.labels_missing")
        self.summary.setText(
            tr(
                "cc.summary",
                white=h.get("White", "?"),
                black=h.get("Black", "?"),
                date=h.get("Date", "?"),
                result=h.get("Result", "*"),
                labels=labels,
            )
        )

        self.side_combo.clear()
        self.side_combo.addItem(tr("cc.side_white", name=h.get("White", "?")), chess.WHITE)
        self.side_combo.addItem(tr("cc.side_black", name=h.get("Black", "?")), chess.BLACK)
        mine = {u.lower() for u in self.config.get("chesscom_usernames", [])}
        if h.get("Black", "").lower() in mine and h.get("White", "").lower() not in mine:
            self.side_combo.setCurrentIndex(1)

        self.cards = []
        self.table.setRowCount(0)
        self.analyze_btn.setEnabled(True)
        self.import_btn.setEnabled(False)

    # --- Analysis ---

    def selected_kinds(self) -> set[str]:
        return {kind for kind, check in self.kind_checks.items() if check.isChecked()}

    def on_analyze(self):
        if not self.game:
            return
        kinds = self.selected_kinds()
        path = self.engine_path()
        if kinds & set(ENGINE_KINDS) and not path:
            if askUser(tr("cc.engine_ask_download"), parent=self):
                self.download_engine(then=self.on_analyze)
            return

        options = AnalysisOptions(
            user_color=self.side_combo.currentData(),
            kinds=kinds,
            move_time=self.time_spin.value(),
            solution_time=max(1.0, self.time_spin.value() * 3),
        )
        game = self.game

        def progress(done, total):
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=tr("cc.analyzing", done=done, total=total), value=done, max=total
                )
            )

        def task(col):
            if not (kinds & set(ENGINE_KINDS)):
                return analyze_game(game, options)
            with engine.open_engine(path) as sf:
                return analyze_game(game, options, sf, progress)

        QueryOp(parent=self, op=task, success=self.show_cards).failure(
            lambda e: showWarning(error_text(e), parent=self)
        ).with_progress(tr("cc.analyzing", done=0, total="?")).without_collection().run_in_background()

    def show_cards(self, cards):
        self.cards = sorted(cards, key=lambda c: (c.ply, c.kind))
        self.table.setRowCount(len(self.cards))
        for row, card in enumerate(self.cards):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, COL_CHECK, check)
            for col, value in (
                (COL_MOVE, card.move_text),
                (COL_KIND, tr(f"kind.{card.kind}")),
                (COL_SOLUTION, card.solution_text),
                (COL_EVAL, card.eval_text),
                (COL_DECK, ""),
            ):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip(card.name)
                self.table.setItem(row, col, item)
        self.refresh_decks()
        self.import_btn.setEnabled(bool(self.cards) and self.model_combo.count() > 0)
        if not self.cards:
            tooltip(tr("cc.no_cards"), parent=self)

    def placement(self, card) -> decks.Placement:
        return decks.place_game_card(card, decks.root_name(self.root_edit.text()))

    def refresh_decks(self):
        for row, card in enumerate(self.cards):
            placement = self.placement(card)
            item = self.table.item(row, COL_DECK)
            item.setText(placement.deck)
            item.setToolTip("\n".join([placement.deck, *placement.tags]))

    # --- Import ---

    def on_import(self):
        selected = [
            card
            for row, card in enumerate(self.cards)
            if self.table.item(row, COL_CHECK).checkState() == Qt.CheckState.Checked
        ]
        if not selected:
            showWarning(tr("warn.no_selection"), parent=self)
            return
        base = mw.col.models.get(self.model_combo.currentData())
        if not base:
            showWarning(tr("warn.base_missing"), parent=self)
            return
        try:
            models = {m: anki_ops.ensure_mode_note_type(base, m) for m in {c.mode for c in selected}}
        except anki_ops.ChessImportError as e:
            showWarning(str(e), parent=self)
            return
        rows = [(card, models[card.mode], self.placement(card)) for card in selected]

        side = self.side_combo.currentData()
        username = self.game.headers.get("White" if side == chess.WHITE else "Black", "")
        usernames = list(dict.fromkeys([*self.config.get("chesscom_usernames", []), username]))
        update_existing = self.update_existing.isChecked()
        self.config.update(
            {
                "chesscom_usernames": [u for u in usernames if u and u != "?"],
                "deck_root": self.root_edit.text().strip(),
                "chesscom_kinds": sorted(self.selected_kinds()),
                "analysis_time": self.time_spin.value(),
                "base_note_type": base["name"],
                "update_existing": update_existing,
            }
        )
        write_config(self.config)

        stats = {"created": 0, "updated": 0, "skipped": 0}

        def on_success(_changes):
            tooltip(tr("cc.result", **stats), parent=mw)
            self.accept()

        CollectionOp(
            parent=self,
            op=lambda col: anki_ops.import_chapters(
                col, rows, update_existing, False, stats, tr("cc.undo")
            ),
        ).success(on_success).run_in_background()


def show_chesscom_dialog():
    if not mw.col:
        return
    apply_language()
    ChessComImportDialog(mw).exec()
