"""
Update imported Lichess studies: download again every study already in the collection
(tag lichess::study::<id>) and update the notes whose chapter changed on Lichess, with
their variation and key move cards. Notes keep their note type and deck. New chapters
and chapters removed from Lichess are only reported: some may have been left out on
purpose, so the import window is offered for the new ones.
"""

from __future__ import annotations

import time
from typing import Callable

from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.utils import askUser, showInfo, showWarning, tooltip

from . import anki_ops, decks, expand
from .i18n import tr
from .lichess_api import LichessError, fetch_study_pgn
from .pgn_split import KIND_EMPTY, KIND_STRUCTURE, KIND_UNSUPPORTED, split_games
from .structures import StructureCard
from .ui_common import apply_language, error_text, get_config

REQUEST_PAUSE = 0.3  # seconds between studies, to stay under Lichess' rate limit


def chapter_cards(ch, strip_anno: bool, col=None) -> list:
    """The chapter and the cards that may have been made from it, once each."""
    if ch.kind == KIND_STRUCTURE:
        # An Image Occlusion note, for the side it was imported for
        card = StructureCard(ch, ch.player or ch.side_to_move)
        side = anki_ops.structure_side(col, card) if col is not None else None
        return [StructureCard(ch, side) if side else card]
    cards = {}
    for card in [ch, *expand.split_variations(ch, strip_anno), *expand.key_move_cards(ch, strip_anno)]:
        cards.setdefault(card.dedupe_key, card)
    return list(cards.values())


def update_rows(col, results, strip_anno: bool, report: dict) -> list:
    """Rows for import_chapters: the cards of each study that already have notes."""
    rows = []
    for study_id, value in results:
        if isinstance(value, LichessError):
            report["errors"].append(f"{study_id}: {error_text(value)}")
            continue
        chapters = split_games(value)
        name = next((c.study_name for c in chapters if c.study_name), study_id)
        report["studies"] += 1
        for ch in chapters:
            if ch.kind in (KIND_EMPTY, KIND_UNSUPPORTED):
                continue
            tags = decks.chapter_tags(ch, decks.suggest_kind(ch))
            imported = False
            for card in chapter_cards(ch, strip_anno, col):
                nids = anki_ops.find_existing(col, card)
                if nids:
                    imported = True
                    # Its own note type, so it isn't reported as another one
                    rows.append((card, col.get_note(nids[0]).note_type(), decks.Placement("", tags)))
            if not imported:
                report["new"].setdefault(study_id, (name, []))[1].append(ch.name)
        ids = {c.chapter_id for c in chapters}
        report["removed"] += len(anki_ops.removed_chapter_notes(col, study_id, ids))
    return rows


def update_imported_studies(parent=None, open_studies: Callable[[str], None] | None = None):
    """
    open_studies(links) loads the studies that have new chapters in the import window,
    when the user wants to.
    """
    if not mw.col:
        return
    apply_language()
    parent = parent or mw
    config = get_config()
    ids = [study_id for study_id, _, _ in anki_ops.imported_studies(mw.col)]
    if not ids:
        tooltip(tr("update.none"), parent=parent)
        return
    token = config.get("lichess_token", "")
    strip_anno = bool(config.get("strip_anno", True))

    def progress(done, total):
        mw.taskman.run_on_main(
            lambda: mw.progress.update(label=tr("update.progress", done=done, total=total), value=done, max=total)
        )

    def fetch(col):
        results = []
        for done, study_id in enumerate(ids):
            progress(done, len(ids))
            try:
                results.append((study_id, fetch_study_pgn(study_id, token=token)))
            except LichessError as e:
                results.append((study_id, e))
            time.sleep(REQUEST_PAUSE)
        return results

    QueryOp(
        parent=parent,
        op=fetch,
        success=lambda results: apply_updates(results, strip_anno, parent, open_studies),
    ).failure(lambda e: showWarning(error_text(e), parent=parent)).with_progress(tr("update.progress", done=0, total=len(ids))).without_collection().run_in_background()


def apply_updates(results, strip_anno: bool, parent, open_studies):
    report = {"studies": 0, "errors": [], "new": {}, "removed": 0}
    stats = {}

    def op(col):
        rows = update_rows(col, results, strip_anno, report)
        return anki_ops.import_chapters(
            col, rows, True, strip_anno, stats, tr("update.undo"), move_cards=False
        )

    def on_success(_changes):
        lines = [
            tr(
                "update.summary",
                studies=report["studies"],
                updated=stats.get("updated", 0),
                unchanged=stats.get("unchanged", 0),
            )
        ]
        if report["removed"]:
            lines.append(tr("update.removed", count=report["removed"]))
        if report["errors"]:
            lines.append(tr("study.load_errors", errors="\n".join(report["errors"])))
        new = report["new"]
        if new:
            names = "\n".join(f"• {name}: {len(chapters)}" for name, chapters in new.values())
            lines.append(tr("update.new_chapters", studies=names))
            urls = " ".join(f"https://lichess.org/study/{i}" for i in new)
            if open_studies and askUser("\n\n".join([*lines, tr("update.open_new")]), parent=parent):
                open_studies(urls)
                return
        showInfo("\n\n".join(lines), parent=parent)

    CollectionOp(parent=parent, op=op).success(on_success).run_in_background()
