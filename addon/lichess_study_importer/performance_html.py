"""
HTML of the performance panel: headline tiles, month-by-month line charts and the
tables, in tabs. Rendered in an AnkiWebView; every text from the data (tags, themes,
openings) is escaped, and the tooltip script writes with textContent.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import html
import json

from .i18n import STRINGS, tr
from .performance import MIN_GAMES, MIN_REVIEWS, Table

# One series per chart: categorical slot 1, stepped for each surface (validated light and dark)
CSS = """
.viz-root {
  --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b; --text-secondary: #52514e;
  --text-muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7; --series-1: #2a78d6;
  --border: rgba(11,11,11,0.10);
  color-scheme: light; background: var(--page); color: var(--text-primary);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 13px;
  padding: 12px 16px 24px;
}
.nightMode .viz-root, .night_mode .viz-root {
  --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #f0efec; --text-secondary: #c3c2b7;
  --text-muted: #898781; --grid: #2c2c2a; --axis: #383835; --series-1: #3987e5;
  --border: rgba(255,255,255,0.10);
  color-scheme: dark;
}
.viz-root h2 { font-size: 15px; font-weight: 600; margin: 20px 0 6px; }
.viz-root .note { color: var(--text-secondary); margin: 6px 0 0; max-width: 72em; line-height: 1.45; }
.viz-root .hint { background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 12px; margin: 8px 0 12px; color: var(--text-secondary); }
.tabs { display: flex; gap: 4px; flex-wrap: wrap; border-bottom: 1px solid var(--grid); margin-bottom: 8px; }
.tabs button { background: none; border: 0; border-bottom: 2px solid transparent; color: var(--text-secondary);
  font: inherit; padding: 6px 10px; cursor: pointer; }
.tabs button[aria-selected="true"] { color: var(--text-primary); border-bottom-color: var(--text-primary); font-weight: 600; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 12px 0; }
.tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.tile .label { color: var(--text-secondary); }
.tile .value { font-size: 28px; font-weight: 600; margin: 4px 0 2px; }
.tile .base { color: var(--text-muted); font-size: 12px; }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
figure.chart { position: relative; margin: 0; background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px 8px; outline: none; }
figure.chart:focus-visible { box-shadow: 0 0 0 2px var(--series-1); }
figure.chart figcaption { font-weight: 600; margin-bottom: 4px; }
figure.chart .empty { color: var(--text-muted); padding: 40px 0; text-align: center; }
svg.line { width: 100%; height: auto; display: block; overflow: visible; }
svg.line .grid { stroke: var(--grid); stroke-width: 1; }
svg.line .axis { stroke: var(--axis); stroke-width: 1; }
svg.line .tick { fill: var(--text-muted); font-size: 10px; font-variant-numeric: tabular-nums; }
svg.line .series { fill: none; stroke: var(--series-1); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
svg.line .dot { fill: var(--series-1); stroke: var(--surface-1); stroke-width: 2; }
svg.line .dot.few { fill: var(--surface-1); stroke: var(--series-1); stroke-width: 2; }
svg.line .end { fill: var(--text-secondary); font-size: 11px; }
svg.line .cross { stroke: var(--text-muted); stroke-width: 1; visibility: hidden; }
.tip { position: absolute; pointer-events: none; background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); visibility: hidden;
  white-space: nowrap; z-index: 2; }
.tip strong { display: block; font-size: 14px; }
.tip span { color: var(--text-secondary); font-size: 12px; }
table.data { border-collapse: collapse; margin-top: 4px; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
table.data th, table.data td { padding: 5px 10px; border-bottom: 1px solid var(--grid); text-align: left; }
table.data th { color: var(--text-secondary); font-weight: 600; }
table.data td { font-variant-numeric: tabular-nums; }
table.data tr:last-child td { border-bottom: 0; }
"""

SCRIPT = """
(function () {
  document.querySelectorAll('.tabs button').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.tabs button').forEach(function (o) { o.setAttribute('aria-selected', o === b); });
      document.querySelectorAll('section.tab').forEach(function (s) { s.hidden = s.id !== b.dataset.tab; });
      if (window.pycmd) { pycmd('ankichess_perf_tab:' + b.dataset.tab); }
    });
  });
  document.querySelectorAll('figure.chart[data-points]').forEach(function (fig) {
    var pts = JSON.parse(fig.dataset.points), svg = fig.querySelector('svg'), tip = fig.querySelector('.tip');
    var cross = svg.querySelector('.cross'), idx = -1;
    function show(i) {
      idx = Math.max(0, Math.min(pts.length - 1, i));
      var p = pts[idx];
      cross.setAttribute('x1', p.x); cross.setAttribute('x2', p.x); cross.style.visibility = 'visible';
      tip.textContent = '';
      var strong = document.createElement('strong'); strong.textContent = p.value;
      var span = document.createElement('span'); span.textContent = p.label;
      tip.appendChild(strong); tip.appendChild(span);
      var box = svg.getBoundingClientRect(), figBox = fig.getBoundingClientRect();
      var scale = box.width / svg.viewBox.baseVal.width;
      var left = box.left - figBox.left + p.x * scale + 10;
      if (left + tip.offsetWidth > figBox.width) { left -= tip.offsetWidth + 20; }
      tip.style.left = left + 'px'; tip.style.top = (box.top - figBox.top + 4) + 'px';
      tip.style.visibility = 'visible';
    }
    function hide() { cross.style.visibility = 'hidden'; tip.style.visibility = 'hidden'; }
    svg.addEventListener('pointermove', function (e) {
      var box = svg.getBoundingClientRect(), x = (e.clientX - box.left) * svg.viewBox.baseVal.width / box.width;
      var best = 0;
      pts.forEach(function (p, i) { if (Math.abs(p.x - x) < Math.abs(pts[best].x - x)) { best = i; } });
      show(best);
    });
    svg.addEventListener('pointerleave', hide);
    fig.addEventListener('focus', function () { show(idx < 0 ? pts.length - 1 : idx); });
    fig.addEventListener('blur', hide);
    fig.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { show(idx - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { show(idx + 1); e.preventDefault(); }
    });
  });
})();
"""

W, H = 320, 150
LEFT, RIGHT, TOP, BOTTOM = 34, 40, 10, 22
TAB_KEYS = ("summary", "memory", "skill", "games", "openings", "lpuzzles", "efficiency")


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def has_key(key: str) -> bool:
    return key in STRINGS["en"]


def label(value) -> str:
    """A cell or column: translated when it is a translation key."""
    if isinstance(value, str) and has_key(value):
        return tr(value)
    return "—" if value is None else str(value)


def group_label(value: str) -> str:
    """'puzzle:fork' -> 'Puzzles: fork', 'game_error:blunder' -> 'Errors in my games: Blunder'."""
    group, _, sub = str(value).partition(":")
    name = tr(f"perf.group.{group}") if has_key(f"perf.group.{group}") else group
    if not sub:
        return name
    sub_name = tr(f"kind.{sub}") if has_key(f"kind.{sub}") else sub
    return f"{name}: {sub_name}"


def table_html(table: Table) -> str:
    parts = [f"<h2>{esc(label(table.key))}</h2>"]
    if not table.rows:
        parts.append(f'<p class="note">{esc(tr("perf.empty"))}</p>')
    else:
        group_cols = {i for i, c in enumerate(table.columns) if c == "perf.col.group"}
        head = "".join(f"<th>{esc(label(c))}</th>" for c in table.columns)
        body = []
        for row in table.rows:
            cells = [group_label(v) if i in group_cols else label(v) for i, v in enumerate(row)]
            body.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>")
        parts.append(f'<table class="data"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>')
    if table.note:
        parts.append(f'<p class="note">{esc(label(table.note))}</p>')
    return "".join(parts)


def nice_range(values: list[float]) -> tuple[float, float, float]:
    """(low, high, step) with 3-5 clean ticks around the values."""
    low, high = min(values), max(values)
    if high - low < 1e-9:
        low, high = low - 1, high + 1
    span = high - low
    raw = span / 4
    magnitude = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 0.1
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = (low // step) * step
    end = -(-high // step) * step
    return start, end, step


def line_chart(title_key: str, points: list[tuple[str, float | None, int]], min_base: int, suffix: str = "") -> str:
    """Single series by month (no legend: the title names it); hollow dots: too few data."""
    points = [p for p in points if p[1] is not None]
    caption = f"<figcaption>{esc(tr(title_key))}</figcaption>"
    if not points:
        return f'<figure class="chart">{caption}<div class="empty">{esc(tr("perf.empty"))}</div></figure>'
    low, high, step = nice_range([v for _, v, _ in points])
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM

    def x_of(i):
        return LEFT + (plot_w / 2 if len(points) == 1 else plot_w * i / (len(points) - 1))

    def y_of(v):
        return TOP + plot_h * (1 - (v - low) / (high - low))

    svg = [f'<svg class="line" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(tr(title_key))}">']
    tick = low
    while tick <= high + step / 2:
        y = y_of(tick)
        svg.append(f'<line class="grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{y:.1f}" y2="{y:.1f}"/>')
        text = f"{tick:.0f}" if step >= 1 else f"{tick:.1f}"
        svg.append(f'<text class="tick" x="{LEFT - 6}" y="{y + 3:.1f}" text-anchor="end">{esc(text)}</text>')
        tick += step
    svg.append(f'<line class="axis" x1="{LEFT}" x2="{W - RIGHT}" y1="{TOP + plot_h}" y2="{TOP + plot_h}"/>')
    month_labels = {0, len(points) - 1} if len(points) > 1 else {0}
    for i in sorted(month_labels):
        anchor = "start" if i == 0 and len(points) > 1 else ("end" if i == len(points) - 1 and len(points) > 1 else "middle")
        svg.append(f'<text class="tick" x="{x_of(i):.1f}" y="{H - 6}" text-anchor="{anchor}">{esc(points[i][0])}</text>')
    coords = [(x_of(i), y_of(v)) for i, (_, v, _) in enumerate(points)]
    if len(coords) > 1:
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(coords))
        svg.append(f'<path class="series" d="{path}"/>')
    svg.append(f'<line class="cross" x1="0" x2="0" y1="{TOP}" y2="{TOP + plot_h}"/>')
    data = []
    for (month, value, base), (x, y) in zip(points, coords):
        few = base < min_base
        svg.append(f'<circle class="dot{" few" if few else ""}" cx="{x:.1f}" cy="{y:.1f}" r="4"/>')
        note = tr("perf.base", n=base) + (" *" if few else "")
        data.append({"x": round(x, 1), "value": f"{value:.1f}{suffix}", "label": f"{month} · {note}"})
    last_x, last_y = coords[-1]
    svg.append(f'<text class="end" x="{last_x + 8:.1f}" y="{last_y + 4:.1f}">{esc(f"{points[-1][1]:.1f}{suffix}")}</text>')
    svg.append("</svg>")
    return (
        f'<figure class="chart" tabindex="0" data-points="{esc(json.dumps(data))}">'
        f'{caption}{"".join(svg)}<div class="tip" role="status"></div></figure>'
    )


def tiles_html(tiles: list[tuple[str, str, int]], min_bases: list[int]) -> str:
    items = []
    for (key, value, base), min_base in zip(tiles, min_bases):
        flag = " *" if base < min_base else ""
        items.append(
            f'<div class="tile"><div class="label">{esc(tr(key))}</div>'
            f'<div class="value">{esc(value)}</div>'
            f'<div class="base">{esc(tr("perf.base", n=base) + flag)}</div></div>'
        )
    return f'<div class="tiles">{"".join(items)}</div>'


def page(
    tiles: list[tuple[str, str, int]],
    series: dict[str, list],
    tabs: dict[str, list[Table]],
    active: str = "summary",
    hints: list[str] | None = None,
) -> str:
    """The whole panel; tabs: tab key -> its tables (the summary tab also gets tiles and charts)."""
    active = active if active in TAB_KEYS else "summary"
    nav = "".join(
        f'<button type="button" data-tab="{key}" aria-selected="{"true" if key == active else "false"}">'
        f"{esc(tr(f'perf.tab.{key}'))}</button>"
        for key in TAB_KEYS
    )
    sections = []
    for key in TAB_KEYS:
        content = []
        if key == "summary":
            content.append(tiles_html(tiles, [MIN_REVIEWS, MIN_REVIEWS, MIN_GAMES, MIN_GAMES]))
            content.append(
                '<div class="charts">'
                + line_chart("perf.chart.retention", series.get("retention", []), MIN_REVIEWS, "%")
                + line_chart("perf.chart.first_pass", series.get("first_pass", []), MIN_REVIEWS, "%")
                + line_chart("perf.chart.accuracy", series.get("accuracy", []), MIN_GAMES)
                + line_chart("perf.chart.errors40", series.get("errors40", []), MIN_GAMES)
                + "</div>"
            )
            content.append(f'<p class="note">{esc(tr("perf.low_sample", reviews=MIN_REVIEWS, games=MIN_GAMES))}</p>')
        content += [table_html(t) for t in tabs.get(key, [])]
        hidden = "" if key == active else " hidden"
        sections.append(f'<section class="tab" id="{key}"{hidden}>{"".join(content)}</section>')
    hint_html = "".join(f'<div class="hint">{esc(h)}</div>' for h in hints or [])
    return (
        f"<style>{CSS}</style><div class=\"viz-root\"><nav class=\"tabs\">{nav}</nav>{hint_html}"
        f"{''.join(sections)}</div><script>{SCRIPT}</script>"
    )
