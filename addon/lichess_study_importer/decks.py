"""
Where each imported card goes: deck and extra tags.

    <root>::Openings::<family>          opening lines, book moves, book lines
                                        (+ tag <opening>::<family>::<variation>)
    <root>::Tactics::<study>            Lichess chapters starting from a FEN
    <root>::Annotated games::<study>    Lichess full games
    <root>::My games::<error type>      Chess.com errors and missed mates

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from .chess_lib import chess
from .i18n import tr
from .openings import follow_book, load_book
from .pgn_split import KIND_EXERCISE, KIND_GAME, KIND_LINE, Chapter

OPENING_KINDS = ("opening", "book", "book_line")  # game_analysis kinds filed by opening


@dataclass
class Placement:
    deck: str
    tags: list[str] = field(default_factory=list)


def root_name(configured: str | None) -> str:
    """Configured root deck, or the default for the interface language."""
    return deck_part(configured or "") or tr("deck.root")


def deck_part(text: str) -> str:
    """One level of a deck name: '::' would create an extra level."""
    return re.sub(r"\s*::\s*", ": ", text or "").strip(" :")


def tag_part(text: str) -> str:
    """One level of a hierarchical tag: no spaces or punctuation, lowercase."""
    return re.sub(r"[^\w-]+", "_", text or "").strip("_").lower()


def split_opening(name: str | None) -> tuple[str | None, str | None]:
    """'Slav Defense: Czech Variation, Carlsbad Variation' -> ('Slav Defense', 'Czech Variation')."""
    if not name:
        return None, None
    family, _, rest = name.partition(": ")
    variation = rest.split(", ")[0].strip() or None
    return family.strip() or None, variation


def opening_placement(root: str, opening: str | None) -> Placement:
    family, variation = split_opening(opening)
    deck = f"{root}::{tr('deck.openings')}::{deck_part(family) if family else tr('deck.other_openings')}"
    tags = []
    if family:
        tag = f"{tr('tag.opening')}::{tag_part(family)}"
        if variation:
            tag += f"::{tag_part(variation)}"
        tags.append(tag)
    return Placement(deck, tags)


def chapter_opening(ch: Chapter) -> str | None:
    """Catalog name of the deepest book position reached by a chapter's main line."""
    try:
        game = chess.pgn.read_game(io.StringIO(ch.pgn()))
    except (ValueError, KeyError):
        return None
    if game is None:
        return None
    return follow_book(game.board(), list(game.mainline_moves())).opening_name


def suggest_kind(ch: Chapter) -> str:
    """Chapter kind, with chapters starting from a book position treated as opening lines."""
    if ch.kind == KIND_EXERCISE:
        try:
            board = chess.Board(ch.fen)
        except ValueError:
            return ch.kind
        if board.epd() in load_book():
            return KIND_LINE
    return ch.kind


def place_chapter(ch: Chapter, root: str, kind: str | None = None, opening: str | None = None) -> Placement:
    """kind overrides the suggested chapter kind; opening avoids parsing the chapter again."""
    kind = kind or suggest_kind(ch)
    if kind == KIND_LINE:
        return opening_placement(root, opening if opening is not None else chapter_opening(ch))
    study = deck_part(ch.study_name) or tr("deck.unnamed_study")
    section = tr("deck.games") if kind == KIND_GAME else tr("deck.tactics")
    return Placement(f"{root}::{section}::{study}")


def place_game_card(card, root: str) -> Placement:
    """Placement for a game_analysis.GameCard."""
    if card.kind in OPENING_KINDS:
        return opening_placement(root, card.opening)
    return Placement(f"{root}::{tr('deck.my_games')}::{tr(f'deck.kind.{card.kind}')}")
