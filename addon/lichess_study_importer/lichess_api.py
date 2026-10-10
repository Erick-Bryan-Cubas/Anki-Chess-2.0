"""
Lichess API: study PGNs, a user's studies, puzzles and analysed games.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

STUDY_URL_RE = re.compile(r"lichess\.org/study/([A-Za-z0-9]{8})(?:/([A-Za-z0-9]{8}))?")
BARE_ID_RE = re.compile(r"^\s*([A-Za-z0-9]{8})\s*$")
# A game, not a study, a user page or a puzzle: lichess.org/<8 chars>[<4 chars>][/black]
GAME_URL_RE = re.compile(r"lichess\.org/(?:game/export/)?([A-Za-z0-9]{8})(?:[A-Za-z0-9]{4})?(?![A-Za-z0-9/])|lichess\.org/([A-Za-z0-9]{8})/(?:white|black)")
PUZZLE_URL_RE = re.compile(r"lichess\.org/training/([A-Za-z0-9]{5})\b")
PUZZLE_ID_RE = re.compile(r"(?<![\w/.])([A-Za-z0-9]{5})(?![\w/])")
API = "https://lichess.org/api"
USER_AGENT = "AnkiChess-StudyImporter"


class LichessError(Exception):
    """Carries an i18n key (see i18n.py) and its parameters; the UI translates it."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


def _get(url: str, token: str = "", accept: str = "", timeout: int = 30) -> str:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    if token.strip():
        # Personal token: study:read for private studies, puzzle:read for puzzle activity
        headers["Authorization"] = f"Bearer {token.strip()}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            hint = "error.no_access.token_hint" if token.strip() else "error.no_access.public_hint"
            raise LichessError("error.no_access", code=e.code, hint=hint) from e
        if e.code == 429:
            raise LichessError("error.rate_limited") from e
        raise LichessError("error.http", code=e.code) from e
    except urllib.error.URLError as e:
        raise LichessError("error.connection", reason=e.reason) from e


def _ndjson(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# --- Studies ---


def parse_study_url(text: str) -> tuple[str, str | None] | None:
    """Return (study_id, chapter_id or None) from a study URL or a bare study id."""
    m = STUDY_URL_RE.search(text or "")
    if m:
        return m.group(1), m.group(2)
    m = BARE_ID_RE.match(text or "")
    if m:
        return m.group(1), None
    return None


def parse_study_urls(text: str) -> list[tuple[str, str | None]]:
    """Every study URL or bare study id in a text (several separated by spaces or lines)."""
    found = []
    for word in re.split(r"[\s,;]+", text or ""):
        parsed = parse_study_url(word)
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def fetch_study_pgn(
    study_id: str, chapter_id: str | None = None, token: str = "", timeout: int = 30
) -> str:
    path = f"{study_id}/{chapter_id}" if chapter_id else study_id
    # orientation: [Orientation "white"|"black"], the side the chapter is studied from
    return _get(
        f"{API}/study/{path}.pgn?comments=true&variations=true&clocks=false&orientation=true",
        token,
        timeout=timeout,
    )


def fetch_user_studies(username: str, token: str = "") -> list[dict]:
    """A user's studies (id, name, updatedAt...); private ones need their token."""
    return _ndjson(_get(f"{API}/study/by/{username.strip()}", token, accept="application/x-ndjson"))


# --- Puzzles ---


def parse_puzzle_ids(text: str) -> list[str]:
    """Puzzle ids from training links (lichess.org/training/abc12) or bare 5-character ids."""
    ids = PUZZLE_URL_RE.findall(text or "") or PUZZLE_ID_RE.findall(text or "")
    return list(dict.fromkeys(ids))


def fetch_puzzle(puzzle_id: str) -> dict:
    """{"game": {"pgn": ...}, "puzzle": {"id", "fen", "lastMove", "solution", "initialPly"...}}"""
    return json.loads(_get(f"{API}/puzzle/{puzzle_id}"))


def fetch_puzzle_activity(token: str, max_entries: int = 100) -> list[dict]:
    """Your latest puzzles, most recent first: {"date", "win", "puzzle": {...}} (puzzle:read)."""
    return _ndjson(
        _get(f"{API}/puzzle/activity?max={max_entries}", token, accept="application/x-ndjson")
    )


# --- Games ---


def parse_game_url(text: str) -> str | None:
    """Game id from a Lichess game link (any player's view of it)."""
    m = GAME_URL_RE.search(text or "")
    return (m.group(1) or m.group(2)) if m else None


def fetch_game_pgn(game_id: str, token: str = "") -> str:
    """
    A game's PGN with the server analysis, when it was requested on Lichess: evals,
    ?/??/?! marks with "X was best" comments and the best line as a variation.
    """
    return _get(
        f"https://lichess.org/game/export/{game_id}?evals=true&literate=true&clocks=false&opening=true",
        token,
        accept="application/x-chess-pgn",
    )
