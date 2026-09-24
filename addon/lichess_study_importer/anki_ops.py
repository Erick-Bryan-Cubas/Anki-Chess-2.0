"""
Anki collection operations: find/clone AnkiChess note types and add notes.
"""

from __future__ import annotations

import html
import json
import re

from aqt import mw

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
    raise ChessImportError("O template não tem bloco window.USER_CONFIG para configurar o modo.")


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
        parts.append(f'<a href="{html.escape(ch.chapter_url)}">Lichess</a>')
    return pgn_field, "<br>".join(parts)


def _find_existing(col, ch: Chapter) -> list[int]:
    if not (ch.study_id and ch.chapter_id):
        return []
    return list(col.find_notes(f'"PGN:*study/{ch.study_id}/{ch.chapter_id}*"'))


def import_chapters(col, rows, deck_name: str, update_existing: bool, strip_anno: bool, stats: dict):
    """
    rows: list of (Chapter, note type dict). Runs inside a CollectionOp; `stats`
    is filled with created/updated/skipped counts.
    """
    undo_pos = col.add_custom_undo_entry("Importar estudo do Lichess")
    deck_id = col.decks.id(deck_name)

    for ch, model in rows:
        pgn_field, text_field = build_note_fields(ch, strip_anno)
        tags = ["lichess", f"lichess::{ch.kind}"]
        if ch.study_id:
            tags.append(f"lichess::study::{ch.study_id}")

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
                col.update_note(note)
            stats["updated"] += 1
            continue

        note = col.new_note(model)
        note.fields[0] = pgn_field
        if len(note.fields) > 1:
            note.fields[1] = text_field
        note.tags = tags
        col.add_note(note, deck_id)
        stats["created"] += 1

    return col.merge_undo_entries(undo_pos)
