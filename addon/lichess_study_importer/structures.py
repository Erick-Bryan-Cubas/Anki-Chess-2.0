"""
Structure chapters (a [FEN] with no moves, often only pawns) as Image Occlusion notes.

The image is the board, from the side you play, with the structure's name in a band
under it. Its masks make three cards:
  c1  your pieces hidden (everything but the opponent's pieces is masked): rebuild yours
  c2  the opponent's pieces hidden: rebuild theirs
  c3  the name band hidden: which structure is this?
Masks cover every square that isn't shown, not only the hidden pieces, so their shape
doesn't give the answer away. No mask has oi=1 ("hide one, guess one"): the masks of the
other cards stay visible.

Pure Python (no aqt imports) so it can be unit tested outside Anki; the image is drawn
by board_image.py.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass

from .pgn_split import ID_TAG, Chapter

# Image layout, in pixels: the board (python-chess SVG with coordinates), then the band
BOARD_SIZE = 600
BAND_HEIGHT = 72
IMAGE_HEIGHT = BOARD_SIZE + BAND_HEIGHT
# python-chess draws a 15 unit margin (the coordinates) around 8 squares of 45 units
SVG_UNITS = 390
MARGIN = 15 / SVG_UNITS * BOARD_SIZE
SQUARE = 45 / SVG_UNITS * BOARD_SIZE
# Changing the drawing changes every image name, so updated notes get the new image
RENDER_VERSION = 1
# AnkiChess "wood" board theme (src/utils/themeData.ts)
COLORS = {
    "square light": "#f0d9b5",
    "square dark": "#b58863",
    "margin": "#2c2c2c",
    "coord": "#d7dee9",
}
BAND_BACKGROUND = "#2c2c2c"
BAND_TEXT = "#d7dee9"
# Lichess brushes of [%csl] (square colours, with alpha) and [%cal] (python-chess arrow names)
BRUSHES = {"G": "#15781b99", "R": "#88202099", "B": "#00308899", "Y": "#e68f0099"}
ARROW_COLORS = {"G": "green", "R": "red", "B": "blue", "Y": "yellow"}
CSL_RE = re.compile(r"\[%csl\s+([^\]]*)\]")
CAL_RE = re.compile(r"\[%cal\s+([^\]]*)\]")
SIDE_RE = re.compile(r'\[Side "([wb])"\]')  # in the Comments field, see StructureCard.comments
SQUARE_RE = re.compile(r"^([GRBY])([a-h][1-8])$")
ARROW_RE = re.compile(r"^([GRBY])([a-h][1-8])([a-h][1-8])$")
FILES = "abcdefgh"


def placement(fen: str) -> dict[str, str]:
    """Pieces by square ("e4": "P"), from the first field of a FEN."""
    pieces = {}
    rows = (fen.split() or [""])[0].split("/")
    for row_index, row in enumerate(rows[:8]):
        file = 0
        for char in row:
            if char.isdigit():
                file += int(char)
            elif file < 8:
                pieces[f"{FILES[file]}{8 - row_index}"] = char
                file += 1
    return pieces


def stored_side(comments: str) -> str | None:
    """The side a structure note was imported for, from its Comments field."""
    m = SIDE_RE.search(comments)
    return m.group(1) if m else None


def display_square(col: int, row: int, side: str) -> str:
    """Square at a display column/row (0 = left/top) of a board seen from `side`."""
    if side == "b":
        return f"{FILES[7 - col]}{row + 1}"
    return f"{FILES[col]}{8 - row}"


@dataclass
class StructureCard:
    chapter: Chapter
    side: str  # "w"/"b": the side you play, shown at the bottom and rebuilt on card 1

    link_label = "Lichess"
    is_structure = True

    @property
    def dedupe_key(self) -> str | None:
        return self.chapter.dedupe_key

    @property
    def name(self) -> str:
        return self.chapter.name

    @property
    def study_name(self) -> str:
        return self.chapter.study_name

    @property
    def chapter_url(self) -> str:
        return self.chapter.chapter_url

    @property
    def note_tags(self) -> list[str]:
        return self.chapter.note_tags

    @property
    def fen(self) -> str:
        return self.chapter.fen or ""

    # --- Masks ---

    def masks(self, recall: str) -> list[tuple[float, float, float, float]]:
        """
        (left, top, width, height), as fractions of the image, covering every square
        except the pieces of the side not recalled. Free squares are merged into runs
        per row, and identical runs of consecutive rows into one rectangle.
        """
        pieces = placement(self.fen)
        runs: list[tuple[int, int, int, int]] = []  # first col, last col, first row, last row
        for row in range(8):
            col = 0
            while col < 8:
                piece = pieces.get(display_square(col, row, self.side))
                shown = piece is not None and (piece.isupper() != (recall == "w"))
                if shown:
                    col += 1
                    continue
                start = col
                while col < 8:
                    piece = pieces.get(display_square(col, row, self.side))
                    if piece is not None and (piece.isupper() != (recall == "w")):
                        break
                    col += 1
                above = next((r for r in runs if r[:2] == (start, col - 1) and r[3] == row - 1), None)
                if above:
                    runs[runs.index(above)] = (start, col - 1, above[2], row)
                else:
                    runs.append((start, col - 1, row, row))
        return [
            (
                (MARGIN + first * SQUARE) / BOARD_SIZE,
                (MARGIN + top * SQUARE) / IMAGE_HEIGHT,
                (last - first + 1) * SQUARE / BOARD_SIZE,
                (bottom - top + 1) * SQUARE / IMAGE_HEIGHT,
            )
            for first, last, top, bottom in runs
        ]

    @staticmethod
    def band_mask() -> tuple[float, float, float, float]:
        return (0.0, BOARD_SIZE / IMAGE_HEIGHT, 1.0, BAND_HEIGHT / IMAGE_HEIGHT)

    def occlusions(self) -> str:
        """The Occlusion field: c1 your pieces, c2 the opponent's, c3 the name."""
        other = "b" if self.side == "w" else "w"
        groups = [self.masks(self.side), self.masks(other), [self.band_mask()]]
        return "".join(
            f"{{{{c{ordinal}::image-occlusion:rect:left={left:.4f}:top={top:.4f}"
            f":width={width:.4f}:height={height:.4f}}}}}"
            for ordinal, rects in enumerate(groups, start=1)
            for left, top, width, height in rects
        )

    # --- Fields ---

    def header(self) -> str:
        """Shown above the image of every card: not the name, card 3 asks for it."""
        return html.escape(self.study_name)

    def back_extra(self) -> str:
        """The plans the annotator wrote, and the link to the chapter."""
        parts = []
        if self.chapter.comment_text:
            parts.append(html.escape(self.chapter.comment_text).replace("\n", "<br>"))
        if self.chapter_url:
            parts.append(f'<a href="{html.escape(self.chapter_url)}">{self.link_label}</a>')
        return "<br><br>".join(parts)

    def comments(self) -> str:
        """
        Not shown on the cards: identifies the note when the study is imported again,
        and keeps the side chosen for it.
        """
        side = f'[Side "{self.side}"]'
        return f'[{ID_TAG} "{self.dedupe_key}"] {side}' if self.dedupe_key else side

    def image_name(self) -> str:
        identity = "\n".join(
            [str(RENDER_VERSION), self.fen, self.side, self.name, *self.chapter.commands]
        )
        return f"ankichess-structure-{hashlib.sha1(identity.encode()).hexdigest()[:12]}.png"

    def fields(self) -> list[str]:
        """Occlusion, Image, Header, Back Extra, Comments: the stock IO note type's order."""
        return [
            self.occlusions(),
            f'<img src="{self.image_name()}">',
            self.header(),
            self.back_extra(),
            self.comments(),
        ]

    # --- Marks of the annotator, drawn on the board ---

    def marks(self) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
        """Highlighted squares {square: colour} and arrows [(tail, head, colour)]."""
        squares: dict[str, str] = {}
        arrows: list[tuple[str, str, str]] = []
        for command in self.chapter.commands:
            for m in CSL_RE.finditer(command):
                for item in m.group(1).split(","):
                    sq = SQUARE_RE.match(item.strip())
                    if sq:
                        squares[sq.group(2)] = BRUSHES[sq.group(1)]
            for m in CAL_RE.finditer(command):
                for item in m.group(1).split(","):
                    arrow = ARROW_RE.match(item.strip())
                    if arrow:
                        arrows.append((arrow.group(2), arrow.group(3), ARROW_COLORS[arrow.group(1)]))
        return squares, arrows
