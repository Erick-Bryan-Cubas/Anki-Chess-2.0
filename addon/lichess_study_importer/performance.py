"""
Performance metrics from what Anki already records (the review log, the cards' FSRS
memory state, the importer's tags) and from the metrics saved for each analysed game.

Three questions, each answered without the Elo:
- memory: does what I study stay?          (true retention of reviews, by group)
- skill: do I solve what I have never seen? (first answer of each new card)
- transfer: does it show in my games?      (game_stats per game, by speed and opening)
plus how much each kind of study costs (minutes per unit of knowledge).

Every function is pure: the dialog reads the collection (load_cards / load_reviews take
the collection) and renders the Table objects; the CSV export writes the same tables.
"""

from __future__ import annotations

import io
import json
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, fields
from datetime import date, datetime, timedelta

from .chess_lib import chess
from .game_stats import GameStats, position_key
from .i18n import tr

DAY_MS = 86_400_000
MATURE_DAYS = 21
MIN_REVIEWS = 30  # fewer answers than this: the rate is shown but flagged as unreliable
MIN_GAMES = 10
MIN_USER_MOVES = 15  # shorter games (and abandoned ones) say little about how you play
ERROR_KINDS = ("blunder", "mistake", "inaccuracy", "miss", "missed_mate")
OPENING_KINDS = ("opening", "book", "book_line")
STUDY_KINDS = ("line", "exercise", "game", "structure")
GAME_SOURCES = ("lichess", "chesscom")
RATING_RE = re.compile(r"\((\d{3,4})\)")
ID_RE = re.compile(r'\[AnkiChessId "([^"]*)"\]')
CHAPTER_RE = re.compile(r'\[ChapterName "([^"]*)"\]')
DAY_PARTS = ((0, "night"), (6, "morning"), (12, "afternoon"), (18, "evening"))
# Revlog types: 0 learn, 1 review, 2 relearn, 3 filtered; 4 manual and 5 rescheduled
# are not answers
ANSWER_TYPES = (0, 1, 2, 3)


# --- Data read from the collection ---


@dataclass
class CardInfo:
    cid: int
    group: str  # puzzle | game_error | opening | study | other
    subs: list[str] = field(default_factory=list)  # puzzle themes, error kind, study kind
    eco: str | None = None
    rating: int | None = None  # puzzle rating
    stability: float | None = None  # FSRS, days
    decay: float | None = None
    desired: float | None = None  # desired retention of its deck (FSRS)
    leech: bool = False
    pgn: str = ""  # for the positions it trains (repeated errors)


@dataclass
class Review:
    ts: int  # ms
    cid: int
    ease: int  # 1 Again .. 4 Easy
    ivl: int  # days (negative: seconds, in learning)
    last_ivl: int
    time_ms: int
    type: int

    @property
    def day(self) -> date:
        return datetime.fromtimestamp(self.ts / 1000).date()


@dataclass
class Table:
    key: str  # i18n key of its title
    columns: list[str]  # i18n keys
    rows: list[list] = field(default_factory=list)
    note: str = ""  # i18n key of an explanation under the table


def classify(tags: list[str], pgn: str) -> tuple[str, list[str], str | None, int | None]:
    """(group, subgroups, ECO, puzzle rating) of a note, from its tags or else its PGN id."""
    lowered = [t.lower() for t in tags]
    eco = next((t.split("::", 1)[1].upper() for t in lowered if t.startswith("eco::")), None)
    if "lichess::puzzle" in lowered:
        themes = [t.split("::")[2] for t in lowered if t.startswith("lichess::puzzle::") and t.count("::") == 2]
        m = RATING_RE.search(CHAPTER_RE.search(pgn).group(1)) if CHAPTER_RE.search(pgn) else None
        return "puzzle", [t for t in themes if t != "failed"], eco, int(m.group(1)) if m else None
    for source in GAME_SOURCES:
        for kind in ERROR_KINDS:
            if f"{source}::{kind}" in lowered:
                return "game_error", [kind], eco, None
        for kind in OPENING_KINDS:
            if f"{source}::{kind}" in lowered:
                return "opening", [kind], eco, None
    for source in ("lichess", "pgn"):
        for kind in STUDY_KINDS:
            if f"{source}::{kind}" in lowered:
                return "study", [kind], eco, None
    # Notes imported before these tags existed: the id written in the PGN
    m = ID_RE.search(pgn)
    key = m.group(1) if m else ""
    if key.startswith("puzzle/"):
        return "puzzle", [], eco, None
    if key.startswith("book/"):
        return "opening", ["book_line"], eco, None
    parts = key.split("/")
    if len(parts) == 4 and parts[0] in GAME_SOURCES:
        kind = parts[3]
        return ("opening" if kind in OPENING_KINDS else "game_error"), [kind], eco, None
    if key.startswith(("study/", "pgn/")):
        return "study", [], eco, None
    return "other", [], eco, None


def card_from_row(cid: int, tags: str, flds: str, data: str, desired: float | None) -> CardInfo:
    tag_list = tags.split()
    pgn = flds.split("\x1f", 1)[0]
    group, subs, eco, rating = classify(tag_list, pgn)
    memory = {}
    try:
        memory = json.loads(data) if data else {}
    except ValueError:
        pass
    return CardInfo(
        cid=cid,
        group=group,
        subs=subs,
        eco=eco,
        rating=rating,
        stability=memory.get("s"),
        decay=memory.get("decay"),
        desired=memory.get("dr") or desired,
        leech="leech" in (t.lower() for t in tag_list),
        pgn=pgn,
    )


def load_cards(col, chess_mids: list[int]) -> dict[int, CardInfo]:
    """Every card of the AnkiChess note types."""
    if not chess_mids:
        return {}
    ids = ",".join(str(int(m)) for m in chess_mids)
    desired_by_deck: dict[int, float | None] = {}
    cards = {}
    for cid, did, tags, flds, data in col.db.all(
        f"select c.id, c.did, n.tags, n.flds, c.data from cards c join notes n on n.id = c.nid where n.mid in ({ids})"
    ):
        if did not in desired_by_deck:
            try:
                desired_by_deck[did] = col.decks.config_dict_for_deck_id(did).get("desiredRetention")
            except Exception:  # noqa: BLE001 - filtered decks have no options
                desired_by_deck[did] = None
        cards[cid] = card_from_row(cid, tags, flds, data, desired_by_deck[did])
    return cards


def load_reviews(col, cids) -> list[Review]:
    if not cids:
        return []
    rows = col.db.all(
        "select r.id, r.cid, r.ease, r.ivl, r.lastIvl, r.time, r.type from revlog r "
        f"where r.cid in ({','.join(str(int(c)) for c in cids)}) order by r.id"
    )
    return [Review(*row) for row in rows]


# --- Statistics helpers ---


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% interval of a pass rate (Wilson score), in %."""
    if total <= 0:
        return None
    p = passed / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return round(100 * (center - half), 1), round(100 * (center + half), 1)


def rate(passed: int, total: int) -> str:
    """'87.5% (81-92) · 120', or '—'; '*' marks too few answers to rely on."""
    if total <= 0:
        return "—"
    low, high = wilson(passed, total)
    flag = "" if total >= MIN_REVIEWS else " *"
    return f"{100 * passed / total:.1f}% ({low:.0f}–{high:.0f}) · {total}{flag}"


def median(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def fmt(value, suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def retrievability(stability: float, days: float, decay: float | None) -> float:
    """FSRS forgetting curve: the chance of recalling after `days` (0.9 at days == stability)."""
    decay = decay or 0.5
    factor = 0.9 ** (-1 / decay) - 1
    return (1 + factor * days / stability) ** (-decay)


def month_of(day: date | str) -> str:
    return day[:7] if isinstance(day, str) else day.strftime("%Y-%m")


def day_part(ts: int) -> str:
    hour = datetime.fromtimestamp(ts / 1000).hour
    return next(name for start, name in reversed(DAY_PARTS) if hour >= start)


# --- Periods ---


@dataclass
class Period:
    start: date | None = None  # inclusive
    end: date | None = None  # inclusive

    def contains(self, day: date | None) -> bool:
        if day is None:
            return self.start is None and self.end is None
        return (self.start is None or day >= self.start) and (self.end is None or day <= self.end)


def period_from(choice: str, today: date, protocol: str | None) -> Period:
    """choice: all | 30 | 90 | 365 | protocol | before_protocol."""
    if choice in ("30", "90", "365"):
        return Period(today - timedelta(days=int(choice) - 1), today)
    if choice in ("protocol", "before_protocol") and protocol:
        start = date.fromisoformat(protocol)
        return Period(start, None) if choice == "protocol" else Period(None, start - timedelta(days=1))
    return Period()


# --- Memory, skill and efficiency (Anki's review log) ---


def _groups_of(card: CardInfo, by: str) -> list[str]:
    if by == "group":
        return [card.group]
    if by == "sub":
        return [f"{card.group}:{s}" for s in card.subs] or [card.group]
    if by == "eco":
        return [card.eco] if card.eco else []
    return []


def memory_table(cards: dict[int, CardInfo], reviews: list[Review], period: Period, by: str = "group") -> Table:
    titles = {"group": "perf.memory.title", "sub": "perf.memory.sub_title", "eco": "perf.memory.eco_title"}
    first = "perf.col.eco" if by == "eco" else "perf.col.group"
    table = Table(
        titles[by],
        [first, "perf.col.young", "perf.col.mature", "perf.col.time_ok", "perf.col.leeches"],
        note="perf.memory.note" if by == "group" else "",
    )
    young = defaultdict(lambda: [0, 0])
    mature = defaultdict(lambda: [0, 0])
    times = defaultdict(list)
    for r in reviews:
        card = cards.get(r.cid)
        if card is None or r.type != 1 or not period.contains(r.day):
            continue
        for g in _groups_of(card, by):
            bucket = mature if r.last_ivl >= MATURE_DAYS else young
            bucket[g][0] += r.ease > 1
            bucket[g][1] += 1
            if r.ease > 1:
                times[g].append(r.time_ms / 1000)
    leeches = defaultdict(int)
    for card in cards.values():
        if card.leech:
            for g in _groups_of(card, by):
                leeches[g] += 1
    for g in sorted(set(young) | set(mature)):
        table.rows.append([g, rate(*young[g]), rate(*mature[g]), fmt(median(times[g]), " s"), leeches[g]])
    return table


def first_answers(cards: dict[int, CardInfo], reviews: list[Review]) -> dict[int, Review]:
    """The first answer of each card that started as new (learning step)."""
    first: dict[int, Review] = {}
    for r in reviews:
        if r.type in ANSWER_TYPES and r.cid not in first:
            first[r.cid] = r
    return {cid: r for cid, r in first.items() if r.type == 0 and cid in cards}


def skill_table(cards: dict[int, CardInfo], reviews: list[Review], period: Period) -> Table:
    """First-time pass rate by month and group: solving what you have never seen."""
    table = Table("perf.skill.title", ["perf.col.month", "perf.col.group", "perf.col.first_pass"], note="perf.skill.note")
    counts = defaultdict(lambda: [0, 0])
    for cid, r in first_answers(cards, reviews).items():
        if period.contains(r.day):
            key = (month_of(r.day), cards[cid].group)
            counts[key][0] += r.ease > 1
            counts[key][1] += 1
    for (month, group), (passed, total) in sorted(counts.items()):
        table.rows.append([month, group, rate(passed, total)])
    return table


def puzzle_band_table(cards: dict[int, CardInfo], reviews: list[Review], period: Period, band: int = 200) -> Table:
    """First-time pass rate of the puzzle cards by rating band: difficulty held constant."""
    table = Table("perf.bands.title", ["perf.col.band", "perf.col.first_pass"], note="perf.bands.note")
    counts = defaultdict(lambda: [0, 0])
    for cid, r in first_answers(cards, reviews).items():
        card = cards[cid]
        if card.group == "puzzle" and card.rating and period.contains(r.day):
            low = card.rating // band * band
            counts[low][0] += r.ease > 1
            counts[low][1] += 1
    for low, (passed, total) in sorted(counts.items()):
        table.rows.append([f"{low}–{low + band - 1}", rate(passed, total)])
    return table


def efficiency_table(cards: dict[int, CardInfo], reviews: list[Review], period: Period, now_ms: int) -> Table:
    """
    Minutes studied, what they built (sum of FSRS recall chances = cards you would recall
    now), and the cost of taking a card to mature (interval >= 21 days).
    """
    table = Table(
        "perf.efficiency.title",
        [
            "perf.col.group", "perf.col.minutes", "perf.col.cards", "perf.col.knowledge",
            "perf.col.min_per_knowledge", "perf.col.stability", "perf.col.to_mature",
        ],
        note="perf.efficiency.note",
    )
    minutes = defaultdict(float)
    last_review: dict[int, int] = {}
    to_mature: dict[int, list] = {}  # cid -> [answers, ms, matured]
    for r in reviews:
        card = cards.get(r.cid)
        if card is None or r.type not in ANSWER_TYPES:
            continue
        last_review[r.cid] = r.ts
        progress = to_mature.setdefault(r.cid, [0, 0, False])
        if not progress[2]:
            progress[0] += 1
            progress[1] += r.time_ms
            progress[2] = r.ivl >= MATURE_DAYS
        if period.contains(r.day):
            minutes[card.group] += r.time_ms / 60000
    knowledge = defaultdict(float)
    has_fsrs = defaultdict(bool)
    stabilities = defaultdict(list)
    matured = defaultdict(list)
    studied = defaultdict(int)
    for cid, card in cards.items():
        if cid not in last_review:
            continue
        studied[card.group] += 1
        if card.stability:
            days = max(0.0, (now_ms - last_review[cid]) / DAY_MS)
            knowledge[card.group] += retrievability(card.stability, days, card.decay)
            stabilities[card.group].append(card.stability)
            has_fsrs[card.group] = True
        answers, ms, done = to_mature.get(cid, (0, 0, False))
        if done:
            matured[card.group].append((answers, ms / 60000))
    for g in sorted(studied):
        k = knowledge[g] if has_fsrs[g] else None
        cost = (
            f"{statistics.mean(a for a, _ in matured[g]):.1f} / {statistics.mean(m for _, m in matured[g]):.1f} min"
            if matured[g] else "—"
        )
        table.rows.append([
            g,
            fmt(round(minutes[g], 1)),
            studied[g],
            fmt(round(k, 1) if k is not None else None),
            fmt(round(minutes[g] / k, 2) if k else None),
            fmt(median(stabilities[g]), " d"),
            cost,
        ])
    return table


def calibration_table(cards: dict[int, CardInfo], reviews: list[Review], period: Period) -> Table:
    """True retention next to the desired retention, and by time of day."""
    table = Table("perf.calibration.title", ["perf.col.slice", "perf.col.retention", "perf.col.desired"], note="perf.calibration.note")
    total = [0, 0]
    parts = defaultdict(lambda: [0, 0])
    desired = []
    for r in reviews:
        card = cards.get(r.cid)
        if card is None or r.type != 1 or not period.contains(r.day):
            continue
        total[0] += r.ease > 1
        total[1] += 1
        part = parts[day_part(r.ts)]
        part[0] += r.ease > 1
        part[1] += 1
        if card.desired:
            desired.append(card.desired)
    target = fmt(round(100 * statistics.mean(desired), 1), "%") if desired else "—"
    table.rows.append(["perf.slice.all", rate(*total), target])
    for _, name in DAY_PARTS:
        if parts[name][1]:
            table.rows.append([f"perf.slice.{name}", rate(*parts[name]), ""])
    return table


# --- Games ---


def eligible_games(games: list[GameStats], speed: str, period: Period) -> list[GameStats]:
    return [
        g for g in games
        if (speed == "all" or g.speed == speed)
        and not g.abandoned
        and g.user_moves >= MIN_USER_MOVES
        and period.contains(date.fromisoformat(g.date) if g.date else None)
    ]


def _per40(count: int, moves: int) -> float | None:
    return round(40 * count / moves, 2) if moves else None


def _share(part: int, total: int) -> str:
    return f"{100 * part / total:.0f}% ({part}/{total})" if total else "—"


def studied_positions(cards: dict[int, CardInfo], reviews: list[Review]) -> dict[str, date]:
    """position_key -> first day a card containing it was answered (main lines only)."""
    first_day: dict[int, date] = {}
    for r in reviews:
        if r.type in ANSWER_TYPES and r.cid not in first_day:
            first_day[r.cid] = r.day
    positions: dict[str, date] = {}
    for cid, day in first_day.items():
        card = cards.get(cid)
        if card is None or not card.pgn:
            continue
        try:
            game = chess.pgn.read_game(io.StringIO(card.pgn))
        except (ValueError, IndexError):
            continue
        if game is None:
            continue
        board = game.board()
        keys = [position_key(board)]
        for move in game.mainline_moves():
            board.push(move)
            keys.append(position_key(board))
        for key in keys:
            if key not in positions or day < positions[key]:
                positions[key] = day
    return positions


def game_summary(games: list[GameStats], positions: dict[str, date] | None = None) -> list[list]:
    """[metric key, value, games it is computed on] for a set of games."""
    evaluated = [g for g in games if g.accuracy is not None]
    analysed = sum(g.analysed_moves for g in games)
    rows = [
        ["perf.game.count", len(games), len(games)],
        ["perf.game.results", " / ".join(str(sum(g.result == r for g in games)) for r in ("win", "draw", "loss")), len(games)],
        ["perf.game.accuracy", fmt(median(g.accuracy for g in evaluated)), len(evaluated)],
        ["perf.game.avg_loss", fmt(median(g.avg_loss for g in evaluated)), len(evaluated)],
        ["perf.game.lichess_accuracy", fmt(median((g.lichess or {}).get("accuracy") for g in games)), sum(bool((g.lichess or {}).get("accuracy")) for g in games)],
        ["perf.game.blunders40", fmt(_per40(sum(g.blunders for g in games), analysed)), len(games)],
        ["perf.game.mistakes40", fmt(_per40(sum(g.mistakes for g in games), analysed)), len(games)],
        ["perf.game.inaccuracies40", fmt(_per40(sum(g.inaccuracies for g in games), analysed)), len(games)],
    ]
    for phase in ("opening", "middlegame", "endgame"):
        moves = sum(g.phases.get(phase, [0, 0, 0, 0])[0] for g in games)
        errors = sum(sum(g.phases.get(phase, [0, 0, 0, 0])[2:4]) for g in games)
        # Based on moves, not games: say so
        rows.append([f"perf.game.phase_{phase}", fmt(_per40(errors, moves)), tr("perf.moves", n=moves)])
    deviated = [g for g in games if g.deviated_by]
    rows += [
        ["perf.game.book_moves", fmt(median(g.book_plies / 2 for g in games)), len(games)],
        ["perf.game.deviated_by_user", _share(sum(g.deviated_by == "user" for g in deviated), len(deviated)), len(deviated)],
        ["perf.game.win_after_book", fmt(median(g.win_after_book for g in evaluated), "%"), len(evaluated)],
        ["perf.game.win_move15", fmt(median(g.win_move15 for g in evaluated), "%"), sum(g.win_move15 is not None for g in evaluated)],
    ]
    winning = [g for g in evaluated if g.max_win is not None and g.max_win >= 80]
    losing = [g for g in evaluated if g.min_win is not None and g.min_win <= 20]
    rows += [
        ["perf.game.conversion", _share(sum(g.result == "win" for g in winning), len(winning)), len(winning)],
        ["perf.game.resilience", _share(sum(g.result != "loss" for g in losing), len(losing)), len(losing)],
        ["perf.game.missed_chances", _share(sum(g.missed or 0 for g in evaluated), sum(g.chances or 0 for g in evaluated)), len(evaluated)],
    ]
    clocked = [g for g in games if g.clock]
    book_moves = sum(g.clock["book_moves"] for g in clocked)
    low = (sum(g.clock["low_errors"] for g in clocked), sum(g.clock["low_moves"] for g in clocked))
    ok = (sum(g.clock["ok_errors"] for g in clocked), sum(g.clock["ok_moves"] for g in clocked))
    rows += [
        ["perf.game.book_seconds", fmt(round(sum(g.clock["book_seconds"] for g in clocked) / book_moves, 1) if book_moves else None, " s"), len(clocked)],
        ["perf.game.used15", fmt(median(g.clock["used15_pct"] for g in clocked), "%"), len(clocked)],
        ["perf.game.low_clock_errors", f"{fmt(_per40(*low))} / {fmt(_per40(*ok))}", len(clocked)],
    ]
    if positions is not None:
        total = repeated = 0
        for g in games:
            played = date.fromisoformat(g.date) if g.date else None
            for key in g.error_positions:
                total += 1
                repeated += bool(played and key in positions and positions[key] < played)
        rows.append(["perf.game.repeated_errors", _share(repeated, total), len(games)])
    return rows


def games_table(games: list[GameStats], positions: dict[str, date] | None = None) -> Table:
    table = Table("perf.games.title", ["perf.col.metric", "perf.col.value", "perf.col.based_on"], note="perf.games.note")
    table.rows = game_summary(games, positions)
    return table


def games_trend_table(games: list[GameStats]) -> Table:
    """The main game metrics month by month."""
    table = Table(
        "perf.trend.title",
        ["perf.col.month", "perf.game.count", "perf.game.accuracy", "perf.game.blunders40",
         "perf.game.mistakes40", "perf.game.book_moves", "perf.game.missed_chances"],
        note="perf.trend.note",
    )
    by_month = defaultdict(list)
    for g in games:
        if g.date:
            by_month[month_of(g.date)].append(g)
    for month in sorted(by_month):
        summary = {row[0]: row[1] for row in game_summary(by_month[month])}
        flag = "" if len(by_month[month]) >= MIN_GAMES else " *"
        table.rows.append([month + flag, *(summary[k] for k in table.columns[1:])])
    return table


def openings_table(
    games: list[GameStats], cards: dict[int, CardInfo], reviews: list[Review], period: Period
) -> Table:
    """By ECO code: what was studied next to how the games in it went."""
    table = Table(
        "perf.openings.title",
        ["perf.col.eco", "perf.col.reviews", "perf.col.mature", "perf.game.count",
         "perf.game.book_moves", "perf.game.deviated_by_user", "perf.game.phase_opening", "perf.game.win_move15"],
        note="perf.openings.note",
    )
    studied = defaultdict(lambda: [0, 0, 0])  # reviews, mature passed, mature total
    for r in reviews:
        card = cards.get(r.cid)
        if card is None or not card.eco or r.type != 1 or not period.contains(r.day):
            continue
        studied[card.eco][0] += 1
        if r.last_ivl >= MATURE_DAYS:
            studied[card.eco][1] += r.ease > 1
            studied[card.eco][2] += 1
    played = defaultdict(list)
    for g in games:
        if g.eco:
            played[g.eco.upper()].append(g)
    for eco in sorted(set(studied) | set(played)):
        summary = {row[0]: row[1] for row in game_summary(played[eco])} if played[eco] else {}
        reviews_n, passed, total = studied[eco]
        table.rows.append([
            eco,
            reviews_n,
            rate(passed, total),
            len(played[eco]),
            *(summary.get(k, "—") for k in table.columns[4:]),
        ])
    return table


# --- Lichess puzzle history ---


def puzzle_history_tables(entries: list[dict], period: Period, band: int = 200) -> list[Table]:
    """Attempts on Lichess by month, by rating band and by theme: fixed difficulty, no opponent."""
    chosen = [e for e in entries if period.contains(datetime.fromtimestamp(e["date"] / 1000).date())]
    monthly = Table("perf.lpuzzles.month_title", ["perf.col.month", "perf.col.win_rate", "perf.col.avg_rating"], note="perf.lpuzzles.note")
    by_month = defaultdict(list)
    for e in chosen:
        by_month[datetime.fromtimestamp(e["date"] / 1000).strftime("%Y-%m")].append(e)
    for month in sorted(by_month):
        items = by_month[month]
        monthly.rows.append([month, rate(sum(e["win"] for e in items), len(items)), round(statistics.mean(e["rating"] for e in items))])
    bands = Table("perf.lpuzzles.band_title", ["perf.col.band", "perf.col.win_rate"])
    by_band = defaultdict(list)
    for e in chosen:
        by_band[e["rating"] // band * band].append(e["win"])
    for low in sorted(by_band):
        bands.rows.append([f"{low}–{low + band - 1}", rate(sum(by_band[low]), len(by_band[low]))])
    themes = Table("perf.lpuzzles.theme_title", ["perf.col.theme", "perf.col.win_rate"])
    by_theme = defaultdict(list)
    for e in chosen:
        for t in e["themes"]:
            by_theme[t].append(e["win"])
    for theme in sorted(by_theme, key=lambda t: (-len(by_theme[t]), t))[:20]:
        themes.rows.append([theme, rate(sum(by_theme[theme]), len(by_theme[theme]))])
    return [monthly, bands, themes]


# --- CSV rows ---


def review_rows(cards: dict[int, CardInfo], reviews: list[Review]) -> list[list]:
    header = ["timestamp", "date", "hour", "card_id", "group", "subgroups", "eco", "puzzle_rating",
              "ease", "passed", "interval", "last_interval", "seconds", "type", "first_answer"]
    firsts = {id(r) for r in first_answers(cards, reviews).values()}
    rows = [header]
    for r in reviews:
        card = cards.get(r.cid)
        if card is None or r.type not in ANSWER_TYPES:
            continue
        moment = datetime.fromtimestamp(r.ts / 1000)
        rows.append([
            r.ts, moment.date().isoformat(), moment.hour, r.cid, card.group, "|".join(card.subs),
            card.eco or "", card.rating or "", r.ease, int(r.ease > 1), r.ivl, r.last_ivl,
            round(r.time_ms / 1000, 1), r.type, int(id(r) in firsts),
        ])
    return rows


def game_rows(games: list[GameStats]) -> list[list]:
    simple = [f.name for f in fields(GameStats) if f.name not in ("phases", "clock", "lichess", "error_positions")]
    clock_keys = ["base", "inc", "book_seconds", "book_moves", "used15_pct", "low_moves", "low_errors", "ok_moves", "ok_errors"]
    header = [*simple]
    for phase in ("opening", "middlegame", "endgame"):
        header += [f"{phase}_{k}" for k in ("moves", "inaccuracies", "mistakes", "blunders")]
    header += [f"clock_{k}" for k in clock_keys] + ["lichess_accuracy", "lichess_acpl", "error_positions"]
    rows = [header]
    for g in games:
        data = g.to_dict()
        row = [data[k] for k in simple]
        for phase in ("opening", "middlegame", "endgame"):
            row += list(g.phases.get(phase, [0, 0, 0, 0]))
        row += [(g.clock or {}).get(k) for k in clock_keys]
        row += [(g.lichess or {}).get("accuracy"), (g.lichess or {}).get("acpl"), "|".join(g.error_positions)]
        rows.append(row)
    return rows


# --- Headline and month by month (the panel's charts) ---


def _serious_per40(games: list[GameStats]) -> float | None:
    return _per40(sum(g.blunders + g.mistakes for g in games), sum(g.analysed_moves for g in games))


def monthly_series(
    cards: dict[int, CardInfo], reviews: list[Review], games: list[GameStats], period: Period
) -> dict[str, list[tuple[str, float | None, int]]]:
    """name -> [(YYYY-MM, value, how many answers or games it is based on)], oldest first."""
    mature = defaultdict(lambda: [0, 0])
    for r in reviews:
        if r.cid in cards and r.type == 1 and r.last_ivl >= MATURE_DAYS and period.contains(r.day):
            mature[month_of(r.day)][0] += r.ease > 1
            mature[month_of(r.day)][1] += 1
    first = defaultdict(lambda: [0, 0])
    for r in first_answers(cards, reviews).values():
        if period.contains(r.day):
            first[month_of(r.day)][0] += r.ease > 1
            first[month_of(r.day)][1] += 1
    by_month = defaultdict(list)
    for g in games:
        if g.date:
            by_month[month_of(g.date)].append(g)

    def rates(counts):
        return [(m, round(100 * p / t, 1), t) for m, (p, t) in sorted(counts.items()) if t]

    return {
        "retention": rates(mature),
        "first_pass": rates(first),
        "accuracy": [
            (m, median(g.accuracy for g in gs), sum(g.accuracy is not None for g in gs))
            for m, gs in sorted(by_month.items())
            if any(g.accuracy is not None for g in gs)
        ],
        "errors40": [(m, _serious_per40(gs), len(gs)) for m, gs in sorted(by_month.items()) if _serious_per40(gs) is not None],
    }


def headline(
    cards: dict[int, CardInfo], reviews: list[Review], games: list[GameStats], period: Period
) -> list[tuple[str, str, int]]:
    """The four numbers the panel leads with: (i18n key, value, what it is based on)."""
    mature = [0, 0]
    for r in reviews:
        if r.cid in cards and r.type == 1 and r.last_ivl >= MATURE_DAYS and period.contains(r.day):
            mature[0] += r.ease > 1
            mature[1] += 1
    first = [0, 0]
    for r in first_answers(cards, reviews).values():
        if period.contains(r.day):
            first[0] += r.ease > 1
            first[1] += 1
    evaluated = [g for g in games if g.accuracy is not None]

    def pct(passed, total):
        return f"{100 * passed / total:.1f}%" if total else "—"

    return [
        ("perf.chart.retention", pct(*mature), mature[1]),
        ("perf.chart.first_pass", pct(*first), first[1]),
        ("perf.chart.accuracy", fmt(median(g.accuracy for g in evaluated)), len(evaluated)),
        ("perf.chart.errors40", fmt(_serious_per40(games)), len(games)),
    ]
