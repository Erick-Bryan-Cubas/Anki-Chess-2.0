import os
import sys
import types
from datetime import date, datetime

import pytest

HERE = os.path.dirname(__file__)
ADDON_DIR = os.path.join(HERE, "..", "lichess_study_importer")

if "lsi" not in sys.modules:
    pkg = types.ModuleType("lsi")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["lsi"] = pkg

from lsi import performance as pf, performance_store as store  # noqa: E402
from lsi.chess_lib import chess  # noqa: E402
from lsi.game_stats import GameStats, position_key  # noqa: E402

DAY = pf.DAY_MS


def ts(day: str, hour: int = 10) -> int:
    return int(datetime.fromisoformat(f"{day}T{hour:02d}:00:00").timestamp() * 1000)


def review(day, cid, ease, ivl=10, last_ivl=5, seconds=20, kind=1, hour=10):
    return pf.Review(ts(day, hour), cid, ease, ivl, last_ivl, seconds * 1000, kind)


class FakeCol:
    def __init__(self):
        self.config = {}

    def get_config(self, key, default=None):
        return self.config.get(key, default)

    def set_config(self, key, value):
        self.config[key] = value

    def remove_config(self, key):
        self.config.pop(key, None)

    def all_config(self):
        return dict(self.config)


# --- Classification ---


@pytest.mark.parametrize(
    "tags,pgn,expected",
    [
        (["lichess", "lichess::puzzle", "lichess::puzzle::fork", "lichess::puzzle::failed"],
         '[ChapterName "Puzzle abc12 (1734)"]', ("puzzle", ["fork"], None, 1734)),
        (["chesscom", "chesscom::blunder", "chesscom::game::123"], "", ("game_error", ["blunder"], None, None)),
        (["lichess", "lichess::book_line", "eco::C45"], "", ("opening", ["book_line"], "C45", None)),
        (["lichess", "lichess::line", "lichess::study::abc", "eco::b30"], "", ("study", ["line"], "B30", None)),
        (["lichess", "lichess::game"], "", ("study", ["game"], None, None)),
        # Old notes without these tags: the id in the PGN
        ([], '[AnkiChessId "lichess/AbCd/12/mistake"]', ("game_error", ["mistake"], None, None)),
        ([], '[AnkiChessId "book/0123abcd"]', ("opening", ["book_line"], None, None)),
        ([], '[AnkiChessId "study/abc/def"]', ("study", [], None, None)),
        (["my_tag"], "1. e4 e5", ("other", [], None, None)),
    ],
)
def test_classify(tags, pgn, expected):
    assert pf.classify(tags, pgn) == expected


def test_card_from_row_reads_fsrs_state():
    card = pf.card_from_row(1, " lichess lichess::puzzle leech ", "PGN\x1ftext", '{"s": 12.5, "d": 5.0, "dr": 0.9}', 0.85)
    assert (card.group, card.stability, card.desired, card.leech, card.pgn) == ("puzzle", 12.5, 0.9, True, "PGN")
    assert pf.card_from_row(2, "", "", "", 0.85).desired == 0.85


# --- Helpers ---


def test_wilson_and_rate():
    low, high = pf.wilson(80, 100)
    assert low < 80 < high and low == pytest.approx(71.1, abs=0.2)
    assert pf.rate(0, 0) == "—"
    assert pf.rate(9, 10).endswith("· 10 *")  # too few answers
    assert not pf.rate(45, 50).endswith("*")


def test_retrievability():
    assert pf.retrievability(10, 10, 0.5) == pytest.approx(0.9)
    assert pf.retrievability(10, 10, 0.1542) == pytest.approx(0.9)  # FSRS-6 decay
    assert pf.retrievability(10, 0, None) == 1


def test_periods():
    today = date(2026, 11, 10)
    assert pf.period_from("30", today, None) == pf.Period(date(2026, 10, 12), today)
    assert pf.period_from("protocol", today, "2026-11-01") == pf.Period(date(2026, 11, 1), None)
    assert pf.period_from("before_protocol", today, "2026-11-01") == pf.Period(None, date(2026, 10, 31))
    assert pf.period_from("protocol", today, None) == pf.Period()


# --- Review log metrics ---


@pytest.fixture
def deck():
    cards = {
        1: pf.CardInfo(1, "puzzle", ["fork"], rating=1650, stability=10.0, desired=0.9),
        2: pf.CardInfo(2, "puzzle", ["pin"], rating=1850, stability=30.0, desired=0.9),
        3: pf.CardInfo(3, "opening", ["book_line"], eco="C45", leech=True),
    }
    reviews = [
        review("2026-10-01", 1, 1, ivl=0, last_ivl=0, kind=0),  # new: failed
        review("2026-10-01", 1, 3, ivl=1, last_ivl=0, kind=0),
        review("2026-10-02", 2, 3, ivl=1, last_ivl=0, kind=0),  # new: passed
        review("2026-10-02", 3, 3, ivl=1, last_ivl=0, kind=0),
        review("2026-10-10", 1, 3, ivl=10, last_ivl=1, hour=22),
        review("2026-10-20", 2, 3, ivl=30, last_ivl=25, hour=8),  # mature pass
        review("2026-10-20", 3, 1, ivl=1, last_ivl=25, hour=8),  # mature lapse
        review("2026-10-21", 3, 0, ivl=5, last_ivl=1, kind=4),  # manual: not an answer
    ]
    return cards, reviews


def test_memory_table(deck):
    cards, reviews = deck
    table = pf.memory_table(cards, reviews, pf.Period())
    rows = {row[0]: row for row in table.rows}
    assert rows["opening"][2].startswith("0.0%") and rows["opening"][4] == 1  # lapse, leech
    assert rows["puzzle"][1].startswith("100.0%") and rows["puzzle"][2].startswith("100.0%")
    by_eco = pf.memory_table(cards, reviews, pf.Period(), by="eco")
    assert [r[0] for r in by_eco.rows] == ["C45"]
    by_sub = pf.memory_table(cards, reviews, pf.Period(), by="sub")
    assert {r[0] for r in by_sub.rows} == {"puzzle:fork", "puzzle:pin", "opening:book_line"}


def test_skill_and_bands(deck):
    cards, reviews = deck
    firsts = pf.first_answers(cards, reviews)
    assert {cid: r.ease for cid, r in firsts.items()} == {1: 1, 2: 3, 3: 3}
    skill = pf.skill_table(cards, reviews, pf.Period())
    assert [r[:2] for r in skill.rows] == [["2026-10", "opening"], ["2026-10", "puzzle"]]
    assert skill.rows[1][2].startswith("50.0%")
    bands = pf.puzzle_band_table(cards, reviews, pf.Period())
    assert [(r[0], r[1][:6]) for r in bands.rows] == [("1600–1799", "0.0% ("), ("1800–1999", "100.0%")]


def test_efficiency_and_calibration(deck):
    cards, reviews = deck
    now = ts("2026-10-20", 12)
    table = pf.efficiency_table(cards, reviews, pf.Period(), now)
    rows = {row[0]: row for row in table.rows}
    assert rows["puzzle"][2] == 2  # cards studied
    assert float(rows["puzzle"][3]) > 1.5  # both recalled with high chance
    assert rows["opening"][3] == "—"  # no FSRS state
    assert rows["puzzle"][6].startswith("2.0 /")  # card 2: two answers to reach 21 days
    cal = pf.calibration_table(cards, reviews, pf.Period())
    assert cal.rows[0][0] == "perf.slice.all" and cal.rows[0][2] == "90.0%"
    assert {r[0] for r in cal.rows[1:]} == {"perf.slice.morning", "perf.slice.evening"}


# --- Games ---


def game(**kw):
    base = dict(source="lichess", game_id="g", color="white", date="2026-10-05", speed="blitz",
                result="win", user_moves=30, analysed_moves=25, accuracy=85.0, avg_loss=4.0,
                blunders=1, mistakes=1, inaccuracies=2, book_plies=8, deviated_by="user",
                win_after_book=55.0, win_move15=60.0, max_win=90.0, min_win=40.0, chances=2, missed=1,
                phases={"opening": [5, 0, 0, 0], "middlegame": [15, 1, 1, 1], "endgame": [5, 1, 0, 0]},
                clock={"base": 180, "inc": 2, "book_seconds": 8.0, "book_moves": 4, "used15_pct": 30.0,
                       "low_moves": 5, "low_errors": 1, "ok_moves": 20, "ok_errors": 1},
                eco="C45")
    base.update(kw)
    return GameStats(**base)


def test_eligible_games():
    games = [game(game_id="a"), game(game_id="b", speed="rapid"), game(game_id="c", abandoned=True),
             game(game_id="d", user_moves=10), game(game_id="e", date="2025-01-01")]
    chosen = pf.eligible_games(games, "blitz", pf.Period(date(2026, 1, 1), None))
    assert [g.game_id for g in chosen] == ["a"]


def test_game_summary():
    positions = {"p1": date(2026, 9, 1)}
    games = [game(game_id="a", error_positions=["p1", "p2"]), game(game_id="b", result="loss", max_win=70.0, min_win=10.0)]
    rows = {r[0]: r[1] for r in pf.game_summary(games, positions)}
    assert rows["perf.game.count"] == 2 and rows["perf.game.results"] == "1 / 0 / 1"
    assert rows["perf.game.blunders40"] == "1.6"  # 2 blunders in 50 moves
    assert rows["perf.game.phase_middlegame"] == "5.3"  # 4 errors in 30 moves
    assert rows["perf.game.conversion"] == "100% (1/1)"
    assert rows["perf.game.resilience"] == "0% (0/1)"
    assert rows["perf.game.missed_chances"] == "50% (2/4)"
    assert rows["perf.game.book_seconds"] == "2.0 s"
    assert rows["perf.game.low_clock_errors"] == "8.0 / 2.0"
    assert rows["perf.game.repeated_errors"] == "50% (1/2)"


def test_games_trend_and_openings(deck):
    cards, reviews = deck
    games = [game(game_id="a"), game(game_id="b", date="2026-11-02", eco="B30")]
    trend = pf.games_trend_table(games)
    assert [r[0] for r in trend.rows] == ["2026-10 *", "2026-11 *"]
    openings = pf.openings_table(games, cards, reviews, pf.Period())
    rows = {r[0]: r for r in openings.rows}
    assert rows["C45"][1] == 1 and rows["C45"][3] == 1  # one review, one game
    assert rows["B30"][1] == 0 and rows["B30"][3] == 1


def test_studied_positions():
    board = chess.Board()
    cards = {1: pf.CardInfo(1, "opening", pgn="1. e4 e5 2. Nf3 *")}
    positions = pf.studied_positions(cards, [review("2026-10-01", 1, 3, kind=0)])
    board.push_san("e4")
    assert positions[position_key(board)] == date(2026, 10, 1)
    assert len(positions) == 4


def test_puzzle_history_tables():
    entries = [
        {"id": "a", "date": ts("2026-10-01"), "win": True, "rating": 1500, "themes": ["fork"]},
        {"id": "b", "date": ts("2026-10-02"), "win": False, "rating": 1700, "themes": ["fork", "pin"]},
        {"id": "c", "date": ts("2026-11-02"), "win": True, "rating": 1710, "themes": ["pin"]},
    ]
    monthly, bands, themes = pf.puzzle_history_tables(entries, pf.Period())
    assert [r[0] for r in monthly.rows] == ["2026-10", "2026-11"] and monthly.rows[0][2] == 1600
    assert [r[0] for r in bands.rows] == ["1400–1599", "1600–1799"]
    assert [r[0] for r in themes.rows] == ["fork", "pin"]


def test_csv_rows(deck):
    cards, reviews = deck
    rows = pf.review_rows(cards, reviews)
    assert rows[0][0] == "timestamp" and len(rows) == 8  # the manual entry is left out
    assert sum(r[-1] for r in rows[1:]) == 3  # first answers
    games = pf.game_rows([game(game_id="a", lichess={"accuracy": 80}, error_positions=["x", "y"])])
    header, row = games
    assert len(header) == len(row)
    assert row[header.index("middlegame_blunders")] == 1
    assert row[header.index("clock_used15_pct")] == 30.0
    assert row[header.index("lichess_accuracy")] == 80 and row[-1] == "x|y"


# --- Store ---


def test_store_games_in_the_collection_config():
    col = FakeCol()
    stats = game(game_id="a")
    assert store.save_game(col, stats)
    again = game(game_id="a", analysed_at="2030-01-01")
    assert not store.save_game(col, again)  # same metrics: no write to sync
    assert store.save_game(col, game(game_id="a", blunders=3))
    col.set_config("other_addon_key", {"x": 1})
    col.set_config(store.GAME_PREFIX + "broken", {"unknown": 1})
    assert [g.blunders for g in store.load_games(col)] == [3]
    store.remove_game(col, "lichess/a")
    assert store.load_games(col) == []


def test_protocol_start():
    col = FakeCol()
    assert store.protocol_start(col) is None
    store.set_protocol_start(col, "2026-11-10")
    assert store.protocol_start(col) == "2026-11-10"
    store.set_protocol_start(col, None)
    assert store.protocol_start(col) is None


def test_puzzle_cache(tmp_path):
    path = str(tmp_path / "sub" / "cache.json")
    assert store.load_puzzle_activity(path) == {}
    api = [{"date": 2, "win": True, "puzzle": {"id": "b", "rating": 1500, "themes": ["fork"]}},
           {"date": 1, "win": False, "puzzle": {"id": "a", "rating": 1400, "themes": []}}]
    data = store.merge_puzzle_activity({}, "Me", api)
    data = store.merge_puzzle_activity(data, "me", api[:1])  # repeated: kept once
    assert [e["id"] for e in data["entries"]] == ["a", "b"]
    store.save_puzzle_activity(data, path)
    assert store.load_puzzle_activity(path) == data
    assert store.merge_puzzle_activity(data, "other", [])["entries"] == []  # another account


def test_monthly_series_and_headline(deck):
    cards, reviews = deck
    games = [game(game_id="a"), game(game_id="b", date="2026-11-02", accuracy=None)]
    series = pf.monthly_series(cards, reviews, games, pf.Period())
    assert series["retention"] == [("2026-10", 50.0, 2)]
    assert series["first_pass"] == [("2026-10", 66.7, 3)]
    assert series["accuracy"] == [("2026-10", 85.0, 1)]
    assert [m for m, _, _ in series["errors40"]] == ["2026-10", "2026-11"]
    tiles = pf.headline(cards, reviews, games, pf.Period())
    assert [t[1] for t in tiles] == ["50.0%", "66.7%", "85.0", "3.2"]
    assert [t[2] for t in tiles] == [2, 3, 1, 2]
