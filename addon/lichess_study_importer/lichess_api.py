"""
Download study PGNs from the public Lichess API.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request

STUDY_URL_RE = re.compile(r"lichess\.org/study/([A-Za-z0-9]{8})(?:/([A-Za-z0-9]{8}))?")
BARE_ID_RE = re.compile(r"^\s*([A-Za-z0-9]{8})\s*$")
API_BASE = "https://lichess.org/api/study"
USER_AGENT = "AnkiChess-StudyImporter"


class LichessError(Exception):
    """Carries an i18n key (see i18n.py) and its parameters; the UI translates it."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


def parse_study_url(text: str) -> tuple[str, str | None] | None:
    """Return (study_id, chapter_id or None) from a study URL or a bare study id."""
    m = STUDY_URL_RE.search(text or "")
    if m:
        return m.group(1), m.group(2)
    m = BARE_ID_RE.match(text or "")
    if m:
        return m.group(1), None
    return None


def fetch_study_pgn(
    study_id: str, chapter_id: str | None = None, token: str = "", timeout: int = 30
) -> str:
    path = f"{study_id}/{chapter_id}" if chapter_id else study_id
    url = f"{API_BASE}/{path}.pgn?comments=true&variations=true&clocks=false"
    headers = {"User-Agent": USER_AGENT}
    if token.strip():
        # Personal token with the study:read scope, needed for private studies
        headers["Authorization"] = f"Bearer {token.strip()}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            hint = (
                "error.no_access.token_hint" if token.strip() else "error.no_access.public_hint"
            )
            raise LichessError("error.no_access", code=e.code, hint=hint) from e
        if e.code == 429:
            raise LichessError("error.rate_limited") from e
        raise LichessError("error.http", code=e.code) from e
    except urllib.error.URLError as e:
        raise LichessError("error.connection", reason=e.reason) from e
