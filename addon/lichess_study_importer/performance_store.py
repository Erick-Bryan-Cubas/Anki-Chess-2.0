"""
Where the performance data lives.

- Game metrics (game_stats.GameStats) and the date the grading protocol started go in
  the collection's config, which AnkiWeb syncs: every computer sees the games analysed
  on the others. One key per game, so two computers never overwrite each other's games,
  and the same game analysed twice keeps one entry.
- The Lichess puzzle history is only cached on this computer: it can be downloaded again.

Takes the collection as a parameter (no aqt imports) so it can be unit tested.
"""

from __future__ import annotations

import json
import os

from .game_stats import GameStats

GAME_PREFIX = "ankichess_perf:game:"
PROTOCOL_KEY = "ankichess_perf:protocol_start"
USER_FILES = os.path.join(os.path.dirname(__file__), "user_files")
PUZZLE_CACHE = os.path.join(USER_FILES, "puzzle_activity.json")


def _same(a: dict, b: dict) -> bool:
    ignore = {"analysed_at"}
    return {k: v for k, v in a.items() if k not in ignore} == {k: v for k, v in b.items() if k not in ignore}


def save_game(col, stats: GameStats) -> bool:
    """Store a game's metrics; False when nothing changed (no write, nothing to sync)."""
    key = GAME_PREFIX + stats.key
    data = stats.to_dict()
    old = col.get_config(key, None)
    if isinstance(old, dict) and _same(old, data):
        return False
    col.set_config(key, data)
    return True


def load_games(col) -> list[GameStats]:
    games = []
    for key, value in col.all_config().items():
        if key.startswith(GAME_PREFIX) and isinstance(value, dict):
            try:
                games.append(GameStats.from_dict(value))
            except TypeError:
                continue  # written by an incompatible version
    return sorted(games, key=lambda g: (g.date or "", g.key))


def remove_game(col, key: str) -> None:
    col.remove_config(GAME_PREFIX + key)


def protocol_start(col) -> str | None:
    """YYYY-MM-DD from which the answer buttons follow the grading protocol."""
    value = col.get_config(PROTOCOL_KEY, None)
    return value if isinstance(value, str) and value else None


def set_protocol_start(col, date: str | None) -> None:
    if date:
        col.set_config(PROTOCOL_KEY, date)
    else:
        col.remove_config(PROTOCOL_KEY)


# --- Lichess puzzle history (local cache) ---


def load_puzzle_activity(path: str = PUZZLE_CACHE) -> dict:
    """{"user": lichess username, "entries": [{"date" (ms), "win", "rating", "themes", "id"}]}."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def merge_puzzle_activity(cached: dict, user: str, entries: list[dict]) -> dict:
    """Add downloaded activity entries (Lichess' format) to the cache, one per attempt."""
    if cached.get("user") and cached["user"].lower() != user.lower():
        cached = {}  # another account: start over
    seen = {(e["id"], e["date"]) for e in cached.get("entries", [])}
    merged = list(cached.get("entries", []))
    for entry in entries:
        puzzle = entry.get("puzzle") or {}
        compact = {
            "id": puzzle.get("id", ""),
            "date": int(entry.get("date", 0)),
            "win": bool(entry.get("win")),
            "rating": int(puzzle.get("rating", 0)),
            "themes": list(puzzle.get("themes", [])),
        }
        if compact["id"] and (compact["id"], compact["date"]) not in seen:
            seen.add((compact["id"], compact["date"]))
            merged.append(compact)
    merged.sort(key=lambda e: e["date"])
    return {"user": user, "entries": merged}


def save_puzzle_activity(data: dict, path: str = PUZZLE_CACHE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
