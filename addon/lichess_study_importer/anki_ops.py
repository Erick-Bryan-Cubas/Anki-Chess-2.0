"""
Anki collection operations: find/clone AnkiChess note types and add notes.
"""

from __future__ import annotations

import html
import json
import re

from anki.collection import AddNoteRequest
from aqt import mw

from .i18n import tr
from .pgn_field import GLUED_BREAK_SEARCH, has_glued_breaks, show_line_breaks, space_line_breaks
from .pgn_split import MODE_FLIPPED, MODE_PUZZLE, MODE_STUDY, Chapter

# Same markers used by the AnkiChess Companion add-on
NOTE_TYPE_TAG = "ankiChessVersion"
CONFIG_RE = re.compile(r"window\.USER_CONFIG\s*=\s*(\{[\s\S]*?\})\s*;")
CONFIG_PLACEHOLDER = "// __USER_CONFIG__"

MODE_SUFFIX = {MODE_FLIPPED: "Flipped", MODE_STUDY: "Study"}
MODE_CONFIG = {
    MODE_FLIPPED: {"flipBoard": True, "playBothSides": False},
    MODE_STUDY: {"flipBoard": False, "playBothSides": True},
}


class ChessImportError(Exception):
    pass


def is_chess_note_type(m: dict) -> bool:
    if NOTE_TYPE_TAG in m:
        return True
    flds = [f["name"] for f in m["flds"]]
    if flds and flds[0].strip().upper() == "PGN":
        return True
    return any("window.USER_CONFIG" in t["qfmt"] for t in m["tmpls"])


def find_chess_note_types() -> list[dict]:
    return [m for m in mw.col.models.all() if is_chess_note_type(m)]


def show_pgn_line_breaks(text: str, card, kind: str) -> str:
    """card_will_show: PGNs pasted in the editor read correctly before being fixed."""
    note = card.note()
    if "PGN" not in note or not has_glued_breaks(note["PGN"]):
        return text
    if not is_chess_note_type(note.note_type()):
        return text
    return show_line_breaks(text, note["PGN"])


def fix_pgn_line_breaks(col) -> int:
    """Space the line breaks of PGNs pasted in the editor, so every device reads them."""
    notes = []
    for nid in col.find_notes(GLUED_BREAK_SEARCH):
        note = col.get_note(nid)
        if is_chess_note_type(note.note_type()):
            note["PGN"] = space_line_breaks(note["PGN"])
            notes.append(note)
    if notes:
        col.update_notes(notes)
    return len(notes)


def mode_note_type_name(base_name: str, mode: str) -> str:
    return base_name if mode == MODE_PUZZLE else f"{base_name} {MODE_SUFFIX[mode]}"


def _set_template_config(qfmt: str, overrides: dict) -> str:
    match = CONFIG_RE.search(qfmt)
    if match:
        try:
            config = json.loads(match.group(1))
        except json.JSONDecodeError:
            config = {}
        config.update(overrides)
        repl = f"window.USER_CONFIG = {json.dumps(config, indent=2)};"
        return qfmt[: match.start()] + repl + qfmt[match.end() :]
    if CONFIG_PLACEHOLDER in qfmt:
        repl = f"window.USER_CONFIG = {json.dumps(overrides, indent=2)};"
        return qfmt.replace(CONFIG_PLACEHOLDER, repl)
    raise ChessImportError(tr("warn.no_user_config"))


def ensure_mode_note_type(base: dict, mode: str) -> dict:
    """Return the note type for a mode, cloning the base one when missing."""
    if mode == MODE_PUZZLE:
        return base
    mm = mw.col.models
    name = mode_note_type_name(base["name"], mode)
    existing = mm.by_name(name)
    if existing:
        return existing

    clone = mm.copy(base, add=False)
    clone["name"] = name
    for tmpl in clone["tmpls"]:
        tmpl["qfmt"] = _set_template_config(tmpl["qfmt"], MODE_CONFIG[mode])
    # Keep the tag so the Companion add-on keeps updating this note type
    clone[NOTE_TYPE_TAG] = base.get(NOTE_TYPE_TAG, "2.0")
    mm.add(clone)
    return mm.by_name(name)


def build_note_fields(ch: Chapter, strip_anno: bool) -> tuple[str, str]:
    # Same format as the Companion example note: escaped text with <br> line breaks.
    # The leading space keeps tags/lines separated once {{text:PGN}} strips the <br>.
    pgn = html.escape(ch.pgn(strip_anno=strip_anno), quote=False).rstrip("\n")
    pgn_field = pgn.replace("\n", " <br>")

    parts = [f"<h3>{html.escape(ch.name)}</h3>"]
    if ch.study_name:
        parts.append(html.escape(ch.study_name))
    if ch.chapter_url:
        parts.append(f'<a href="{html.escape(ch.chapter_url)}">{html.escape(ch.link_label)}</a>')
    return pgn_field, "<br>".join(parts)


def _find_existing(col, ch: Chapter) -> list[int]:
    if not ch.dedupe_key:
        return []
    return list(col.find_notes(f'"PGN:*{ch.dedupe_key}*"'))


def import_chapters(
    col, rows, update_existing: bool, strip_anno: bool, stats: dict, undo_label: str = ""
):
    """
    rows: list of (card, note type dict, decks.Placement), where a card is a
    pgn_split.Chapter or a game_analysis.GameCard. Runs inside a CollectionOp;
    `stats` is filled with created/updated/skipped counts.

    Updating also moves the note's cards to the card's deck, so re-importing with
    "update" reorganises older imports into the current deck layout.
    """
    undo_pos = col.add_custom_undo_entry(undo_label or tr("undo.import"))
    deck_ids: dict[str, int] = {}

    def deck_id(name: str) -> int:
        if name not in deck_ids:
            deck_ids[name] = col.decks.id(name)
        return deck_ids[name]

    to_add, to_update = [], []
    moves: dict[int, list[int]] = {}  # deck id -> card ids
    for ch, model, placement in rows:
        pgn_field, text_field = build_note_fields(ch, strip_anno)
        tags = [*ch.note_tags, *placement.tags]

        existing = _find_existing(col, ch)
        if existing:
            if not update_existing:
                stats["skipped"] += 1
                continue
            for nid in existing:
                note = col.get_note(nid)
                note.fields[0] = pgn_field
                if len(note.fields) > 1:
                    note.fields[1] = text_field
                for t in tags:
                    note.add_tag(t)
                to_update.append(note)
                moves.setdefault(deck_id(placement.deck), []).extend(note.card_ids())
            stats["updated"] += 1
            continue

        note = col.new_note(model)
        note.fields[0] = pgn_field
        if len(note.fields) > 1:
            note.fields[1] = text_field
        note.tags = tags
        to_add.append(AddNoteRequest(note=note, deck_id=deck_id(placement.deck)))
        stats["created"] += 1

    # Batched, so the import is a few undo steps: one per note would push the
    # custom entry out of Anki's undo queue on large imports
    if to_update:
        col.update_notes(to_update)
        for did, card_ids in moves.items():
            col.set_deck(card_ids, did)
    if to_add:
        col.add_notes(to_add)
    return col.merge_undo_entries(undo_pos)
