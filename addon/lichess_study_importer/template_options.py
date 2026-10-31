"""
The card's helps, on or off for each AnkiChess note type: hints while solving, the refutation
of a wrong move, and the answer button suggested on the back (features of the template preview
this add-on ships). Like the template's other settings they live in each card template's
window.USER_CONFIG, so they sync to AnkiDroid with the note type.

Pure Python (no aqt imports) so the tests can use it.
"""

from __future__ import annotations

import json
import re

# Same markers used by the AnkiChess Companion add-on
CONFIG_RE = re.compile(r"window\.USER_CONFIG\s*=\s*(\{[\s\S]*?\})\s*;")
CONFIG_PLACEHOLDER = "// __USER_CONFIG__"

GRADE_MODES = ("off", "suggest", "answer")
EASY_TIME_MAX = 120

# The helps, with the template's defaults (default_config.json) for a template without them
DEFAULTS = {"hints": True, "refutation": True, "autoGrade": "suggest", "easyTime": 0}


def read_config(qfmt: str) -> dict | None:
    """The template's settings: {} for an unfilled placeholder, None without (readable) ones."""
    match = CONFIG_RE.search(qfmt)
    if not match:
        return {} if CONFIG_PLACEHOLDER in qfmt else None
    try:
        config = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return config if isinstance(config, dict) else None


def write_config(qfmt: str, overrides: dict) -> str | None:
    """The template with these settings changed and its others kept (None: it has no settings)."""
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
        return qfmt.replace(CONFIG_PLACEHOLDER, f"window.USER_CONFIG = {json.dumps(overrides, indent=2)};")
    return None


def options_of(qfmt: str) -> dict | None:
    """The helps a template has, the defaults for those it doesn't set; None without settings."""
    config = read_config(qfmt)
    if config is None:
        return None
    values = {key: config.get(key, default) for key, default in DEFAULTS.items()}
    values["hints"] = bool(values["hints"])
    values["refutation"] = bool(values["refutation"])
    if values["autoGrade"] not in GRADE_MODES:
        values["autoGrade"] = DEFAULTS["autoGrade"]
    try:
        values["easyTime"] = min(max(int(values["easyTime"]), 0), EASY_TIME_MAX)
    except (TypeError, ValueError):
        values["easyTime"] = DEFAULTS["easyTime"]
    return values
