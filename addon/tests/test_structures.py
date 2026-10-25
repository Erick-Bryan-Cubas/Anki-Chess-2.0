import os
import re
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

from lsi import decks, i18n  # noqa: E402
from lsi.pgn_split import (  # noqa: E402
    KIND_EMPTY,
    KIND_EXERCISE,
    KIND_LINE,
    KIND_STRUCTURE,
    Chapter,
    split_games,
)
from lsi.structures import (  # noqa: E402
    BOARD_SIZE,
    IMAGE_HEIGHT,
    MARGIN,
    SQUARE,
    StructureCard,
    display_square,
    placement,
    stored_side,
)

# Chapters of https://lichess.org/study/w7B3QmIi (Siciliana O'Kelly)
with open(os.path.join(HERE, "fixtures", "okelly_structures.pgn"), encoding="utf-8") as f:
    CHAPTERS = {ch.name: ch for ch in split_games(f.read())}

NAJDORF = CHAPTERS["Estrutura I (Najdorf)"]
HEDGEHOG = CHAPTERS["Estrutura IV (Porco-espinho)"]
SHAPE_RE = re.compile(
    r"\{\{c(\d+)::image-occlusion:rect:left=([\d.]+):top=([\d.]+):width=([\d.]+):height=([\d.]+)\}\}"
)


@pytest.fixture(autouse=True)
def portuguese():
    i18n.set_language("pt-BR")
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


def masked(rects, col: int, row: int) -> bool:
    """Whether the centre of a displayed square is under one of the rectangles."""
    x = (MARGIN + (col + 0.5) * SQUARE) / BOARD_SIZE
    y = (MARGIN + (row + 0.5) * SQUARE) / IMAGE_HEIGHT
    return any(left <= x <= left + width and top <= y <= top + height for left, top, width, height in rects)


# --- Classification ---


def test_a_fen_with_no_moves_is_a_structure():
    kinds = {name: ch.kind for name, ch in CHAPTERS.items()}
    assert kinds == {
        "Introdução": KIND_LINE,
        "Estrutura I (Najdorf)": KIND_STRUCTURE,
        "Estrutura III (PDI/Alapin)": KIND_STRUCTURE,  # no comment: no plans, still a structure
        "Estrutura IV (Porco-espinho)": KIND_STRUCTURE,  # pieces too
        "Estrutura V (Botvinnik)": KIND_STRUCTURE,  # a gamebook chapter, with a game's tags
        "Exercício - avanço e5": KIND_EXERCISE,
    }
    assert Chapter(tags={}, movetext="{ Pratique mais nos links }").kind == KIND_EMPTY  # no FEN


def test_structure_side_and_key():
    assert NAJDORF.player == "b"  # [Orientation "black"]
    assert NAJDORF.dedupe_key == "study/w7B3QmIi/3CY8U1bO"
    # From a file, without a chapter URL: keyed by its position
    ch = Chapter(tags={"FEN": "8/1p3ppp/p2p4/4p3/4P3/8/PPP2PPP/8 w - - 0 1"}, movetext="*")
    assert ch.dedupe_key.startswith("pgn/")


def test_comment_text_keeps_the_plans_without_commands():
    text = NAJDORF.comment_text
    assert text.startswith("Nessa estrutura, todos os planos")
    assert "Plano das brancas:\n1. Colocar um cavalo em d5" in text
    assert "\n\nPlano das pretas:\n1. Quebra o centro" in text
    assert CHAPTERS["Estrutura III (PDI/Alapin)"].comment_text == ""

    ch = Chapter(tags={"FEN": "8/8/8/8/8/8/8/8 w - - 0 1"}, movetext='{ [%anno "basso01", basso01] [%csl Gd5][%cal Gb7b5] Plano:\n1. b5 }\n *')
    assert ch.comment_text == "Plano:\n1. b5"
    assert StructureCard(ch, "b").marks() == ({"d5": "#15781b99"}, [("b7", "b5", "green")])


# --- Masks ---


@pytest.mark.parametrize("side", ["w", "b"])
@pytest.mark.parametrize("ch", [NAJDORF, HEDGEHOG], ids=["najdorf", "hedgehog"])
def test_masks_cover_every_square_but_the_pieces_shown(ch, side):
    card = StructureCard(ch, side)
    pieces = placement(card.fen)
    for recall in ("w", "b"):
        rects = card.masks(recall)
        assert len(rects) <= 16  # runs merged, not one mask per square
        for row in range(8):
            for col in range(8):
                piece = pieces.get(display_square(col, row, side))
                shown = piece is not None and piece.isupper() != (recall == "w")
                assert masked(rects, col, row) != shown, (recall, display_square(col, row, side))


def test_your_side_is_at_the_bottom():
    assert display_square(0, 7, "w") == "a1"
    assert display_square(0, 7, "b") == "h8"
    assert display_square(0, 0, "b") == "h1"


def test_occlusions_make_three_cards_hiding_one_at_a_time():
    card = StructureCard(NAJDORF, "b")
    field = card.occlusions()
    shapes = SHAPE_RE.findall(field)
    assert "".join(f"{{{{c{s[0]}::image-occlusion:rect:left={s[1]}:top={s[2]}:width={s[3]}:height={s[4]}}}}}" for s in shapes) == field
    assert "oi=" not in field  # hide one, guess one: the other cards' masks stay visible
    by_card = {}
    for ordinal, *values in shapes:
        by_card.setdefault(int(ordinal), []).append(tuple(float(v) for v in values))
        assert all(0 <= float(v) <= 1 for v in values)
    assert sorted(by_card) == [1, 2, 3]
    # c1 hides your (black) pawns, c2 the white ones, c3 the name band under the board
    assert display_square(1, 6, "b") == "g7" and display_square(3, 3, "b") == "e4"
    assert masked(by_card[1], 1, 6) and not masked(by_card[2], 1, 6)  # g7: a black pawn
    assert masked(by_card[2], 3, 3) and not masked(by_card[1], 3, 3)  # e4: the white one
    assert by_card[3] == [(0.0, round(BOARD_SIZE / IMAGE_HEIGHT, 4), 1.0, round(1 - BOARD_SIZE / IMAGE_HEIGHT, 4))]


def test_the_hedgehog_card_hides_your_pieces_too():
    card = StructureCard(HEDGEHOG, "b")
    # Black king on g8: row 7 (bottom), col 1 from Black's side
    assert display_square(1, 7, "b") == "g8"
    assert masked(card.masks("b"), 1, 7) and not masked(card.masks("w"), 1, 7)


# --- Fields ---


def test_fields_of_the_note():
    card = StructureCard(NAJDORF, "b")
    occlusion, image, header, back, comments = card.fields()
    assert re.fullmatch(r'<img src="ankichess-structure-[0-9a-f]{12}\.png">', image)
    # The header is on every card: the study, not the structure's name (card 3 asks it)
    assert header == "QUICKSTART - Siciliana O&#x27;kelly"
    assert "Estrutura I" not in header
    assert back.startswith("Nessa estrutura, todos os planos")
    assert "<br>Plano das brancas:<br>1. Colocar" in back
    assert back.endswith('<a href="https://lichess.org/study/w7B3QmIi/3CY8U1bO">Lichess</a>')
    assert comments == '[AnkiChessId "study/w7B3QmIi/3CY8U1bO"] [Side "b"]'
    assert stored_side(comments) == "b"
    assert occlusion == card.occlusions()


def test_image_name_follows_what_is_drawn():
    name = StructureCard(NAJDORF, "b").image_name()
    assert StructureCard(NAJDORF, "b").image_name() == name  # stable
    assert StructureCard(NAJDORF, "w").image_name() != name  # other side, other image
    assert StructureCard(HEDGEHOG, "b").image_name() != name


def test_structures_go_to_their_own_subdeck():
    place = decks.place_chapter(NAJDORF, "Xadrez", kind=KIND_STRUCTURE)
    assert place.deck == "Xadrez::QUICKSTART - Siciliana O'kelly::Estruturas"
    assert "estudo::QUICKSTART_-_Siciliana_O'kelly::Estrutura_I_(Najdorf)" in place.tags
    assert StructureCard(NAJDORF, "b").note_tags[:2] == ["lichess", "lichess::structure"]
