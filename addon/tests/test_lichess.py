import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(__file__)
ADDON_DIR = os.path.join(HERE, "..", "lichess_study_importer")

# Load the add-on modules as a package without running __init__ (it needs aqt)
if "lsi" not in sys.modules:
    pkg = types.ModuleType("lsi")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["lsi"] = pkg

from lsi import chesscom, game_analysis as ga, i18n, lichess_api, note_info, puzzles  # noqa: E402
from lsi.chess_lib import chess  # noqa: E402
from lsi.pgn_split import MODE_FLIPPED, split_games  # noqa: E402


@pytest.fixture(autouse=True)
def portuguese():
    i18n.set_language("pt-BR")
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


def fixture(name: str) -> str:
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


def test_parse_several_study_links():
    text = (
        "https://lichess.org/study/s4KZKju4\n"
        "https://lichess.org/study/0QRkVohU/9VHbXCsv, 7lucWTlb https://lichess.org/study/s4KZKju4"
    )
    assert lichess_api.parse_study_urls(text) == [
        ("s4KZKju4", None),
        ("0QRkVohU", "9VHbXCsv"),
        ("7lucWTlb", None),
    ]


@pytest.mark.parametrize(
    "url,game_id",
    [
        ("https://lichess.org/5BBrW941", "5BBrW941"),
        ("lichess.org/5BBrW941/black", "5BBrW941"),
        ("https://lichess.org/5BBrW941abcd", "5BBrW941"),
        ("https://lichess.org/study/s4KZKju4", None),
        ("https://lichess.org/training/tgu12", None),
        ("https://lichess.org/@/basso01", None),
    ],
)
def test_parse_game_url(url, game_id):
    assert lichess_api.parse_game_url(url) == game_id


def test_parse_puzzle_ids():
    assert lichess_api.parse_puzzle_ids("https://lichess.org/training/tgu12 lichess.org/training/DG7B9") == [
        "tgu12",
        "DG7B9",
    ]
    assert lichess_api.parse_puzzle_ids("tgu12, DG7B9") == ["tgu12", "DG7B9"]


def test_puzzle_card():
    data = json.loads(fixture("lichess_puzzle.json"))
    card = puzzles.puzzle_card(data, win=False)
    assert card.dedupe_key == "puzzle/tgu12"
    assert card.mode == MODE_FLIPPED  # the opponent's last move comes first
    game = chess.pgn.read_game(__import__("io").StringIO(card.pgn()))
    moves = [m.uci() for m in game.mainline_moves()]
    assert moves == [data["puzzle"]["lastMove"], *data["puzzle"]["solution"]]
    assert game.headers["Orientation"] == "black"
    assert game.headers["AnkiChessId"] == "puzzle/tgu12"
    assert "lichess::puzzle::mateIn3" in card.note_tags and "lichess::puzzle::failed" in card.note_tags
    assert card.chapter_url == "https://lichess.org/training/tgu12"


def test_puzzle_from_activity_without_game():
    entry = {
        "date": 1789845997743,
        "win": False,
        "puzzle": {
            "id": "DG7B9",
            "rating": 1847,
            "plays": 5722,
            "solution": ["f3f6", "h5f6", "h1h6"],
            "themes": ["middlegame", "short", "advantage"],
            "fen": "2r2rk1/1pp2p1p/p2p1npq/3Pp2n/4P3/5QN1/PPP2P2/R2NK2R w KQ - 1 1",
            "lastMove": "e8f6",
        },
    }
    card = puzzles.puzzle_card(entry, win=False)
    assert card.mode == "puzzle"  # no game: starts at the puzzle position
    assert "1. Qxf6 Nxf6 2. Rxh6" in card.pgn()


def test_lichess_server_analysis_without_stockfish():
    game = chesscom.read_game(fixture("lichess_analysed.pgn"))
    assert ga.has_server_analysis(game)
    cards = [c for c in ga.analyze_game(game, ga.AnalysisOptions(chess.BLACK)) if c.kind in ga.ENGINE_KINDS]
    first = cards[0]
    assert first.name == "5... Melhor que d5? (Erro)"
    assert first.solution_text == "cxd4"  # "cxd4 was best"
    assert first.eval_text == "-1.9 → -0.2"  # (0.22 → 1.85) seen from Black
    assert first.dedupe_key == "lichess/AbCdEfGh/9/mistake"
    assert first.link_label == "Lichess" and first.chapter_url == "https://lichess.org/AbCdEfGh"
    assert first.note_tags == ["lichess", "lichess::mistake", "lichess::game::AbCdEfGh"]
    mates = [c for c in cards if c.kind == ga.KIND_MISSED_MATE]
    assert mates and any(c.solution_text.endswith("#") for c in mates)


def test_chapter_details():
    ch = split_games(
        '[Event "Moscow Open 2009 A"]\n[Date "2009.02.01"]\n[White "Lyubokhiner"]\n[WhiteElo "2400"]\n'
        '[Black "Yarmolenko"]\n[ECO "B28"]\n[Opening "Sicilian Defense: O\'Kelly Variation"]\n'
        '[Annotator "https://lichess.org/@/basso01"]\n[GameId "5BBrW941"]\n[ChapterName "(Bc4) Lyubokhiner"]\n'
        '[Result "0-1"]\n\n1. e4 c5 2. Nf3 a6 0-1\n'
    )[0]
    assert note_info.chapter_details(ch) == [
        "Abertura: B28 Sicilian Defense: O&#x27;Kelly Variation",
        "Lyubokhiner (2400) – Yarmolenko",
        "Moscow Open 2009 A · 2009.02.01",
        'Autor: <a href="https://lichess.org/@/basso01">basso01</a>',
        '<a href="https://lichess.org/5BBrW941">Partida original</a>',
    ]
