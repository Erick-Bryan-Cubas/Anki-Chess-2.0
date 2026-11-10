import json
import os
import re
import sys
import types
from html import unescape

HERE = os.path.dirname(__file__)
ADDON_DIR = os.path.join(HERE, "..", "lichess_study_importer")

if "lsi" not in sys.modules:
    pkg = types.ModuleType("lsi")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["lsi"] = pkg

from lsi import i18n, performance_html as ph  # noqa: E402
from lsi.performance import Table  # noqa: E402

SERIES = {
    "retention": [("2026-09", 82.0, 40), ("2026-10", 85.5, 12)],
    "first_pass": [],
    "accuracy": [("2026-10", 88.1, 14)],
    "errors40": [("2026-08", 3.2, 11), ("2026-09", None, 0), ("2026-10", 2.5, 12)],
}
TILES = [("perf.chart.retention", "85.5%", 52), ("perf.chart.first_pass", "—", 0),
         ("perf.chart.accuracy", "88.1", 14), ("perf.chart.errors40", "2.5", 3)]


def test_labels():
    assert ph.label("perf.col.group") == "Group"
    assert ph.label("C45") == "C45" and ph.label(None) == "—" and ph.label(3) == "3"
    assert ph.group_label("puzzle:fork") == "Puzzles: fork"
    assert ph.group_label("game_error:blunder") == "Errors from my games: Blunder"
    assert ph.group_label("study") == "Studies"


def test_nice_range():
    low, high, step = ph.nice_range([82.0, 85.5])
    assert low <= 82 and high >= 85.5 and step in (1, 2, 2.5, 5)
    assert ph.nice_range([3.0, 3.0])[0] < 3 < ph.nice_range([3.0, 3.0])[1]


def test_line_chart_points_and_sparse_months():
    chart = ph.line_chart("perf.chart.errors40", SERIES["errors40"], 10)
    points = json.loads(unescape(re.search(r'data-points="([^"]*)"', chart).group(1)))
    assert [p["value"] for p in points] == ["3.2", "2.5"]  # the month without a value is left out
    assert points[0]["label"].startswith("2026-08 · based on 11")
    assert chart.count("<circle") == 2 and 'class="series"' in chart
    few = ph.line_chart("perf.chart.retention", SERIES["retention"], 30, "%")
    assert few.count('class="dot few"') == 1 and "85.5%" in few  # 12 answers: hollow, end label
    assert "No data in this period." in ph.line_chart("perf.chart.first_pass", [], 30)


def test_page_escapes_data_and_keeps_the_tab():
    table = Table("perf.memory.sub_title", ["perf.col.group", "perf.col.young"],
                  [["puzzle:<script>alert(1)</script>", "90.0% (80–95) · 40"]])
    html = ph.page(TILES, SERIES, {"memory": [table]}, active="memory", hints=["<b>hint</b>"])
    assert "<script>alert" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;hint&lt;/b&gt;" in html
    assert re.search(r'<section class="tab" id="memory">', html)
    assert re.search(r'<section class="tab" id="summary" hidden>', html)
    assert html.count('class="tile"') == 4 and "based on 3 *" in html  # 3 games: too few
    assert ph.page(TILES, SERIES, {}, active="unknown").count('id="summary">') == 1


def test_page_in_portuguese():
    i18n.set_language("pt-BR")
    try:
        html = ph.page(TILES, SERIES, {"games": [Table("perf.games.title", ["perf.col.metric"], [])]})
        assert "Resumo" in html and "Partidas: qualidade dos seus lances" in html and "Sem dados neste período." in html
    finally:
        i18n.set_language("en")
