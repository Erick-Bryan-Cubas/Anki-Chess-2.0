"""
AnkiChess card options: the card's helps (hints, the refutation of a wrong move, the answer
button suggested on the back) on or off for each AnkiChess note type and card template.
They are written into each template's window.USER_CONFIG (see template_options), so they
apply on every device the note type syncs to, AnkiDroid included.
"""

from __future__ import annotations

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    Qt,
)
from aqt.utils import tooltip

from .anki_ops import find_chess_note_types
from .i18n import tr
from .template_options import EASY_TIME_MAX, GRADE_MODES, options_of, write_config
from .ui_common import readonly_item, restore_window, save_window

COLUMNS = ("tmplopts.col_template", "tmplopts.col_hints", "tmplopts.col_refutation", "tmplopts.col_grade", "tmplopts.col_easy")
TIPS = (None, "tmplopts.tip_hints", "tmplopts.tip_refutation", "tmplopts.tip_grade", "tmplopts.tip_easy")


def _centered(widget: QWidget) -> QWidget:
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(widget)
    return holder


class TemplateOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle(tr("tmplopts.title"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("tmplopts.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # One row per card template whose settings can be read: (note type, template, values, widgets)
        self.rows: list[tuple[dict, dict, dict, dict]] = []
        for m in sorted(find_chess_note_types(), key=lambda m: m["name"].lower()):
            for tmpl in m["tmpls"]:
                values = options_of(tmpl["qfmt"])
                if values is not None:
                    self.rows.append((m, tmpl, values, {}))

        if not self.rows:
            layout.addWidget(QLabel(tr("tmplopts.none")))
        self.table = QTableWidget(len(self.rows), len(COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(key) for key in COLUMNS])
        for col, tip in enumerate(TIPS):
            if tip:
                self.table.horizontalHeaderItem(col).setToolTip(tr(tip))
        self.table.verticalHeader().setVisible(False)
        for row, (m, tmpl, values, widgets) in enumerate(self.rows):
            name = m["name"] if len(m["tmpls"]) == 1 else f'{m["name"]} — {tmpl["name"]}'
            self.table.setItem(row, 0, readonly_item(name))
            for col, key in ((1, "hints"), (2, "refutation")):
                box = QCheckBox()
                box.setChecked(values[key])
                box.setToolTip(tr(TIPS[col]))
                widgets[key] = box
                self.table.setCellWidget(row, col, _centered(box))
            grade = QComboBox()
            for mode in GRADE_MODES:
                grade.addItem(tr(f"tmplopts.grade_{mode}"), mode)
            grade.setCurrentIndex(GRADE_MODES.index(values["autoGrade"]))
            grade.setToolTip(tr(TIPS[3]))
            widgets["autoGrade"] = grade
            self.table.setCellWidget(row, 3, grade)
            easy = QSpinBox()
            easy.setRange(0, EASY_TIME_MAX)
            easy.setValue(values["easyTime"])
            easy.setToolTip(tr(TIPS[4]))
            widgets["easyTime"] = easy
            self.table.setCellWidget(row, 4, easy)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(bool(self.rows))
        layout.addWidget(buttons)
        restore_window(self, "ankichess_template_options", (760, 420))

    def chosen(self, widgets: dict) -> dict:
        return {
            "hints": widgets["hints"].isChecked(),
            "refutation": widgets["refutation"].isChecked(),
            "autoGrade": widgets["autoGrade"].currentData(),
            "easyTime": widgets["easyTime"].value(),
        }

    def save(self):
        changed_types: dict[int, dict] = {}
        templates = 0
        for m, tmpl, values, widgets in self.rows:
            chosen = self.chosen(widgets)
            changes = {key: value for key, value in chosen.items() if value != values[key]}
            if not changes:
                continue
            new_qfmt = write_config(tmpl["qfmt"], changes)
            if new_qfmt is None:
                continue
            tmpl["qfmt"] = new_qfmt
            changed_types[m["id"]] = m
            templates += 1
        for m in changed_types.values():
            mw.col.models.update_dict(m)
        tooltip(tr("tmplopts.saved", count=templates), parent=mw)
        self.accept()

    def done(self, result):
        save_window(self, "ankichess_template_options")
        super().done(result)


def show_template_options():
    if not mw.col:
        return
    TemplateOptionsDialog(mw).exec()
