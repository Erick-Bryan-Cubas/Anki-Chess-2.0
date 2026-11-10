"""
Performance metrics of one analysed game, from the user's side: the denominator the
error cards lose (every move played, games without errors, accuracy, theory depth,
clock use). Saved per game (see performance_store.py) so the progress in real games
can be compared with what is studied in Anki.

Every win% is seen from the user: wins[k] is the win chance after k plies.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone

from .chess_lib import chess
from .chesscom import move_label

SCHEMA_VERSION = 1

# Lichess judges a move by the drop of its winning chances (-1..1): .3 blunder, .2 mistake,
# .1 inaccuracy (lila Advice.scala). On the 0-100 win% scale that is 15, 10 and 5 points.
DROP_KINDS = ((15.0, "blunder"), (10.0, "mistake"), (5.0, "inaccuracy"))
LABEL_KINDS = {"Blunder": "blunder", "Mistake": "mistake", "Inaccuracy": "inaccuracy"}
# Error kind -> GameStats counter, in the order of the phases' lists
COUNT_FIELDS = {"inaccuracy": "inaccuracies", "mistake": "mistakes", "blunder": "blunders"}
# An opponent move that gives you this much is a chance; giving back half of it misses it
CHANCE_GAIN = 10.0
# Clock at or under this share of the starting time: playing under time pressure
LOW_CLOCK_SHARE = 0.10
OPENING_LAST_MOVE = 10
ENDGAME_PIECES = 6  # queens, rooks, bishops and knights left on the board (Lichess' divider)
PHASES = ("opening", "middlegame", "endgame")
TIME_CONTROL_RE = re.compile(r"^(\d+)(?:\+(\d+))?$")


def win_percent(score) -> float:
    """Lichess win chance (0-100) for a score seen from the side of interest."""
    cp = score.score(mate_score=10000)
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def move_accuracy(drop: float) -> float:
    """Lichess accuracy of one move from its win% drop (lichess.org/page/accuracy)."""
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def drop_kind(drop: float) -> str | None:
    return next((kind for threshold, kind in DROP_KINDS if drop >= threshold), None)


def parse_time_control(text: str | None) -> tuple[int, int] | None:
    """(base seconds, increment) from "600+5"; None for correspondence or unknown."""
    m = TIME_CONTROL_RE.match((text or "").strip())
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def speed_of(time_control: tuple[int, int] | None) -> str:
    """Lichess' speed classes, by the estimated game time (base + 40 increments)."""
    if time_control is None:
        return "correspondence"
    total = time_control[0] + 40 * time_control[1]
    for limit, name in ((29, "ultrabullet"), (179, "bullet"), (479, "blitz"), (1499, "rapid")):
        if total < limit:
            return name
    return "classical"


def position_key(board: chess.Board) -> str:
    """Short fingerprint of a position (pieces, side to move, castling, en passant)."""
    return hashlib.sha1(board.epd().encode()).hexdigest()[:10]


def phase_of(board: chess.Board) -> str:
    if board.fullmove_number <= OPENING_LAST_MOVE:
        return "opening"
    pieces = sum(
        len(board.pieces(piece, color))
        for color in chess.COLORS
        for piece in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
    )
    return "endgame" if pieces <= ENDGAME_PIECES else "middlegame"


@dataclass
class GameStats:
    source: str  # lichess | chesscom
    game_id: str
    color: str  # white | black: the side the user played
    date: str | None = None  # YYYY-MM-DD
    time_control: str | None = None
    speed: str | None = None
    result: str | None = None  # win | draw | loss, for the user
    rating: int | None = None
    opp_rating: int | None = None
    eco: str | None = None
    opening: str | None = None
    plies: int = 0
    user_moves: int = 0
    abandoned: bool = False
    # Theory: plies played in the catalog, where it was left and by whom (user | opponent)
    book_plies: int = 0
    deviation_ply: int | None = None
    deviated_by: str | None = None
    # Where the evaluations came from: eval ([%eval] in the PGN), engine, labels or None
    eval_source: str | None = None
    # User moves after the theory with an evaluation before and after them
    analysed_moves: int = 0
    accuracy: float | None = None  # mean Lichess accuracy of those moves
    avg_loss: float | None = None  # mean win% drop of those moves
    inaccuracies: int = 0
    mistakes: int = 0
    blunders: int = 0
    # phase -> [moves, inaccuracies, mistakes, blunders]
    phases: dict[str, list[int]] = field(default_factory=dict)
    win_after_book: float | None = None
    win_move15: float | None = None
    max_win: float | None = None
    min_win: float | None = None
    chances: int | None = None  # opponent mistakes worth >= 10 win% to you
    missed: int | None = None  # ...answered by giving back at least half of it
    # {base, inc, book_seconds, book_moves, used15_pct, low_moves, low_errors, ok_moves, ok_errors}
    clock: dict | None = None
    lichess: dict | None = None  # Lichess' own accuracy and acpl, when its export gives them
    # position_key() of the positions where you made a mistake or a blunder
    error_positions: list[str] = field(default_factory=list)
    analysed_at: str = ""
    v: int = SCHEMA_VERSION

    @property
    def key(self) -> str:
        return f"{self.source}/{self.game_id}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> GameStats:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def wins_from_pgn(game: chess.pgn.Game, user: chess.Color) -> list[float | None]:
    """Win% after each ply from the [%eval] comments (Lichess server analysis)."""
    wins: list[float | None] = [None]
    for node in game.mainline():
        score = node.eval()
        wins.append(win_percent(score.pov(user)) if score is not None else None)
    return wins


def _result(headers, user: chess.Color) -> str | None:
    result = headers.get("Result", "*")
    if result == "1/2-1/2":
        return "draw"
    if result in ("1-0", "0-1"):
        return "win" if (result == "1-0") == (user == chess.WHITE) else "loss"
    return None


def _rating(headers, color: chess.Color) -> int | None:
    value = headers.get("WhiteElo" if color == chess.WHITE else "BlackElo", "")
    return int(value) if value.isdigit() else None


def _date(headers) -> str | None:
    for key in ("UTCDate", "Date", "EndDate"):
        value = headers.get(key, "")
        if re.match(r"^\d{4}\.\d{2}\.\d{2}$", value):
            return value.replace(".", "-")
    return None


def _first_known(wins: list[float | None], *plies: int) -> float | None:
    for ply in plies:
        if 0 <= ply < len(wins) and wins[ply] is not None:
            return round(wins[ply], 1)
    return None


def _clock_stats(nodes, boards, user, time_control, book_plies, errors_at) -> dict | None:
    if time_control is None or time_control[0] <= 0:
        return None
    base, inc = time_control
    clocks = [node.clock() for node in nodes]
    user_plies = [i for i in range(len(nodes)) if boards[i].turn == user]
    if not user_plies or any(clocks[i] is None for i in user_plies):
        return None
    stats = {"base": base, "inc": inc, "book_seconds": 0.0, "book_moves": 0, "used15_pct": None,
             "low_moves": 0, "low_errors": 0, "ok_moves": 0, "ok_errors": 0}
    used15, reached15 = 0.0, False
    for i in user_plies:
        before = clocks[i - 2] if i >= 2 else base
        spent = max(0.0, before - clocks[i] + inc)
        if i < book_plies:
            stats["book_seconds"] += spent
            stats["book_moves"] += 1
        if boards[i].fullmove_number <= 15:
            used15 += spent
            reached15 = reached15 or boards[i].fullmove_number == 15
        if i in errors_at:  # analysed moves only: (move counted, was a mistake or blunder)
            low = "low" if before <= LOW_CLOCK_SHARE * base else "ok"
            stats[f"{low}_moves"] += 1
            stats[f"{low}_errors"] += int(errors_at[i])
    stats["book_seconds"] = round(stats["book_seconds"], 1)
    if reached15:
        stats["used15_pct"] = round(100 * used15 / base, 1)
    return stats


def collect_stats(
    game: chess.pgn.Game,
    source: str,
    game_id: str,
    user: chess.Color,
    wins: list[float | None],
    book,
    eval_source: str | None,
    official: dict | None = None,
) -> GameStats:
    """
    The game's metrics from its win% timeline (wins[k]: after k plies, None when unknown)
    and its theory (openings.BookResult). Moves still in the catalog are not judged.
    """
    h = game.headers
    nodes = list(game.mainline())
    boards = [game.board()]
    for node in nodes:
        board = boards[-1].copy()
        board.push(node.move)
        boards.append(board)
    time_control = parse_time_control(h.get("TimeControl"))
    stats = GameStats(
        source=source,
        game_id=game_id,
        color="white" if user == chess.WHITE else "black",
        date=_date(h),
        time_control=h.get("TimeControl") or None,
        speed=speed_of(time_control) if h.get("TimeControl") else None,
        result=_result(h, user),
        rating=_rating(h, user),
        opp_rating=_rating(h, not user),
        eco=h.get("ECO") or None,
        opening=book.opening_name or h.get("Opening") or None,
        plies=len(nodes),
        user_moves=sum(boards[i].turn == user for i in range(len(nodes))),
        abandoned="abandon" in h.get("Termination", "").lower(),
        book_plies=book.last_book_ply,
        deviation_ply=book.deviation_ply,
        eval_source=eval_source,
        phases={phase: [0, 0, 0, 0] for phase in PHASES},
        lichess=official or None,
        analysed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )
    if book.deviation_ply is not None:
        stats.deviated_by = "user" if boards[book.deviation_ply].turn == user else "opponent"

    labeled = eval_source == "labels"
    accuracies, losses = [], []
    errors_at: dict[int, bool] = {}  # ply -> was a mistake or blunder (analysed moves)
    for i in range(book.last_book_ply, len(nodes)):
        if boards[i].turn != user:
            continue
        if wins[i] is not None and wins[i + 1] is not None:
            drop = max(0.0, wins[i] - wins[i + 1])
            kind = drop_kind(drop)
            accuracies.append(move_accuracy(drop))
            losses.append(drop)
        elif labeled:
            kind = LABEL_KINDS.get(move_label(nodes[i]))
        else:
            continue
        stats.analysed_moves += 1
        errors_at[i] = kind in ("mistake", "blunder")
        if errors_at[i]:
            stats.error_positions.append(position_key(boards[i]))
        phase = stats.phases[phase_of(boards[i])]
        phase[0] += 1
        if kind:
            name = COUNT_FIELDS[kind]
            setattr(stats, name, getattr(stats, name) + 1)
            phase[1 + list(COUNT_FIELDS).index(kind)] += 1

    if accuracies:
        stats.accuracy = round(sum(accuracies) / len(accuracies), 1)
        stats.avg_loss = round(sum(losses) / len(losses), 1)
        known = [w for w in wins[book.last_book_ply:] if w is not None]
        stats.max_win, stats.min_win = round(max(known), 1), round(min(known), 1)
        stats.win_after_book = _first_known(wins, book.last_book_ply, book.last_book_ply + 1)
        stats.win_move15 = _first_known(wins, 30, 31)
        stats.chances = stats.missed = 0
        for j in range(book.last_book_ply, len(nodes) - 1):
            if boards[j].turn == user or None in (wins[j], wins[j + 1], wins[j + 2]):
                continue
            gain = wins[j + 1] - wins[j]
            if gain >= CHANCE_GAIN:
                stats.chances += 1
                stats.missed += int(wins[j + 1] - wins[j + 2] >= gain / 2)
    elif labeled:
        stats.missed = sum(
            move_label(nodes[i]) == "Miss"
            for i in range(book.last_book_ply, len(nodes))
            if boards[i].turn == user
        )

    stats.clock = _clock_stats(nodes, boards, user, time_control, book.last_book_ply, errors_at)
    return stats
