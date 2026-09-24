"""
Qt dialog: load a Lichess study (file or URL), pick chapters/modes and import.
"""

from __future__ import annotations

import os

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

KIND_LABELS = {KIND_EXERCISE: "Exercício", KIND_GAME: "Partida", KIND_EMPTY: "Vazio"}
MODES = [(MODE_PUZZLE, "Puzzle"), (MODE_FLIPPED, "Flipped"), (MODE_STUDY, "Study")]
COL_CHECK, COL_NAME, COL_KIND, COL_MODE, COL_PREVIEW = range(5)


def get_config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def write_config(config: dict) -> None:
    mw.addonManager.writeConfig(__name__, config)


class StudyImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Importar estudo do Lichess")
        self.resize(900, 620)
        self.config = get_config()
        self.chapters: list[Chapter] = []

        layout = QVBoxLayout(self)

        # --- Source ---
        src = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://lichess.org/study/XXXXXXXX  (ou /capítulo)")
        self.url_edit.returnPressed.connect(self.on_load_url)
        btn_url = QPushButton("Carregar URL")
        btn_url.clicked.connect(self.on_load_url)
        btn_file = QPushButton("Abrir arquivo .pgn…")
        btn_file.clicked.connect(self.on_open_file)
        src.addWidget(self.url_edit, 1)
        src.addWidget(btn_url)
        src.addWidget(btn_file)
        layout.addLayout(src)

        token_row = QHBoxLayout()
        self.token_edit = QLineEdit(self.config.get("lichess_token", ""))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Token do Lichess (opcional, escopo study:read) para estudos privados")
        self.token_edit.setToolTip(
            "Crie em https://lichess.org/account/oauth/token com o escopo 'study:read'.\n"
            "Fica salvo em texto puro na configuração do add-on."
        )
        token_row.addWidget(QLabel("Token:"))
        token_row.addWidget(self.token_edit, 1)
        layout.addLayout(token_row)

        self.study_label = QLabel("Nenhum estudo carregado.")
        self.study_label.setWordWrap(True)
        layout.addWidget(self.study_label)

        # --- Chapter table ---
        filters = QHBoxLayout()
        self.include_games = QCheckBox("Incluir partidas completas")
        self.include_games.setChecked(bool(self.config.get("include_games", False)))
        self.include_games.toggled.connect(self.on_toggle_games)
        btn_all = QPushButton("Marcar exercícios")
        btn_all.clicked.connect(lambda: self.set_checked(KIND_EXERCISE, True))
        btn_none = QPushButton("Desmarcar tudo")
        btn_none.clicked.connect(self.uncheck_all)
        filters.addWidget(self.include_games)
        filters.addStretch(1)
        filters.addWidget(btn_all)
        filters.addWidget(btn_none)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Capítulo", "Tipo", "Modo", "Lances"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_KIND, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_MODE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PREVIEW, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        hint = QLabel(
            "<small><b>Puzzle</b>: você joga o lado que move na posição. "
            "<b>Flipped</b>: o 1º lance é do adversário (\"Jogam as brancas\"). "
            "<b>Study</b>: você joga os dois lados. "
            "Cada modo usa um note type próprio (criado a partir do note type base, se não existir).</small>"
        )
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
        form.addRow("Note type base:", self.model_combo)

        self.deck_edit = QLineEdit()
        form.addRow("Baralho:", self.deck_edit)

        self.update_existing = QCheckBox("Atualizar notas já importadas (senão, pula)")
        self.update_existing.setChecked(bool(self.config.get("update_existing", False)))
        form.addRow("", self.update_existing)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.import_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_btn.setText("Importar")
        self.import_btn.setEnabled(False)
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self.model_combo.count() == 0:
            self.study_label.setText(
                "<b>Nenhum note type AnkiChess encontrado.</b> Instale o template AnkiChess "
                "(apkg ou Companion Add-on) antes de importar."
            )

    # --- Loading ---

    def on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir estudo do Lichess", self.config.get("last_dir", ""), "PGN (*.pgn);;Todos (*)"
        )
        if not path:
            return
        self.config["last_dir"] = os.path.dirname(path)
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            showWarning(f"Não foi possível ler o arquivo:\n{e}", parent=self)
            return
        self.load_pgn(text, os.path.basename(path))

    def on_load_url(self):
        parsed = parse_study_url(self.url_edit.text())
        if not parsed:
            showWarning("Informe um link de estudo do Lichess (lichess.org/study/…).", parent=self)
            return
        study_id, chapter_id = parsed
        token = self.token_edit.text()
        self.study_label.setText("Baixando estudo…")

        def on_done(fut):
            try:
                text = fut.result()
            except LichessError as e:
                self.study_label.setText("Falha ao baixar o estudo.")
                showWarning(str(e), parent=self)
                return
            self.load_pgn(text, f"lichess.org/study/{study_id}")

        mw.taskman.run_in_background(
            lambda: fetch_study_pgn(study_id, chapter_id, token=token), on_done
        )

    def load_pgn(self, text: str, source: str):
        self.chapters = split_games(text)
        if not self.chapters:
            showWarning("Nenhum capítulo encontrado no PGN.", parent=self)
            return

        study = next((c.study_name for c in self.chapters if c.study_name), "") or source
        counts = {k: sum(c.kind == k for c in self.chapters) for k in KIND_LABELS}
        self.study_label.setText(
            f"<b>{study}</b> — {len(self.chapters)} capítulos: "
            f"{counts[KIND_EXERCISE]} exercícios, {counts[KIND_GAME]} partidas, {counts[KIND_EMPTY]} vazios."
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
                (COL_KIND, KIND_LABELS[kind]),
                (COL_PREVIEW, ch.preview),
            ):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if col == COL_NAME and ch.chapter_url:
                    item.setToolTip(ch.chapter_url)
                self.table.setItem(row, col, item)

            combo = QComboBox()
            for key, label in MODES:
                combo.addItem(label, key)
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
            showWarning("Nenhum capítulo selecionado.", parent=self)
            return
        deck_name = self.deck_edit.text().strip()
        if not deck_name:
            showWarning("Informe o nome do baralho.", parent=self)
            return
        base = mw.col.models.get(self.model_combo.currentData())
        if not base:
            showWarning("Note type base não encontrado.", parent=self)
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
            tooltip(
                f"Lichess: {stats['created']} criadas, {stats['updated']} atualizadas, "
                f"{stats['skipped']} já existentes puladas.",
                parent=mw,
            )
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
    StudyImportDialog(mw).exec()
