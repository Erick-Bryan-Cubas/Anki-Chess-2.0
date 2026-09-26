"""
Split a Lichess study PGN export into chapters and classify them.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TAG_RE = re.compile(r'^\s*\[(\w+)\s+"((?:[^"\\]|\\.)*)"\]\s*$')
COMMENT_RE = re.compile(r"\{[^}]*\}")
CHAPTER_URL_RE = re.compile(r"/study/([A-Za-z0-9]{8})/([A-Za-z0-9]{8})")
ANNO_RE = re.compile(r"\[%anno\b[^\]]*\]")
EMPTY_COMMENT_RE = re.compile(r"\{\s*\}")
# Embedded comment commands ([%cal ...]); the template parser only accepts "[%name value]"
COMMAND_RE = re.compile(r"\[%[^\]]*\]")
VALID_COMMAND_RE = re.compile(r"\[%\s*[\w.-]+\s+[^\]\s][^\]]*\]")
# A SAN move (or castling), used to decide if a chapter has any moves at all.
SAN_RE = re.compile(r"(?<![\w-])(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?)[+#]?")
# First move of the movetext, with the (optional) leading and trailing comments.
FIRST_MOVE_RE = re.compile(
    r"^\s*(?P<lead>(?:\{[^}]*\}\s*)*)"
    r"(?:\d+\.(?:\.\.)?\s*)?"
    r"(?P<move>\S+)\s*"
    r"(?P<after>\{[^}]*\})?"
)
# "Jogam as brancas", "qual o melhor lance para as pretas?", "White to move"...
SIDE_HINT_RE = re.compile(
    r"(?:jog\w*|jueg\w*|mueve\w*|lance|jugada|play\w*|move)\W+(?:\w+\W+){0,3}?"
    r"(?P<a>brancas|pretas|blancas|negras|white|black)"
    r"|(?P<b>white|black)\s+to\s+(?:play|move)",
    re.IGNORECASE,
)
COLOR_WORDS = {
    "brancas": "w",
    "blancas": "w",
    "white": "w",
    "pretas": "b",
    "negras": "b",
    "black": "b",
}

KIND_EXERCISE = "exercise"
KIND_GAME = "game"
KIND_EMPTY = "empty"

MODE_PUZZLE = "puzzle"
MODE_FLIPPED = "flipped"
MODE_STUDY = "study"


@dataclass
class Chapter:
    tags: dict[str, str] = field(default_factory=dict)
    movetext: str = ""

    @property
    def name(self) -> str:
        return self.tags.get("ChapterName") or self.tags.get("Event") or "?"

    @property
    def study_name(self) -> str:
        return self.tags.get("StudyName", "")

    @property
    def chapter_url(self) -> str:
        return self.tags.get("ChapterURL", "")

    @property
    def study_id(self) -> str | None:
        m = CHAPTER_URL_RE.search(self.chapter_url)
        return m.group(1) if m else None

    @property
    def chapter_id(self) -> str | None:
        m = CHAPTER_URL_RE.search(self.chapter_url)
        return m.group(2) if m else None

    @property
    def fen(self) -> str | None:
        return self.tags.get("FEN")

    @property
    def side_to_move(self) -> str:
        parts = (self.fen or "").split()
        return parts[1] if len(parts) > 1 and parts[1] in ("w", "b") else "w"

    @property
    def kind(self) -> str:
        if not has_moves(self.movetext):
            return KIND_EMPTY
        return KIND_EXERCISE if self.fen else KIND_GAME

    @property
    def suggested_mode(self) -> str:
        kind = self.kind
        if kind == KIND_GAME:
            return MODE_STUDY
        if kind == KIND_EMPTY:
            return MODE_PUZZLE
        return suggest_exercise_mode(self)

    @property
    def preview(self) -> str:
        text = " ".join(COMMENT_RE.sub(" ", self.movetext).split())
        return text[:60] + ("…" if len(text) > 60 else "")

    def pgn(self, strip_anno: bool = True) -> str:
        header = "\n".join(f'[{k} "{escape_tag_value(v)}"]' for k, v in self.tags.items())
        body = drop_malformed_commands(self.movetext)
        body = sanitize(body) if strip_anno else body.strip()
        return f"{header}\n\n{body}\n"


# PGN tag values escape quotes and backslashes: [ChapterName "\"Intro\" - Foreword"]
def unescape_tag_value(value: str) -> str:
    return re.sub(r'\\(["\\])', r"\1", value)


def escape_tag_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def drop_malformed_commands(movetext: str) -> str:
    """
    Remove comment commands the template's PGN parser rejects (e.g. a "[%t@Shrt]"
    typo in a study), which would otherwise make the whole chapter fail to load.
    """
    return COMMAND_RE.sub(
        lambda m: m.group(0) if VALID_COMMAND_RE.fullmatch(m.group(0)) else "", movetext
    )


def has_moves(movetext: str) -> bool:
    return bool(SAN_RE.search(COMMENT_RE.sub(" ", movetext)))


def sanitize(movetext: str) -> str:
    """Remove Lichess annotator markers ([%anno ...]) and comments left empty."""
    text = ANNO_RE.sub("", movetext)
    text = EMPTY_COMMENT_RE.sub("", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _hinted_color(comment: str | None) -> str | None:
    if not comment:
        return None
    m = SIDE_HINT_RE.search(comment)
    if not m:
        return None
    return COLOR_WORDS[(m.group("a") or m.group("b")).lower()]


def suggest_exercise_mode(ch: Chapter) -> str:
    """
    Guess if the solver plays the side to move (puzzle) or the other side,
    with the first move being the opponent's set-up move (flipped).
    """
    stm = ch.side_to_move
    m = FIRST_MOVE_RE.match(ch.movetext)
    if m:
        # A hint right after the first move names the solver ("Jogam as brancas").
        after = _hinted_color(m.group("after"))
        if after:
            return MODE_PUZZLE if after == stm else MODE_FLIPPED
        # A hint before the first move is a question to the side to move.
        lead = _hinted_color(m.group("lead"))
        if lead:
            return MODE_PUZZLE if lead == stm else MODE_FLIPPED

    # Otherwise, the winner of a decisive result is usually the solver.
    winner = {"1-0": "w", "0-1": "b"}.get(ch.tags.get("Result", ""))
    if winner and winner != stm:
        return MODE_FLIPPED
    return MODE_PUZZLE


def split_games(text: str) -> list[Chapter]:
    """Split a multi-game PGN into chapters. Duplicate tags keep the first value."""
    chapters: list[Chapter] = []
    current: Chapter | None = None
    in_moves = False
    brace_depth = 0
    move_lines: list[str] = []

    def flush():
        if current is not None:
            current.movetext = "\n".join(move_lines).strip()
            chapters.append(current)

    for line in text.replace("\r\n", "\n").lstrip("﻿").split("\n"):
        tag = TAG_RE.match(line) if brace_depth == 0 else None
        if tag:
            if current is None or in_moves:
                flush()
                current = Chapter()
                move_lines = []
                in_moves = False
            current.tags.setdefault(tag.group(1), unescape_tag_value(tag.group(2)))
            continue

        if current is None:
            if not line.strip():
                continue
            current = Chapter()  # movetext with no header
            move_lines = []
        if line.strip():
            in_moves = True
        if in_moves:
            move_lines.append(line)
            brace_depth = max(0, brace_depth + line.count("{") - line.count("}"))

    flush()
    return chapters
