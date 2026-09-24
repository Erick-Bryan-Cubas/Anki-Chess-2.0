import os
import sys

import pytest

HERE = os.path.dirname(__file__)
# Import the pure modules directly: the package __init__ depends on aqt.
sys.path.insert(0, os.path.join(HERE, "..", "lichess_study_importer"))

import pgn_split as p  # noqa: E402
from lichess_api import parse_study_url  # noqa: E402


@pytest.fixture(scope="module")
def chapters():
    with open(os.path.join(HERE, "fixtures", "pl05a.pgn"), encoding="utf-8") as f:
        return p.split_games(f.read())


def by_id(chapters, chapter_id):
    return next(c for c in chapters if c.chapter_id == chapter_id)


def test_split_counts(chapters):
    kinds = [c.kind for c in chapters]
    assert len(chapters) == 27
    assert kinds.count(p.KIND_EXERCISE) == 16
    assert kinds.count(p.KIND_GAME) == 10
    assert kinds.count(p.KIND_EMPTY) == 1
    assert all(c.study_id == "7lucWTlb" for c in chapters)


def test_duplicate_tags_removed(chapters):
    pgn = chapters[0].pgn()
    assert pgn.count("[FEN ") == 1
    assert chapters[0].fen.startswith("r2qk2r/")


@pytest.mark.parametrize(
    "chapter_id,mode",
    [
        ("kZ9o8FTD", p.MODE_PUZZLE),  # "qual o melhor lance para as pretas?"
        ("9joqOtyZ", p.MODE_PUZZLE),  # 22... Qh5#
        ("Hx6Og5K3", p.MODE_PUZZLE),  # 0-1, black to move
        ("SJh3zsIz", p.MODE_PUZZLE),  # peão passado
        ("NetioIAN", p.MODE_FLIPPED),  # 1-0, black to move
        ("QtPSc5GK", p.MODE_FLIPPED),  # 1-0, black to move
        ("etwN9soc", p.MODE_FLIPPED),  # draw, "Jogam as brancas"
        ("lZ8fB4Ai", p.MODE_FLIPPED),  # "Jogam as pretas", white to move
        ("MRD53qq4", p.MODE_STUDY),  # full game
    ],
)
def test_suggested_mode(chapters, chapter_id, mode):
    assert by_id(chapters, chapter_id).suggested_mode == mode


def test_empty_chapter(chapters):
    assert by_id(chapters, "DxgnzhzB").kind == p.KIND_EMPTY


def test_anno_stripped(chapters):
    pgn = by_id(chapters, "U1jhX7Mv").pgn()
    assert "[%anno" not in pgn
    assert "Adicionando um novo ataque" in pgn
    assert "[%anno" in by_id(chapters, "U1jhX7Mv").pgn(strip_anno=False)


def test_tag_like_line_inside_comment_does_not_split():
    text = '[Event "a"]\n\n1. e4 { comentário\n[Event "falso"]\n} e5 *\n\n[Event "b"]\n\n1. d4 *\n'
    chs = p.split_games(text)
    assert [c.tags["Event"] for c in chs] == ["a", "b"]


def test_crlf_and_single_game_without_tags():
    chs = p.split_games("1. e4 e5 2. Nf3 *\r\n")
    assert len(chs) == 1 and chs[0].kind == p.KIND_GAME


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://lichess.org/study/7lucWTlb", ("7lucWTlb", None)),
        ("lichess.org/study/7lucWTlb/kZ9o8FTD", ("7lucWTlb", "kZ9o8FTD")),
        ("https://lichess.org/study/7lucWTlb/kZ9o8FTD#12", ("7lucWTlb", "kZ9o8FTD")),
        ("7lucWTlb", ("7lucWTlb", None)),
        ("https://example.com/x", None),
    ],
)
def test_parse_study_url(url, expected):
    assert parse_study_url(url) == expected
