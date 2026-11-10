"""
Tools > Chess performance: the panel of performance_html.py over the review log, the
cards' FSRS state, the saved game metrics and the Lichess puzzle history; the filters
in one row above it, and the CSV export (Power BI, Excel, Python...).
"""

from __future__ import annotations

import csv
import os
import time
from datetime import date

from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (
    QComboBox,
    QDate,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from aqt.utils import showInfo, showWarning, tooltip
from aqt.webview import AnkiWebView

from . import anki_ops, lichess_api, performance_html, performance_store as store
from . import performance as pf
from .i18n import tr
from .ui_common import error_text, get_config, lichess_token, restore_window, save_window, write_config

WINDOW_KEY = "ankichessPerformance"
PERIODS = ("protocol", "30", "90", "365", "all", "before_protocol")
SPEEDS = ("all", "bullet", "blitz", "rapid", "classical", "correspondence", "ultrabullet")
NO_DATE = QDate(2000, 1, 1)
PUZZLE_PAGE = 200
MAX_PUZZLE_PAGES = 200


def read_collection(col) -> dict:
    """Everything the panel needs, read in the background."""
    mids = [m["id"] for m in col.models.all() if anki_ops.is_chess_note_type(m)]
    cards = pf.load_cards(col, mids)
    reviews = pf.load_reviews(col, list(cards))
    return {
        "cards": cards,
        "reviews": reviews,
        "games": store.load_games(col),
        "positions": pf.studied_positions(cards, reviews),
        "protocol": store.protocol_start(col),
    }


class PerformanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("perf.title"))
        restore_window(self, WINDOW_KEY, (1100, 780))
        self.config = get_config()
        self.data: dict | None = None
        self.tables: list[pf.Table] = []
        self.active_tab = self.config.get("perf_tab", "summary")

        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.period_combo = QComboBox()
        for key in PERIODS:
            self.period_combo.addItem(tr(f"perf.period.{key}"), key)
        self.period_combo.setCurrentIndex(max(0, PERIODS.index(self.config.get("perf_period", "90"))))
        self.speed_combo = QComboBox()
        for key in SPEEDS:
            self.speed_combo.addItem(tr(f"perf.speed.{key}"), key)
        self.speed_combo.setCurrentIndex(max(0, SPEEDS.index(self.config.get("perf_speed", "all"))))
        self.protocol_edit = QDateEdit()
        self.protocol_edit.setCalendarPopup(True)
        self.protocol_edit.setDisplayFormat("yyyy-MM-dd")
        self.protocol_edit.setMinimumDate(NO_DATE)
        self.protocol_edit.setSpecialValueText(tr("perf.protocol_none"))
        self.protocol_edit.setToolTip(tr("perf.protocol_tip"))
        self.protocol_edit.setDate(NO_DATE)
        for widget in (
            QLabel(tr("perf.period")), self.period_combo,
            QLabel(tr("perf.speed")), self.speed_combo,
            QLabel(tr("perf.protocol_start")), self.protocol_edit,
        ):
            filters.addWidget(widget)
        filters.addStretch(1)
        for text, tip, slot in (
            (tr("perf.puzzles_update"), tr("perf.puzzles_tip"), self.on_update_puzzles),
            (tr("perf.export"), "", self.on_export),
            (tr("perf.refresh"), "", self.load),
        ):
            button = QPushButton(text)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            filters.addWidget(button)
        layout.addLayout(filters)

        self.web = AnkiWebView(parent=self, title="ankichess_performance")
        self.web.set_bridge_command(self.on_bridge, self)
        layout.addWidget(self.web, 1)

        self.period_combo.currentIndexChanged.connect(lambda _: self.render())
        self.speed_combo.currentIndexChanged.connect(lambda _: self.render())
        self.protocol_edit.dateChanged.connect(self.on_protocol_changed)
        self.load()

    # --- Data ---

    def load(self):
        def on_loaded(data):
            self.data = data
            self.protocol_edit.blockSignals(True)
            self.protocol_edit.setDate(QDate.fromString(data["protocol"], "yyyy-MM-dd") if data["protocol"] else NO_DATE)
            self.protocol_edit.blockSignals(False)
            self.render()

        QueryOp(parent=self, op=read_collection, success=on_loaded).failure(
            lambda e: showWarning(error_text(e), parent=self)
        ).with_progress(tr("perf.loading")).run_in_background()

    def on_protocol_changed(self, value: QDate):
        day = None if value == NO_DATE else value.toString("yyyy-MM-dd")
        store.set_protocol_start(mw.col, day)
        if self.data is not None:
            self.data["protocol"] = day
            self.render()

    def period(self) -> pf.Period:
        protocol = self.data["protocol"] if self.data else None
        return pf.period_from(self.period_combo.currentData(), date.today(), protocol)

    # --- Panel ---

    def build(self):
        """(tiles, series, tables by tab, hints) for the current filters."""
        data = self.data
        cards, reviews = data["cards"], data["reviews"]
        period = self.period()
        games = pf.eligible_games(data["games"], self.speed_combo.currentData(), period)
        entries = store.load_puzzle_activity().get("entries", [])
        now_ms = int(time.time() * 1000)
        tabs = {
            "summary": [pf.calibration_table(cards, reviews, period)],
            "memory": [
                pf.memory_table(cards, reviews, period, "group"),
                pf.memory_table(cards, reviews, period, "sub"),
                pf.memory_table(cards, reviews, period, "eco"),
            ],
            "skill": [pf.skill_table(cards, reviews, period), pf.puzzle_band_table(cards, reviews, period)],
            "games": [pf.games_table(games, data["positions"]), pf.games_trend_table(games)],
            "openings": [pf.openings_table(games, cards, reviews, period)],
            "lpuzzles": pf.puzzle_history_tables(entries, period),
            "efficiency": [pf.efficiency_table(cards, reviews, period, now_ms)],
        }
        hints = []
        if not data["games"]:
            hints.append(tr("perf.hint.no_games"))
        if reviews and not any(c.stability for c in cards.values()):
            hints.append(tr("perf.hint.no_fsrs"))
        tiles = pf.headline(cards, reviews, games, period)
        series = pf.monthly_series(cards, reviews, games, period)
        return tiles, series, tabs, hints

    def render(self):
        if self.data is None:
            return
        tiles, series, tabs, hints = self.build()
        self.tables = [t for key in performance_html.TAB_KEYS for t in tabs.get(key, [])]
        page = performance_html.page(tiles, series, tabs, self.active_tab, hints)
        self.web.stdHtml(page, context=self)

    def on_bridge(self, message: str):
        if message.startswith("ankichess_perf_tab:"):
            self.active_tab = message.split(":", 1)[1]

    # --- Lichess puzzle history ---

    def on_update_puzzles(self):
        token = lichess_token()
        if not token:
            showWarning(tr("perf.puzzles_need_token"), parent=self)
            return
        user = str(get_config().get("lichess_token_user", ""))

        def progress(count):
            mw.taskman.run_on_main(lambda: mw.progress.update(label=tr("perf.puzzles_progress", count=count)))

        def task(col):
            cached = store.load_puzzle_activity()
            if cached.get("user") and user and cached["user"].lower() != user.lower():
                cached = {}
            known = {(e["id"], e["date"]) for e in cached.get("entries", [])}
            new, before = [], None
            for _ in range(MAX_PUZZLE_PAGES):
                page = lichess_api.fetch_puzzle_activity(token, PUZZLE_PAGE, before)
                fresh = [e for e in page if ((e.get("puzzle") or {}).get("id"), e.get("date")) not in known]
                new += fresh
                progress(len(new))
                # Back at what the cache already has, or at the start of the history
                if len(page) < PUZZLE_PAGE or len(fresh) < len(page):
                    break
                before = min(int(e["date"]) for e in page)
            merged = store.merge_puzzle_activity(cached, user, new)
            store.save_puzzle_activity(merged)
            return len(merged["entries"]), len(new)

        def on_done(result):
            total, new = result
            tooltip(tr("perf.puzzles_done", count=total, new=new), parent=self)
            self.render()

        QueryOp(parent=self, op=task, success=on_done).failure(
            lambda e: showWarning(error_text(e), parent=self)
        ).with_progress(tr("perf.puzzles_progress", count=0)).without_collection().run_in_background()

    # --- CSV export ---

    def on_export(self):
        if self.data is None:
            return
        folder = QFileDialog.getExistingDirectory(self, tr("perf.export_title"), self.config.get("last_dir", ""))
        if not folder:
            return
        self.config["last_dir"] = folder
        metrics = [["table", "row", "column", "value"]]
        for table in self.tables:
            title = performance_html.label(table.key)
            group_cols = {i for i, c in enumerate(table.columns) if c == "perf.col.group"}
            for n, row in enumerate(table.rows, 1):
                for i, (column, value) in enumerate(zip(table.columns, row)):
                    text = performance_html.group_label(value) if i in group_cols else performance_html.label(value)
                    metrics.append([title, n, performance_html.label(column), text])
        files = {
            "reviews.csv": pf.review_rows(self.data["cards"], self.data["reviews"]),
            "games.csv": pf.game_rows(self.data["games"]),
            "metrics.csv": metrics,
        }
        try:
            for name, rows in files.items():
                with open(os.path.join(folder, name), "w", encoding="utf-8-sig", newline="") as f:
                    csv.writer(f).writerows(rows)
        except OSError as e:
            showWarning(str(e), parent=self)
            return
        showInfo(tr("perf.export_done", folder=folder), parent=self)

    def done(self, result):
        # Read again: the token or other settings may have changed while the panel was open
        config = get_config()
        config.update(
            {
                "perf_period": self.period_combo.currentData(),
                "perf_speed": self.speed_combo.currentData(),
                "perf_tab": self.active_tab,
                "last_dir": self.config.get("last_dir", config.get("last_dir", "")),
            }
        )
        write_config(config)
        save_window(self, WINDOW_KEY)
        if hasattr(self.web, "cleanup"):
            self.web.cleanup()
        global _open_dialog
        _open_dialog = None
        super().done(result)


_open_dialog: PerformanceDialog | None = None


def show_performance():
    global _open_dialog
    if _open_dialog is None:
        _open_dialog = PerformanceDialog(mw)
        _open_dialog.setModal(False)
    _open_dialog.show()
    _open_dialog.raise_()
    _open_dialog.activateWindow()
