import io
import os
import sys
import types

import pytest

HERE = os.path.dirname(__file__)
ADDON_DIR = os.path.join(HERE, "..", "lichess_study_importer")

if "lsi" not in sys.modules:
    pkg = types.ModuleType("lsi")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["lsi"] = pkg

from lsi import chesscom, game_analysis as ga, game_stats as gs  # noqa: E402
from lsi.chess_lib import chess  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return chesscom.read_game(f.read())


class MaterialEngine:
    """Stand-in for Stockfish: the material after each move, one ply deep."""

    @staticmethod
    def material(board):
        return sum(
            VALUES[p.piece_type] * (1 if p.color == chess.WHITE else -1) for p in board.piece_map().values()
        )

    def _info(self, board, move):
        board.push(move)
        score = chess.engine.PovScore(chess.engine.Cp(100 * self.material(board)), chess.WHITE)
        board.pop()
        return {"score": score, "pv": [move]}

    def analyse(self, board, limit, multipv=None, root_moves=None):
        if root_moves:
            return self._info(board, root_moves[0])
        infos = [self._info(board, m) for m in board.legal_moves]
        infos.sort(key=lambda i: i["score"].pov(board.turn).score(), reverse=True)
        return infos[:multipv] if multipv else infos[0]


def test_helpers():
    assert gs.parse_time_control("600+5") == (600, 5)
    assert gs.parse_time_control("180") == (180, 0)
    assert gs.parse_time_control("-") is None
    assert [gs.speed_of(gs.parse_time_control(t)) for t in ("60+0", "180+2", "600+5", "1800+0")] == [
        "bullet", "blitz", "rapid", "classical",
    ]
    assert gs.speed_of(None) == "correspondence"
    assert gs.move_accuracy(0) == pytest.approx(100, abs=0.01)
    assert gs.move_accuracy(100) == 0
    assert [gs.drop_kind(d) for d in (4.9, 5, 10, 15, 40)] == [None, "inaccuracy", "mistake", "blunder", "blunder"]


def test_lichess_server_analysis_matches_its_labels():
    """The win% drops judge the moves as Lichess does (15/10/5 points)."""
    game = read("lichess_analysed.pgn")
    wins = gs.wins_from_pgn(game, chess.BLACK)
    nodes = list(game.mainline())
    checked = 0
    for i, node in enumerate(nodes[:40]):  # the middlegame: no mate scores
        label = chesscom.move_label(node)
        if label not in gs.LABEL_KINDS or wins[i] is None:
            continue
        mover_is_black = i % 2 == 1
        drop = (wins[i] - wins[i + 1]) if mover_is_black else (wins[i + 1] - wins[i])
        assert gs.drop_kind(drop) == gs.LABEL_KINDS[label], (i, node.san(), drop)
        checked += 1
    assert checked >= 10


def test_stats_from_lichess_evals():
    game = read("lichess_analysed.pgn")
    _, stats = ga.analyze_game_with_stats(game, ga.AnalysisOptions(chess.BLACK), official={"accuracy": 71})
    assert (stats.source, stats.game_id, stats.color) == ("lichess", "AbCdEfGh", "black")
    assert stats.date == "2026-10-01" and stats.speed == "rapid" and stats.time_control == "600+5"
    assert stats.result == "win"  # 0-1
    assert (stats.rating, stats.opp_rating) == (1766, 1828)
    assert stats.eval_source == "eval"
    assert stats.user_moves == len(list(game.mainline())) // 2
    assert stats.analysed_moves > 30
    assert 0 < stats.accuracy < 100 and stats.avg_loss > 0
    assert stats.blunders >= 2 and stats.mistakes >= 3  # 16... Bh6??, 17... Re8?? / 5... d5?, 8... c4?...
    assert sum(sum(p[1:]) for p in stats.phases.values()) == stats.inaccuracies + stats.mistakes + stats.blunders
    assert sum(p[0] for p in stats.phases.values()) == stats.analysed_moves
    assert stats.chances >= 1 and 0 <= stats.missed <= stats.chances  # 6. e5?? was a gift
    assert stats.min_win <= stats.win_after_book <= stats.max_win
    assert stats.clock is None  # the export had no clocks
    assert stats.lichess == {"accuracy": 71}


def test_stats_from_chesscom_labels_and_clock():
    game = read("chesscom_review.pgn")
    _, stats = ga.analyze_game_with_stats(game, ga.AnalysisOptions(chess.WHITE))
    assert (stats.source, stats.game_id) == ("chesscom", "184431566002")
    assert stats.eval_source == "labels"
    assert stats.accuracy is None
    assert (stats.blunders, stats.mistakes) == (1, 1)  # 19. bxa5??, 21. f4?
    assert stats.missed == 3 and stats.chances is None  # Chess.com's "Miss" labels
    assert (stats.book_plies, stats.deviation_ply, stats.deviated_by) == (6, 6, "user")
    clock = stats.clock
    assert (clock["base"], clock["inc"], clock["book_moves"]) == (600, 5, 3)
    assert clock["book_seconds"] > 0
    assert clock["low_moves"] + clock["ok_moves"] == stats.analysed_moves
    assert clock["low_errors"] + clock["ok_errors"] == stats.blunders + stats.mistakes


def test_engine_scan_counts_a_missed_chance():
    # 2... Qg5?? leaves the theory hanging the queen to Nf3, and 3. Nc3 doesn't take it
    pgn = '[Result "*"]\n[TimeControl "180+2"]\n\n1. e4 e5 2. Nf3 Qg5 3. Nc3 Qd8 *'
    game = chess.pgn.read_game(io.StringIO(pgn))
    options = ga.AnalysisOptions(chess.WHITE, kinds=set())
    cards, stats = ga.analyze_game_with_stats(game, options, MaterialEngine())
    assert cards == []  # metrics only
    assert stats.eval_source == "engine"
    assert stats.speed == "blitz"
    assert (stats.book_plies, stats.deviated_by) == (3, "opponent")
    assert stats.chances == 1 and stats.missed == 1
    assert stats.analysed_moves == 1 and stats.blunders == 1  # 3. Nc3 lets the queen go
    assert stats.win_after_book == 50.0


def test_round_trip():
    stats = gs.GameStats(source="lichess", game_id="x", color="white", phases={"opening": [1, 0, 0, 0]})
    data = stats.to_dict()
    data["future_field"] = 1  # written by a newer version: ignored
    assert gs.GameStats.from_dict(data) == stats
    assert stats.key == "lichess/x"
