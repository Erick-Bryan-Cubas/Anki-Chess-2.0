"""
UI strings in English (default) and Brazilian Portuguese.

Pure Python (no aqt imports) so it can be unit tested outside Anki.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "menu.import": "Import Lichess study...",
        "dialog.title": "Import Lichess study",
        "source.url_placeholder": "https://lichess.org/study/XXXXXXXX  (or /chapter)",
        "source.load_url": "Load URL",
        "source.open_file": "Open .pgn file…",
        "source.file_dialog_title": "Open Lichess study",
        "source.file_filter": "PGN (*.pgn);;All files (*)",
        "token.label": "Token:",
        "token.placeholder": "Lichess token (optional, study:read scope) for private studies",
        "token.tooltip": (
            "Create one at https://lichess.org/account/oauth/token with the 'study:read' scope.\n"
            "It is stored as plain text in the add-on config."
        ),
        "study.none": "No study loaded.",
        "study.downloading": "Downloading study…",
        "study.download_failed": "Failed to download the study.",
        "study.summary": (
            "<b>{study}</b> — {total} chapters: {exercises} exercises, "
            "{games} full games, {empty} empty."
        ),
        "filter.include_games": "Include full games",
        "filter.check_exercises": "Select exercises",
        "filter.uncheck_all": "Unselect all",
        "table.chapter": "Chapter",
        "table.kind": "Type",
        "table.mode": "Mode",
        "table.moves": "Moves",
        "kind.exercise": "Exercise",
        "kind.game": "Full game",
        "kind.empty": "Empty",
        "mode.puzzle": "Puzzle",
        "mode.flipped": "Flipped",
        "mode.study": "Study",
        "modes.hint": (
            "<small><b>Puzzle</b>: you play the side to move. "
            "<b>Flipped</b>: the first move is the opponent's (\"White to play\"). "
            "<b>Study</b>: you play both sides. "
            "Each mode uses its own note type (cloned from the base note type if missing).</small>"
        ),
        "form.base_note_type": "Base note type:",
        "form.deck": "Deck:",
        "form.update_existing": "Update notes already imported (otherwise skip them)",
        "button.import": "Import",
        "warn.no_note_types": (
            "<b>No AnkiChess note type found.</b> Install the AnkiChess template "
            "(apkg or Companion add-on) before importing."
        ),
        "warn.read_file": "Could not read the file:\n{error}",
        "warn.invalid_url": "Enter a Lichess study link (lichess.org/study/…).",
        "warn.no_chapters": "No chapters found in the PGN.",
        "warn.no_selection": "No chapters selected.",
        "warn.no_deck": "Enter a deck name.",
        "warn.base_missing": "Base note type not found.",
        "warn.no_user_config": "The template has no window.USER_CONFIG block to set the mode.",
        "result.summary": (
            "Lichess: {created} created, {updated} updated, {skipped} already imported (skipped)."
        ),
        "undo.import": "Import Lichess study",
        "error.no_access": "Study not found or no access (HTTP {code}). {hint}",
        "error.no_access.token_hint": "Check that the token has the 'study:read' scope and access to the study.",
        "error.no_access.public_hint": (
            "If the study is private, enter a personal Lichess token ('study:read' scope) "
            "or export the PGN and use 'Open .pgn file'."
        ),
        "error.rate_limited": "Too many requests to Lichess. Wait a minute and try again.",
        "error.http": "HTTP error {code} while downloading the study.",
        "error.connection": "Could not connect to Lichess: {reason}",
    },
    "pt-BR": {
        "menu.import": "Importar estudo do Lichess...",
        "dialog.title": "Importar estudo do Lichess",
        "source.url_placeholder": "https://lichess.org/study/XXXXXXXX  (ou /capítulo)",
        "source.load_url": "Carregar URL",
        "source.open_file": "Abrir arquivo .pgn…",
        "source.file_dialog_title": "Abrir estudo do Lichess",
        "source.file_filter": "PGN (*.pgn);;Todos (*)",
        "token.label": "Token:",
        "token.placeholder": "Token do Lichess (opcional, escopo study:read) para estudos privados",
        "token.tooltip": (
            "Crie em https://lichess.org/account/oauth/token com o escopo 'study:read'.\n"
            "Fica salvo em texto puro na configuração do add-on."
        ),
        "study.none": "Nenhum estudo carregado.",
        "study.downloading": "Baixando estudo…",
        "study.download_failed": "Falha ao baixar o estudo.",
        "study.summary": (
            "<b>{study}</b> — {total} capítulos: {exercises} exercícios, "
            "{games} partidas, {empty} vazios."
        ),
        "filter.include_games": "Incluir partidas completas",
        "filter.check_exercises": "Marcar exercícios",
        "filter.uncheck_all": "Desmarcar tudo",
        "table.chapter": "Capítulo",
        "table.kind": "Tipo",
        "table.mode": "Modo",
        "table.moves": "Lances",
        "kind.exercise": "Exercício",
        "kind.game": "Partida",
        "kind.empty": "Vazio",
        "mode.puzzle": "Puzzle",
        "mode.flipped": "Flipped",
        "mode.study": "Study",
        "modes.hint": (
            "<small><b>Puzzle</b>: você joga o lado que move na posição. "
            "<b>Flipped</b>: o 1º lance é do adversário (\"Jogam as brancas\"). "
            "<b>Study</b>: você joga os dois lados. "
            "Cada modo usa um note type próprio (criado a partir do note type base, se não existir).</small>"
        ),
        "form.base_note_type": "Note type base:",
        "form.deck": "Baralho:",
        "form.update_existing": "Atualizar notas já importadas (senão, pula)",
        "button.import": "Importar",
        "warn.no_note_types": (
            "<b>Nenhum note type AnkiChess encontrado.</b> Instale o template AnkiChess "
            "(apkg ou Companion Add-on) antes de importar."
        ),
        "warn.read_file": "Não foi possível ler o arquivo:\n{error}",
        "warn.invalid_url": "Informe um link de estudo do Lichess (lichess.org/study/…).",
        "warn.no_chapters": "Nenhum capítulo encontrado no PGN.",
        "warn.no_selection": "Nenhum capítulo selecionado.",
        "warn.no_deck": "Informe o nome do baralho.",
        "warn.base_missing": "Note type base não encontrado.",
        "warn.no_user_config": "O template não tem bloco window.USER_CONFIG para configurar o modo.",
        "result.summary": (
            "Lichess: {created} criadas, {updated} atualizadas, {skipped} já existentes puladas."
        ),
        "undo.import": "Importar estudo do Lichess",
        "error.no_access": "Estudo não encontrado ou sem acesso (HTTP {code}). {hint}",
        "error.no_access.token_hint": "Confira se o token tem o escopo 'study:read' e acesso ao estudo.",
        "error.no_access.public_hint": (
            "Se o estudo é privado, informe um token pessoal do Lichess (escopo 'study:read') "
            "ou exporte o PGN e use 'Abrir arquivo .pgn'."
        ),
        "error.rate_limited": "Muitas requisições ao Lichess. Aguarde um minuto e tente novamente.",
        "error.http": "Erro HTTP {code} ao baixar o estudo.",
        "error.connection": "Falha de conexão com o Lichess: {reason}",
    },
}

_language = DEFAULT_LANGUAGE


def resolve_language(setting: str | None, anki_lang: str | None = None) -> str:
    """
    Map the config value to a supported language: "en", "pt-BR", or "auto"
    (follow Anki's UI language). Anything unknown falls back to English.
    """
    value = (setting or DEFAULT_LANGUAGE).strip()
    if value.lower() == "auto":
        value = anki_lang or DEFAULT_LANGUAGE
    lowered = value.replace("_", "-").lower()
    if lowered.startswith("pt"):
        return "pt-BR"
    return next((lang for lang in STRINGS if lang.lower() == lowered), DEFAULT_LANGUAGE)


def set_language(language: str) -> None:
    global _language
    _language = language if language in STRINGS else DEFAULT_LANGUAGE


def get_language() -> str:
    return _language


def tr(key: str, **params) -> str:
    text = STRINGS[_language].get(key) or STRINGS[DEFAULT_LANGUAGE][key]
    return text.format(**params) if params else text
