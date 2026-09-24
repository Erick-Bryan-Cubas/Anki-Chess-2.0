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
    pass


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
                "Confira se o token tem o escopo 'study:read' e acesso ao estudo."
                if token.strip()
                else "Se o estudo é privado, informe um token pessoal do Lichess "
                "(escopo 'study:read') ou exporte o PGN e use 'Abrir arquivo .pgn'."
            )
            raise LichessError(f"Estudo não encontrado ou sem acesso (HTTP {e.code}). {hint}") from e
        if e.code == 429:
            raise LichessError("Muitas requisições ao Lichess. Aguarde um minuto e tente novamente.") from e
        raise LichessError(f"Erro HTTP {e.code} ao baixar o estudo.") from e
    except urllib.error.URLError as e:
        raise LichessError(f"Falha de conexão com o Lichess: {e.reason}") from e
