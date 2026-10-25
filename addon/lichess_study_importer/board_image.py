"""
The image of a structure note: the board from the side you play, with the annotator's
highlighted squares and arrows, and the structure's name in a band under it. The layout
is the one structures.py places the masks on.
"""

from __future__ import annotations

from aqt.qt import QBuffer, QByteArray, QColor, QFont, QImage, QIODevice, QPainter, QRectF, Qt

from . import structures
from .chess_lib import chess
from .structures import BAND_HEIGHT, BOARD_SIZE, IMAGE_HEIGHT, StructureCard

try:  # Anki ships PyQt6 with the SVG module (aqt.qt doesn't re-export it)
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None


def board_svg(card: StructureCard) -> str:
    board = chess.Board(card.fen)  # python-chess keeps positions without kings
    squares, arrows = card.marks()
    return chess.svg.board(
        board,
        orientation=chess.WHITE if card.side == "w" else chess.BLACK,
        coordinates=True,
        size=BOARD_SIZE,
        colors=structures.COLORS,
        fill={chess.parse_square(sq): color for sq, color in squares.items()},
        arrows=[
            chess.svg.Arrow(chess.parse_square(tail), chess.parse_square(head), color=color)
            for tail, head, color in arrows
        ],
    )


def render_structure_png(card: StructureCard) -> bytes:
    if QSvgRenderer is None:
        raise RuntimeError("PyQt6.QtSvg is not available")
    image = QImage(BOARD_SIZE, IMAGE_HEIGHT, QImage.Format.Format_ARGB32)
    image.fill(QColor(structures.BAND_BACKGROUND))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    QSvgRenderer(QByteArray(board_svg(card).encode("utf-8"))).render(
        painter, QRectF(0, 0, BOARD_SIZE, BOARD_SIZE)
    )

    font = QFont()
    font.setPixelSize(int(BAND_HEIGHT * 0.38))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(structures.BAND_TEXT))
    band = QRectF(12, BOARD_SIZE, BOARD_SIZE - 24, BAND_HEIGHT)
    name = painter.fontMetrics().elidedText(card.name, Qt.TextElideMode.ElideRight, int(band.width()))
    painter.drawText(band, int(Qt.AlignmentFlag.AlignCenter), name)
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)
