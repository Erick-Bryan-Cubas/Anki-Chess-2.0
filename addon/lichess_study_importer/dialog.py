"""
Qt dialog: load Lichess studies (links, a user's studies, .pgn files or pasted PGN),
choose each chapter's type, side, note type and deck, and import them.

The table shows self.rows, one Row per chapter holding what was chosen for it, so
sorting and filtering rebuild the widgets without losing the choices.
"""

from __future__ import annotations

import html
import io
import os
import textwrap
from dataclasses import dataclass, field

import aqt
from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import askUser, openLink, showWarning, tooltip

from . import anki_ops, decks, expand
from .chess_lib import chess
from .i18n import tr
from .lichess_api import LichessError, fetch_study_pgn, fetch_user_studies, parse_study_urls
from .pgn_split import (
    COMMAND_RE,
    KIND_EMPTY,
    KIND_EXERCISE,
    KIND_GAME,
    KIND_LINE,
    KIND_UNSUPPORTED,
    MODE_FLIPPED,
    MODE_STUDY,
    Chapter,
    mode_for,
    split_games,
)
from .ui_common import (
    BoardPreview,
    apply_language,
    ask_pgn,
    error_text,
    get_config,
    readonly_item,
    restore_layout,
    save_layout,
    write_config,
)

KIND_KEYS = {
    KIND_EXERCISE: "kind.exercise",
    KIND_LINE: "kind.line",
    KIND_GAME: "kind.game",
    KIND_EMPTY: "kind.empty",
    KIND_UNSUPPORTED: "kind.unsupported",
}
CHAPTER_KINDS = (KIND_EXERCISE, KIND_LINE, KIND_GAME)  # the kind decides the subdeck
NOT_IMPORTABLE = (KIND_EMPTY, KIND_UNSUPPORTED)
SIDES = (("w", "side.white"), ("b", "side.black"), (None, "side.both"))  # None: Study
OTHER_SIDE = {"w": "b", "b": "w"}
STATUS_KEYS = {"new": "status.new", "same": "status.same", "changed": "status.changed"}
(
    COL_CHECK,
    COL_NAME,
    COL_STATUS,
    COL_KIND,
    COL_SIDE,
    COL_NOTE_TYPE,
    COL_DECK,
    COL_PREVIEW,
) = range(8)
COLUMN_WIDTHS = {
    COL_CHECK: 28,
    COL_NAME: 250,
    COL_STATUS: 90,
    COL_KIND: 140,
    COL_SIDE: 110,
    COL_NOTE_TYPE: 190,
    COL_DECK: 160,
}
LAYOUT_KEY = "lichessStudyImport2"  # window size and columns, kept in the Anki profile


@dataclass(eq=False)
class Study:
    key: str | None  # Lichess study id: renamed decks are kept per study
    name: str
    fallback: str  # deck name for PGNs without StudyName (the file name)
    default_deck: str
    deck: str
    complete: bool  # the whole study was loaded: chapters removed from it can be found


@dataclass(eq=False)
class Row:
    chapter: Chapter
    study: Study
    kind: str
    side: str | None
    note_type: str = ""
    subdeck: str | None = None  # renamed in the Deck column (None: the kind's default)
    checked: bool = False
    status: str = ""
    cache: dict = field(default_factory=dict)  # opening name, parsed game

    @property
    def importable(self) -> bool:
        return self.kind not in NOT_IMPORTABLE


class DeckItem(QTableWidgetItem):
    """Deck cell; an empty subdeck (the chapter goes to the study deck) says so when shown."""

    def data(self, role):
        value = super().data(role)
        editable = self.flags() & Qt.ItemFlag.ItemIsEditable
        if role == Qt.ItemDataRole.DisplayRole and not value and editable:
            return tr("deck.study_itself")
        return value


class UserStudiesDialog(QDialog):
    """Lists the studies of a Lichess user to pick the ones to load."""

    def __init__(self, parent, username: str, token: str):
        super().__init__(parent)
        self.setWindowTitle(tr("user_studies.title"))
        self.resize(560, 480)
        self.token = token
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.user_edit = QLineEdit(username)
        self.user_edit.setPlaceholderText(tr("user_studies.username"))
        self.user_edit.returnPressed.connect(self.on_list)
        btn = QPushButton(tr("user_studies.list"))
        btn.clicked.connect(self.on_list)
        row.addWidget(QLabel(tr("user_studies.username")))
        row.addWidget(self.user_edit, 1)
        row.addWidget(btn)
        layout.addLayout(row)
        self.status = QLabel(tr("user_studies.private_hint"))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("user_studies.load"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("button.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if username:
            self.on_list()

    def on_list(self):
        username = self.user_edit.text().strip()
        if not username:
            return
        self.status.setText(tr("user_studies.loading"))
        QueryOp(
            parent=self,
            op=lambda col: fetch_user_studies(username, self.token),
            success=self.show_studies,
        ).failure(lambda e: self.status.setText(error_text(e))).without_collection().run_in_background()

    def show_studies(self, studies: list[dict]):
        self.list.clear()
        for study in studies:
            item = QListWidgetItem(study.get("name", study["id"]))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, study["id"])
            item.setToolTip(f"https://lichess.org/study/{study['id']}")
            self.list.addItem(item)
        self.status.setText(tr("user_studies.found", count=len(studies)) if studies else tr("user_studies.none"))

    def selected_ids(self) -> list[str]:
        items = (self.list.item(i) for i in range(self.list.count()))
        return [i.data(Qt.ItemDataRole.UserRole) for i in items if i.checkState() == Qt.CheckState.Checked]


class StudyImportDialog(QDialog):
    def __init__(self, parent=None, urls: str = ""):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("dialog.title"))
        self.config = get_config()
        self.studies: list[Study] = []
        self.rows: list[Row] = []
        self.load_errors: list[str] = []
        self.removed_nids: list[int] = []
        self.last_result = ""
        self._populating = False  # cells being filled by the dialog, not edited
        self._spreading = False  # a change being copied to the other selected rows
        self._sort = (None, Qt.SortOrder.AscendingOrder)

        # Flipped/Study note types are cloned from the base one; the root deck and the
        # base are config settings (deck_root, base_note_type), not asked every time
        self.base = anki_ops.default_base(self.config.get("base_note_type", ""))
        self.root = decks.root_name(self.config.get("deck_root"))
        # Note types a chapter can use: (name, mode, exists)
        self.choices = anki_ops.note_type_choices(self.base) if self.base else []
        self.choice_modes = {name: mode for name, mode, _ in self.choices}
        base_name = self.base["name"] if self.base else "AnkiChess"

        layout = QVBoxLayout(self)

        # --- Sources ---
        src = QHBoxLayout()
        self.url_edit = QLineEdit(urls)
        self.url_edit.setPlaceholderText(tr("source.url_placeholder"))
        self.url_edit.returnPressed.connect(self.on_load_url)
        self.url_btn = QPushButton(tr("source.load_url"))
        self.url_btn.clicked.connect(self.on_load_url)
        src.addWidget(self.url_edit, 1)
        src.addWidget(self.url_btn)
        for key, slot in (
            ("source.user_studies", self.on_user_studies),
            ("source.open_file", self.on_open_file),
            ("source.paste", self.on_paste),
        ):
            btn = QPushButton(tr(key))
            btn.clicked.connect(slot)
            src.addWidget(btn)
        self.token_btn = QPushButton(tr("token.show"))
        self.token_btn.setFlat(True)
        self.token_btn.setToolTip(tr("token.tooltip"))
        self.token_btn.clicked.connect(lambda: self.show_token(True))
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
        self.study_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.study_label.linkActivated.connect(self.on_summary_link)
        layout.addWidget(self.study_label)

        # Study deck, editable once a study is loaded (a list picks the study when several)
        self.deck_row = QWidget()
        deck_layout = QHBoxLayout(self.deck_row)
        deck_layout.setContentsMargins(0, 0, 0, 0)
        self.study_combo = QComboBox()
        self.study_combo.currentIndexChanged.connect(self.on_study_selected)
        self.deck_edit = QLineEdit()
        self.deck_edit.setToolTip(tr("form.study_deck_tip"))
        self.deck_edit.textEdited.connect(self.on_study_deck_typed)
        self.deck_edit.editingFinished.connect(self.on_study_deck_edited)
        deck_reset = QPushButton(tr("form.study_deck_reset"))
        deck_reset.setToolTip(tr("form.study_deck_reset_tip"))
        deck_reset.clicked.connect(self.reset_decks)
        deck_layout.addWidget(QLabel(tr("form.study_deck")))
        deck_layout.addWidget(self.study_combo)
        deck_layout.addWidget(self.deck_edit, 1)
        deck_layout.addWidget(deck_reset)
        layout.addWidget(self.deck_row)
        self.deck_row.setVisible(False)

        # --- Options and selection ---
        options = QHBoxLayout()
        self.include_games = QCheckBox(tr("filter.include_games"))
        self.include_games.setChecked(bool(self.config.get("include_games", False)))
        self.include_games.toggled.connect(self.on_toggle_games)
        self.split_lines = QCheckBox(tr("option.split_lines"))
        self.split_lines.setToolTip(tr("option.split_lines_tip"))
        self.split_lines.setChecked(bool(self.config.get("split_lines", False)))
        self.key_moves = QCheckBox(tr("option.key_moves"))
        self.key_moves.setToolTip(tr("option.key_moves_tip"))
        self.key_moves.setChecked(bool(self.config.get("key_moves", False)))
        for check in (self.split_lines, self.key_moves):
            check.toggled.connect(self.on_expand_option)
        for widget in (self.include_games, self.split_lines, self.key_moves):
            options.addWidget(widget)
        options.addStretch(1)
        layout.addLayout(options)

        selection = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(tr("filter.placeholder"))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self.apply_filter)
        selection.addWidget(self.filter_edit, 1)
        for key, slot in (
            ("filter.check_new", self.check_new_and_changed),
            ("filter.check_exercises", self.check_exercises_and_lines),
            ("filter.uncheck_all", self.uncheck_all),
        ):
            btn = QPushButton(tr(key))
            btn.clicked.connect(slot)
            selection.addWidget(btn)
        layout.addLayout(selection)

        # --- Chapter table, with the board of the selected chapter beside it ---
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                tr("table.chapter"),
                tr("table.status"),
                tr("table.kind"),
                tr("table.side"),
                tr("table.note_type"),
                tr("table.deck"),
                tr("table.moves"),
            ]
        )
        for col, tip in (
            (COL_STATUS, tr("table.status_tip")),
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
        self.table.currentCellChanged.connect(lambda row, *_: self.show_preview(row))
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.on_sort)

        self.preview = BoardPreview()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setCollapsible(0, False)
        layout.addWidget(splitter, 1)
        restore_layout(self, self.table, LAYOUT_KEY, (1250, 720))

        hint = QLabel(tr("table.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.update_existing = QCheckBox(tr("form.update_existing"))
        self.update_existing.setChecked(bool(self.config.get("update_existing", False)))
        layout.addWidget(self.update_existing)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close
        )
        self.import_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.import_btn.setText(tr("button.import"))
        self.import_btn.setEnabled(False)
        # Standard buttons follow Anki's language; keep them in the add-on's language
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr("button.close"))
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if not self.base:
            self.study_label.setText(tr("warn.no_note_types"))
        elif urls:
            self.on_load_url()

    def done(self, result: int):
        save_layout(self, self.table, LAYOUT_KEY)
        super().done(result)

    def show_token(self, visible: bool):
        self.token_row.setVisible(visible)
        self.token_btn.setVisible(not visible)

    # --- Loading ---

    def on_open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("source.file_dialog_title"),
            self.config.get("last_dir", ""),
            tr("source.file_filter"),
        )
        if not paths:
            return
        self.config["last_dir"] = os.path.dirname(paths[0])
        sources = []
        for path in paths:
            try:
                with open(path, encoding="utf-8-sig") as f:
                    sources.append((f.read(), os.path.splitext(os.path.basename(path))[0], True))
            except (OSError, UnicodeDecodeError) as e:
                showWarning(tr("warn.read_file", error=e), parent=self)
        if sources:
            self.load_sources(sources)

    def on_paste(self):
        text = ask_pgn(self)
        if text:
            self.load_sources([(text, tr("source.pasted"), True)])

    def on_user_studies(self):
        dialog = UserStudiesDialog(self, self.config.get("lichess_username", ""), self.token_edit.text())
        if not dialog.exec():
            return
        self.config["lichess_username"] = dialog.user_edit.text().strip()
        ids = dialog.selected_ids()
        if ids:
            self.url_edit.setText(" ".join(f"https://lichess.org/study/{i}" for i in ids))
            self.on_load_url()

    def on_load_url(self):
        studies = parse_study_urls(self.url_edit.text())
        if not studies:
            showWarning(tr("warn.invalid_url"), parent=self)
            return
        token = self.token_edit.text()
        self.study_label.setText(tr("study.downloading"))
        self.url_btn.setEnabled(False)

        def fetch_all():
            results = []
            for i, (study_id, chapter_id) in enumerate(studies, 1):
                mw.taskman.run_on_main(
                    lambda i=i: self.study_label.setText(tr("study.downloading_n", done=i, total=len(studies)))
                )
                try:
                    text = fetch_study_pgn(study_id, chapter_id, token=token)
                    results.append((text, f"lichess.org/study/{study_id}", chapter_id is None))
                except LichessError as e:
                    results.append((e, study_id, False))
            return results

        def on_done(fut):
            self.url_btn.setEnabled(True)
            sources, errors = [], []
            for value, source, complete in fut.result():
                if isinstance(value, LichessError):
                    errors.append(f"{source}: {error_text(value)}")
                    if value.key == "error.no_access":
                        self.show_token(True)  # private study: the token is the way in
                else:
                    sources.append((value, source, complete))
            if errors:
                showWarning(tr("study.load_errors", errors="\n".join(errors)), parent=self)
            if sources:
                self.load_sources(sources)
            elif errors:
                self.study_label.setText(tr("study.download_failed"))

        mw.taskman.run_in_background(fetch_all, on_done)

    def load_sources(self, sources: list[tuple[str, str, bool]]):
        """(PGN text, source name, whole study?) of each loaded study or file."""
        study_decks = self.config.get("study_decks", {})
        chapter_decks = self.config.get("chapter_decks", {})
        self.studies, self.rows = [], []
        for text, source, complete in sources:
            by_study: dict[str, Study] = {}
            for ch in split_games(text):
                group = ch.study_id or ch.study_name or source
                study = by_study.get(group)
                if study is None:
                    default = decks.study_deck(ch, self.root, source)
                    key = ch.study_id
                    study = Study(
                        key=key,
                        name=decks.study_name(ch, source),
                        fallback=source,
                        default_deck=default,
                        deck=(study_decks.get(key) if key else None) or default,
                        complete=complete and bool(key),
                    )
                    by_study[group] = study
                    self.studies.append(study)
                row = Row(chapter=ch, study=study, kind=decks.suggest_kind(ch), side=ch.player)
                row.note_type = self.note_type_for_mode(mode_for(row.side, ch.side_to_move))
                if ch.dedupe_key in chapter_decks:
                    row.subdeck = chapter_decks[ch.dedupe_key]
                self.rows.append(row)
        if not self.rows:
            showWarning(tr("warn.no_chapters"), parent=self)
            return

        self.refresh_statuses()
        include_games = self.include_games.isChecked()
        for row in self.rows:
            wanted = row.kind in (KIND_EXERCISE, KIND_LINE) or (row.kind == KIND_GAME and include_games)
            row.checked = row.importable and wanted and row.status != "same"
        self.find_removed_chapters()
        self.last_result = ""
        self._sort = (None, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setSortIndicatorShown(False)

        self.study_combo.blockSignals(True)
        self.study_combo.clear()
        for study in self.studies:
            self.study_combo.addItem(study.name)
        self.study_combo.blockSignals(False)
        self.study_combo.setVisible(len(self.studies) > 1)
        self.deck_row.setVisible(True)
        self.on_study_selected(0)
        self.populate_table()

    def find_removed_chapters(self):
        """Notes of the loaded studies whose chapter was deleted on Lichess."""
        self.removed_nids = []
        for study in self.studies:
            if study.complete:
                ids = {r.chapter.chapter_id for r in self.rows if r.study is study}
                self.removed_nids += anki_ops.removed_chapter_notes(mw.col, study.key, ids)

    def summary_text(self) -> str:
        counts = {k: sum(r.kind == k for r in self.rows) for k in KIND_KEYS}
        params = dict(
            total=len(self.rows),
            exercises=counts[KIND_EXERCISE],
            lines=counts[KIND_LINE],
            games=counts[KIND_GAME],
            empty=counts[KIND_EMPTY] + counts[KIND_UNSUPPORTED],
        )
        if len(self.studies) == 1:
            text = tr("study.summary", study=self.studies[0].name, **params)
        else:
            text = tr("study.summary_many", count=len(self.studies), **params)
        statuses = {s: sum(r.status == s for r in self.rows) for s in STATUS_KEYS}
        text += "<br>" + tr("study.status_counts", **statuses)
        if self.removed_nids:
            text += " " + tr("study.removed", count=len(self.removed_nids))
        if self.last_result:
            text += f"<br><b>{self.last_result}</b>"
        return text

    def on_summary_link(self, link: str):
        if link == "removed" and self.removed_nids:
            nids = ",".join(str(n) for n in self.removed_nids)
            aqt.dialogs.open("Browser", mw, search=(f"nid:{nids}",))

    # --- Note types and cards ---

    def note_type_for_mode(self, mode: str) -> str:
        """The first note type set up for a mode: the base one's variant, else another."""
        return next((name for name, m, _ in self.choices if m == mode), "")

    def row_cards(self, row: Row) -> list[tuple[Chapter, bool]]:
        """(card, is a key move card) imported from a row, depending on the options."""
        ch = row.chapter
        if row.kind == KIND_LINE and self.split_lines.isChecked():
            key = ("split", ch.dedupe_key)
            if key not in row.cache:
                row.cache[key] = expand.split_variations(ch, self.strip_anno)
            return [(card, False) for card in row.cache[key]]
        cards = [(ch, False)]
        if row.kind == KIND_GAME and self.key_moves.isChecked():
            if "key_moves" not in row.cache:
                row.cache["key_moves"] = expand.key_move_cards(ch, self.strip_anno)
            cards += [(card, True) for card in row.cache["key_moves"]]
        return cards

    @property
    def strip_anno(self) -> bool:
        return bool(self.config.get("strip_anno", True))

    def refresh_statuses(self):
        for row in self.rows:
            if not row.importable:
                row.status = ""
                continue
            found = {anki_ops.card_status(mw.col, card, self.strip_anno)[0] for card, _ in self.row_cards(row)}
            row.status = found.pop() if len(found) == 1 else "changed"

    # --- Table ---

    def populate_table(self):
        self._populating = True
        self.table.setRowCount(0)  # drops the widgets of the previous rows
        self.table.setRowCount(len(self.rows))
        for i, row in enumerate(self.rows):
            self.fill_row(i, row)
        self._populating = False
        self.refresh_decks()
        self.apply_filter()
        self.study_label.setText(self.summary_text())
        self.update_import_button()

    def fill_row(self, i: int, row: Row):
        ch = row.chapter
        check = QTableWidgetItem()
        flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        check.setFlags((flags if row.importable else Qt.ItemFlag.NoItemFlags) | Qt.ItemFlag.ItemIsSelectable)
        check.setCheckState(Qt.CheckState.Checked if row.checked else Qt.CheckState.Unchecked)
        self.table.setItem(i, COL_CHECK, check)

        study = f"{row.study.name}\n" if len(self.studies) > 1 else ""
        url_tip = "\n".join(filter(None, [ch.chapter_url, ch.chapter_url and tr("table.open_tip")]))
        self.table.setItem(i, COL_NAME, readonly_item(ch.name, f"{study}{ch.name}\n{url_tip}".strip()))
        status = STATUS_KEYS.get(row.status)
        cards = len(self.row_cards(row)) if row.importable else 0
        status_tip = tr(f"{status}_tip") if status else ""
        if cards > 1:
            status_tip += "\n" + tr("status.cards", count=cards)
        self.table.setItem(i, COL_STATUS, readonly_item(tr(status) if status else "", status_tip.strip()))
        deck_item = DeckItem("")
        deck_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        if row.importable:
            # Renamed with a double-click or F2, see on_item_changed
            deck_item.setFlags(deck_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(i, COL_DECK, deck_item)
        moves = textwrap.fill(ch.moves_preview(600), 80)
        self.table.setItem(i, COL_PREVIEW, readonly_item(ch.moves_preview(200), moves))

        if not row.importable:
            # Nothing to import: plain text instead of combos
            tip = tr("kind.unsupported_tip", variant=ch.variant) if row.kind == KIND_UNSUPPORTED else ""
            for col, text in ((COL_KIND, tr(KIND_KEYS[row.kind])), (COL_SIDE, "—"), (COL_NOTE_TYPE, "—")):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setToolTip(tip)
                self.table.setItem(i, col, item)
            return

        kind_combo = QComboBox()
        for key in CHAPTER_KINDS:
            kind_combo.addItem(tr(KIND_KEYS[key]), key)
        kind_combo.setCurrentIndex(CHAPTER_KINDS.index(row.kind))
        kind_combo.currentIndexChanged.connect(lambda _, r=row: self.on_kind_changed(r))
        self.table.setCellWidget(i, COL_KIND, kind_combo)

        side_combo = QComboBox()
        for side, label_key in SIDES:
            side_combo.addItem(tr(label_key), side)
        side_combo.setCurrentIndex([s for s, _ in SIDES].index(row.side))
        side_combo.setToolTip(tr("side.tooltip", side=tr(f"side.to_move.{ch.side_to_move}")))
        side_combo.currentIndexChanged.connect(lambda _, r=row: self.on_side_changed(r))
        self.table.setCellWidget(i, COL_SIDE, side_combo)

        note_type_combo = QComboBox()
        for name, _, exists in self.choices:
            note_type_combo.addItem(name if exists else f"{name} {tr('note_type.new')}", name)
            if not exists:
                note_type_combo.setItemData(
                    note_type_combo.count() - 1, tr("note_type.new_tip"), Qt.ItemDataRole.ToolTipRole
                )
        note_type_combo.setCurrentIndex(max(0, note_type_combo.findData(row.note_type)))
        note_type_combo.currentIndexChanged.connect(lambda _, r=row: self.on_note_type_changed(r))
        self.table.setCellWidget(i, COL_NOTE_TYPE, note_type_combo)

    def table_row(self, row: Row) -> int:
        return self.rows.index(row)

    def apply_filter(self):
        words = self.filter_edit.text().lower().split()
        for i, row in enumerate(self.rows):
            text = " ".join([row.chapter.name, row.study.name, row.chapter.moves_preview(200)]).lower()
            self.table.setRowHidden(i, not all(w in text for w in words))

    def on_sort(self, col: int):
        keys = {
            COL_CHECK: lambda r: not r.checked,
            COL_NAME: lambda r: (r.study.name.lower(), r.chapter.name.lower()),
            COL_STATUS: lambda r: list(STATUS_KEYS).index(r.status) if r.status in STATUS_KEYS else 9,
            COL_KIND: lambda r: list(KIND_KEYS).index(r.kind),
            COL_SIDE: lambda r: r.side or "z",
            COL_NOTE_TYPE: lambda r: r.note_type,
            COL_DECK: lambda r: self.placement(r).deck.lower(),
        }
        if col not in keys or not self.rows:
            return
        last_col, order = self._sort
        order = (
            Qt.SortOrder.DescendingOrder
            if last_col == col and order == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        self._sort = (col, order)
        self.rows.sort(key=keys[col], reverse=order == Qt.SortOrder.DescendingOrder)
        header = self.table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(col, order)
        self.populate_table()

    # --- Several rows at once ---

    def selected_rows(self) -> list[Row]:
        return [self.rows[index.row()] for index in self.table.selectionModel().selectedRows()]

    def spread(self, row: Row, col: int):
        """
        Copy a combo change to the other selected rows (Ctrl/Shift+click on the chapter
        names selects several; the combos don't change the selection).
        """
        if self._spreading:
            return
        selected = self.selected_rows()
        if row not in selected or len(selected) < 2:
            return
        self._spreading = True
        try:
            # Same list in every row, so the same index means the same choice
            index = self.table.cellWidget(self.table_row(row), col).currentIndex()
            for other in selected:
                combo = self.table.cellWidget(self.table_row(other), col)
                if other is not row and combo:
                    combo.setCurrentIndex(index)
        finally:
            self._spreading = False

    def on_item_changed(self, item: QTableWidgetItem):
        if self._populating:
            return
        row = self.rows[item.row()]
        if item.column() == COL_CHECK:
            row.checked = item.checkState() == Qt.CheckState.Checked
            self.update_import_button()
        elif item.column() == COL_DECK:
            self.on_subdeck_edited(row, item.data(Qt.ItemDataRole.EditRole) or "")

    def on_subdeck_edited(self, row: Row, text: str):
        """A subdeck typed in the Deck column; the same name goes to the other selected rows."""
        selected = self.selected_rows()
        targets = selected if row in selected else [row]
        subdeck = decks.clean_deck_name(text)
        for other in targets:
            if other.importable:
                other.subdeck = None if subdeck == decks.section_name(other.kind) else subdeck
                self.refresh_deck(other)

    def on_double_click(self, i: int, col: int):
        url = self.rows[i].chapter.chapter_url if i < len(self.rows) else ""
        if col == COL_NAME and url:
            openLink(url)

    # --- Side and note type ---

    def on_side_changed(self, row: Row):
        """Puzzle when you make the first move, Flipped when the opponent does, Study for both."""
        i = self.table_row(row)
        row.side = self.table.cellWidget(i, COL_SIDE).currentData()
        row.note_type = self.note_type_for_mode(mode_for(row.side, row.chapter.side_to_move))
        combo = self.table.cellWidget(i, COL_NOTE_TYPE)
        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(row.note_type)))
        combo.blockSignals(False)
        self.spread(row, COL_SIDE)
        self.show_preview(i)

    def on_note_type_changed(self, row: Row):
        """Show the side a note type makes you play, without changing the note type back."""
        i = self.table_row(row)
        row.note_type = self.table.cellWidget(i, COL_NOTE_TYPE).currentData()
        mode = self.choice_modes.get(row.note_type)
        if mode:
            stm = row.chapter.side_to_move
            row.side = None if mode == MODE_STUDY else OTHER_SIDE[stm] if mode == MODE_FLIPPED else stm
            side_combo = self.table.cellWidget(i, COL_SIDE)
            side_combo.blockSignals(True)
            side_combo.setCurrentIndex([s for s, _ in SIDES].index(row.side))
            side_combo.blockSignals(False)
        self.spread(row, COL_NOTE_TYPE)
        self.show_preview(i)

    def on_kind_changed(self, row: Row):
        row.kind = self.table.cellWidget(self.table_row(row), COL_KIND).currentData()
        self.refresh_status(row)
        self.refresh_deck(row)
        self.spread(row, COL_KIND)

    def on_expand_option(self):
        self.refresh_statuses()
        self.populate_table()

    def refresh_status(self, row: Row):
        if row.importable:
            found = {anki_ops.card_status(mw.col, card, self.strip_anno)[0] for card, _ in self.row_cards(row)}
            row.status = found.pop() if len(found) == 1 else "changed"
        i = self.table_row(row)
        status = STATUS_KEYS.get(row.status)
        item = self.table.item(i, COL_STATUS)
        item.setText(tr(status) if status else "")

    # --- Board preview ---

    def show_preview(self, i: int):
        if not 0 <= i < len(self.rows):
            self.preview.show_board(None)
            return
        row = self.rows[i]
        if "game" not in row.cache:
            try:
                row.cache["game"] = chess.pgn.read_game(io.StringIO(row.chapter.pgn(self.strip_anno)))
            except (ValueError, KeyError):
                row.cache["game"] = None
        game = row.cache["game"]
        if game is None:
            self.preview.show_board(None, caption=row.chapter.name)
            return
        board, lastmove = game.board(), None
        first = game.next()
        # Flipped: the opponent's first move is played before your turn
        if first and self.choice_modes.get(row.note_type) == MODE_FLIPPED:
            board.push(first.move)
            lastmove = first.move
        # The chapter's intro, without commands such as [%eval] or [%cal]
        intro = " ".join(filter(None, [game.comment, first.comment if first else ""]))
        intro = " ".join(COMMAND_RE.sub(" ", intro).split())
        intro = textwrap.shorten(html.escape(intro), 300, placeholder=" …") if intro else ""
        caption = f"<b>{html.escape(row.chapter.name)}</b>"
        if intro:
            caption += f"<br>{intro}"
        cards = len(self.row_cards(row)) if row.importable else 0
        if cards > 1:
            caption += "<br><small>" + tr("status.cards", count=cards) + "</small>"
        self.preview.show_board(board, (row.side or "w") == "w", lastmove, caption)

    # --- Decks ---

    def placement(self, row: Row) -> decks.Placement:
        if "opening" not in row.cache or row.cache.get("opening_kind") != row.kind:
            row.cache["opening"] = decks.chapter_opening_name(row.chapter, row.kind)
            row.cache["opening_kind"] = row.kind
        return decks.place_chapter(
            row.chapter,
            self.root,
            kind=row.kind,
            opening=row.cache["opening"] or "",
            fallback_study=row.study.fallback,
            deck=row.study.deck,
            subdeck=row.subdeck,
        )

    def refresh_deck(self, row: Row):
        if not row.importable:
            return
        placement = self.placement(row)
        item = self.table.item(self.table_row(row), COL_DECK)
        # The study deck is in the field above: the cell keeps the subdeck, empty when
        # the chapter goes to the study deck itself
        subdeck = row.subdeck if row.subdeck is not None else decks.section_name(row.kind)
        self._populating = True
        try:
            item.setText(subdeck)
            item.setToolTip("\n".join([placement.deck, *placement.tags]))
        finally:
            self._populating = False

    def refresh_decks(self):
        for row in self.rows:
            self.refresh_deck(row)

    def current_study(self) -> Study | None:
        i = self.study_combo.currentIndex()
        return self.studies[i] if 0 <= i < len(self.studies) else None

    def on_study_selected(self, _index: int):
        study = self.current_study()
        if study:
            self.deck_edit.setText(study.deck)

    def on_study_deck_typed(self, text: str):
        study = self.current_study()
        if study:
            study.deck = decks.clean_deck_name(text) or study.default_deck
            self.refresh_decks()

    def on_study_deck_edited(self):
        """Show the name as Anki will store it (trimmed levels, no empty ones)."""
        study = self.current_study()
        if study and self.deck_edit.text() != study.deck:
            self.deck_edit.setText(study.deck)
        self.refresh_decks()

    def reset_decks(self):
        """Back to the names from Lichess: the study deck and its subdecks."""
        study = self.current_study()
        if not study:
            return
        study.deck = study.default_deck
        self.deck_edit.setText(study.deck)
        for row in self.rows:
            if row.study is study:
                row.subdeck = None
        self.refresh_decks()

    # --- Selection helpers ---

    def set_checked(self, value_for):
        """Check or uncheck rows: value_for(row) is True, False, or None to leave it."""
        self._populating = True
        for i, row in enumerate(self.rows):
            value = value_for(row) if row.importable else None
            if value is not None:
                row.checked = value
                self.table.item(i, COL_CHECK).setCheckState(
                    Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
                )
        self._populating = False
        self.update_import_button()

    def check_new_and_changed(self):
        self.set_checked(lambda r: r.status in ("new", "changed"))

    def check_exercises_and_lines(self):
        self.set_checked(lambda r: True if r.kind in (KIND_EXERCISE, KIND_LINE) else None)

    def uncheck_all(self):
        self.set_checked(lambda r: False)

    def on_toggle_games(self, checked: bool):
        self.set_checked(lambda r: checked if r.kind == KIND_GAME else None)

    def checked_rows(self) -> list[Row]:
        return [r for r in self.rows if r.importable and r.checked]

    def update_import_button(self):
        count = len(self.checked_rows())
        self.import_btn.setText(tr("button.import_count", count=count) if count else tr("button.import"))
        self.import_btn.setEnabled(bool(count) and self.base is not None)

    # --- Import ---

    def import_cards(self, rows: list[Row]) -> list[tuple[Chapter, str, decks.Placement]]:
        """(card, note type name, placement) of every card of the rows."""
        cards = []
        for row in rows:
            placement = self.placement(row)
            for card, key_move in self.row_cards(row):
                if key_move:
                    # Played from your side of the game: its note type follows the card
                    deck = decks.clean_deck_name(f"{row.study.deck}::{decks.section_name(decks.KIND_KEY_MOVE)}")
                    name = self.note_type_for_mode(card.suggested_mode)
                    cards.append((card, name, decks.Placement(deck, placement.tags)))
                else:
                    cards.append((card, row.note_type, placement))
        return cards

    def renamed_decks(self) -> dict:
        """Config entries keeping the deck names edited for these studies (defaults removed)."""
        study_decks = dict(self.config.get("study_decks", {}))
        for study in self.studies:
            if study.key:
                if study.deck != study.default_deck:
                    study_decks[study.key] = study.deck
                else:
                    study_decks.pop(study.key, None)
        chapter_decks = dict(self.config.get("chapter_decks", {}))
        for row in self.rows:
            key = row.chapter.dedupe_key
            if key:
                if row.subdeck is not None:
                    chapter_decks[key] = row.subdeck
                else:
                    chapter_decks.pop(key, None)
        return {"study_decks": study_decks, "chapter_decks": chapter_decks}

    def on_import(self):
        rows = self.checked_rows()
        if not rows:
            showWarning(tr("warn.no_selection"), parent=self)
            return
        base = self.base
        if not base:
            showWarning(tr("warn.base_missing"), parent=self)
            return
        selected = self.import_cards(rows)

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
        cards = [(card, models[name], placement) for card, name, placement in selected]

        update_existing = self.update_existing.isChecked()
        stats = {}
        self.config.update(
            {
                "include_games": self.include_games.isChecked(),
                "split_lines": self.split_lines.isChecked(),
                "key_moves": self.key_moves.isChecked(),
                "update_existing": update_existing,
                "lichess_token": self.token_edit.text().strip(),
                **self.renamed_decks(),
            }
        )
        write_config(self.config)

        def on_success(_changes):
            # The window stays open, to import more chapters or another study
            self.last_result = tr("result.summary", **stats)
            tooltip(self.last_result, parent=mw)
            for row in rows:
                row.checked = False
            self.refresh_statuses()
            self.find_removed_chapters()
            self.populate_table()
            offer_note_type_change(stats.get("other_type"))

        CollectionOp(
            parent=self,
            op=lambda col: anki_ops.import_chapters(col, cards, update_existing, self.strip_anno, stats),
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


def show_import_dialog(urls: str = ""):
    if not mw.col:
        return
    apply_language()
    StudyImportDialog(mw, urls).exec()
