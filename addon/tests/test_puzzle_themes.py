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

from lsi import i18n, puzzle_themes  # noqa: E402


@pytest.fixture(autouse=True)
def english_after():
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


def test_theme_names_in_both_languages():
    i18n.set_language("en")
    keys = ["mateIn1", "backRankMate", "middlegame"]
    assert puzzle_themes.theme_names(keys) == "Mate in 1, Back rank mate, Middlegame"
    i18n.set_language("pt-BR")
    assert puzzle_themes.theme_names(keys) == "Mate em 1, Mate do corredor, Meio-jogo"


def test_a_theme_lichess_added_later_reads_as_words():
    assert puzzle_themes.theme_name("doubleRookMate") == "Double rook mate"
    assert puzzle_themes.theme_name("mateIn6") == "Mate in 6"


def test_every_theme_has_both_names():
    for key, names in puzzle_themes.THEMES.items():
        assert len(names) == 2 and all(n.strip() for n in names), key


def test_puzzle_stats_by_theme():
    tags = [
        " lichess lichess::puzzle lichess::puzzle::result::failed lichess::puzzle::theme::fork lichess::puzzle::theme::short ",
        " lichess lichess::puzzle lichess::puzzle::result::solved lichess::puzzle::theme::fork my_tag ",
        " lichess lichess::puzzle lichess::puzzle::result::solved lichess::puzzle::theme::mateIn1 ",
        # Tagged before the result:: tags (a sync not made yet since the update): still failed
        " lichess lichess::puzzle lichess::puzzle::failed lichess::puzzle::theme::pin ",
        " lichess lichess::study::abcdefgh ",  # not a puzzle
    ]
    total, failed, themes = puzzle_themes.puzzle_stats(tags)
    assert (total, failed) == (4, 2)
    assert themes == {"fork": [2, 1], "short": [1, 1], "mateIn1": [1, 0], "pin": [1, 1]}


def test_solved_search_finds_both_tags():
    assert puzzle_themes.solved_search() == "(tag:lichess::puzzle::result::solved OR tag:lichess::puzzle::solved)"


def test_theme_search():
    assert puzzle_themes.theme_search("fork", False) == "tag:lichess::puzzle::theme::fork"
    assert puzzle_themes.theme_search("fork", True) == "tag:lichess::puzzle::theme::fork tag:lichess::puzzle::result::failed"


def test_primary_theme():
    primary = puzzle_themes.primary_theme
    # A named mate before the tactic, the tactic before a mate in N
    assert primary(["mate", "mateIn2", "backRankMate", "sacrifice"]) == ("mates", "backRankMate")
    assert primary(["mate", "mateIn2", "deflection", "short"]) == ("tactics", "deflection")
    assert primary(["mate", "mateIn3", "long"]) == ("mates", "mateIn3")
    # The most specific tactic: a pin over the hanging piece it wins
    assert primary(["hangingPiece", "pin", "crushing"]) == ("tactics", "pin")
    assert primary(["endgame", "advantage"]) == ("endgames", "endgame")
    assert primary(["rookEndgame", "endgame"]) == ("endgames", "rookEndgame")
    # Phase, goal, length, origin and themes Lichess added later make no deck
    assert primary(["advantage", "middlegame", "short", "master"]) is None
    assert primary(["doubleRookMate"]) is None


def test_every_deck_theme_is_known_and_listed_once():
    keys = [key for _group, group_keys in puzzle_themes.THEME_GROUPS for key in group_keys]
    assert len(keys) == len(set(keys))
    assert set(keys) <= set(puzzle_themes.THEMES)


def test_puzzle_subdeck_in_both_languages():
    from lsi import decks

    i18n.set_language("en")
    assert decks.puzzle_subdeck(["fork", "short"]) == "Tactics::Fork"
    assert decks.puzzle_subdeck(["middlegame"]) == "Other"
    i18n.set_language("pt-BR")
    assert decks.puzzle_subdeck(["rookEndgame", "endgame"]) == "Finais::Final de torres"


def test_when_text_says_today_and_yesterday():
    import time

    from lsi import puzzles

    i18n.set_language("en")
    noon = time.mktime((2026, 11, 27, 12, 29, 0, 0, 0, -1))
    now = noon + 3 * 3600
    assert puzzles.when_text(int(noon * 1000), now) == "today at 12:29"
    assert puzzles.when_text(int((noon - 86400) * 1000), now) == "yesterday at 12:29"
    assert puzzles.when_text(int((noon - 5 * 86400) * 1000), now) == "Nov 22, 2026 12:29"
    i18n.set_language("pt-BR")
    assert puzzles.when_text(int(noon * 1000), now) == "hoje às 12:29"
