"""
A preview of the AnkiChess template: the improvements proposed to the AnkiChess project
(github.com/TowelSniffer/Anki-Chess-2.0) and not released there yet, shipped in this add-on
so trying them takes only installing it.

The build puts the template's script in preview/, named after the official version it
builds on and when it was built: _ankiChess1.3.00-preview-20261030153000.js (a new name
each build, so AnkiDroid doesn't keep a cached copy). anki_ops.apply_template_preview
writes it into the media folder and points the AnkiChess note types at it, changing only
their <script src>: their HTML, styling and settings stay.

- The Companion add-on leaves that name alone: it replaces _ankiChess<version>.js files.
- Only note types on the official version the preview builds on take it. Once the
  Companion installs a newer official version, that one is kept: the improvements are in
  it, or a newer preview follows.
- Turned off (preview_template in the config), note types go back to the official script.
- The Companion's Manage chessRs Notes runs the template's script too: it gets the preview,
  so the settings it shows and saves for each note type include the preview's (hints,
  refutation, answer button...).

Pure Python (no aqt imports) so the build script and the tests can use it.
"""

from __future__ import annotations

import os
import re
from typing import Callable

PREVIEW_DIR = os.path.join(os.path.dirname(__file__), "preview")
SCRIPT_RE = re.compile(r"""(src=["'](?:\./)?)(_ankiChess[^"'/]*\.js)(["'])""")
OFFICIAL_RE = re.compile(r"_ankiChess(\d+(?:\.\d+)+)\.js$")
PREVIEW_RE = re.compile(r"_ankiChess(\d+(?:\.\d+)+)-preview-(\d+)\.js$")


def preview_name(version: str, build: str) -> str:
    """The preview script's name: the official version it builds on, and its build time."""
    return f"_ankiChess{version}-preview-{build}.js"


def bundled() -> str | None:
    """The preview script shipped in the add-on (none in a source checkout)."""
    try:
        names = os.listdir(PREVIEW_DIR)
    except OSError:
        return None
    return max((n for n in names if PREVIEW_RE.match(n)), key=preview_key, default=None)


def preview_key(name: str) -> tuple:
    """Previews in order: the official version they build on, then their build."""
    match = PREVIEW_RE.match(name)
    return (tuple(int(n) for n in match.group(1).split(".")), int(match.group(2)))


def script_of(html: str) -> str | None:
    """The AnkiChess script a template loads."""
    match = SCRIPT_RE.search(html)
    return match.group(2) if match else None


def with_script(html: str, name: str) -> str:
    return SCRIPT_RE.sub(lambda m: m.group(1) + name + m.group(3), html, count=1)


def official_of(name: str) -> str:
    """The official script a preview builds on."""
    return f"_ankiChess{PREVIEW_RE.match(name).group(1)}.js"


def target(current: str, preview: str | None, in_media: Callable[[str], bool]) -> str:
    """
    The script for a note type loading `current`. With the preview on: the preview, for the
    official version it builds on or an older preview. Off (preview None): a preview goes
    back to the official script it builds on, when that is in the media folder.
    """
    official = OFFICIAL_RE.match(current)
    if preview:
        base = PREVIEW_RE.match(preview).group(1)
        if official and official.group(1) == base:
            return preview
        if PREVIEW_RE.match(current) and preview_key(current) < preview_key(preview):
            return preview
        # A newer official version, or a newer preview synced from another device
        return current
    if PREVIEW_RE.match(current) and in_media(official_of(current)):
        return official_of(current)
    return current


# The Companion's pages that run the template's script: Manage chessRs Notes and its help
COMPANION_PAGE_RE = re.compile(r"""data-mode=["']addon-(?:settings|about)["']""")
QUOTED_OFFICIAL_RE = re.compile(r"""(["'])(_ankiChess(\d+(?:\.\d+)+)\.js)\1""")


def companion_page(body: str, preview: str | None) -> str:
    """
    A Companion page (Manage chessRs Notes, its help) loading the preview instead of the
    official script it builds on, so it shows and saves the preview's settings too.
    """
    if not preview or not COMPANION_PAGE_RE.search(body):
        return body
    base = PREVIEW_RE.match(preview).group(1)

    def swap(match: re.Match) -> str:
        quote = match.group(1)
        return f"{quote}{preview}{quote}" if match.group(3) == base else match.group(0)

    return QUOTED_OFFICIAL_RE.sub(swap, body)
