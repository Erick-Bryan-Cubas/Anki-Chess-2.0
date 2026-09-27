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
            "<b>{study}</b> — {total} chapters: {exercises} exercises, {lines} opening lines, "
            "{games} full games, {empty} empty."
        ),
        "filter.include_games": "Include full games",
        "filter.check_exercises": "Select exercises and lines",
        "filter.uncheck_all": "Unselect all",
        "table.chapter": "Chapter",
        "table.kind": "Type",
        "table.mode": "Mode",
        "table.moves": "Moves",
        "kind.exercise": "Exercise",
        "kind.game": "Full game",
        "kind.line": "Opening line",
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
        "form.deck_root": "Root deck:",
        "form.deck_root_tip": "Cards go to <root>::Openings::<family>, ::Tactics::<study>, ::Annotated games::<study> and ::My games::<error type>.",
        "table.deck": "Deck",
        "deck.root": "Chess",
        "deck.openings": "Openings",
        "deck.other_openings": "Other",
        "deck.tactics": "Tactics",
        "deck.games": "Annotated games",
        "deck.my_games": "My games",
        "deck.unnamed_study": "Study",
        "deck.kind.blunder": "Blunders",
        "deck.kind.mistake": "Mistakes",
        "deck.kind.miss": "Misses",
        "deck.kind.inaccuracy": "Inaccuracies",
        "deck.kind.missed_mate": "Missed mates",
        "tag.opening": "opening",
        "form.update_existing": "Update notes already imported (otherwise skip them)",
        "button.import": "Import",
        "button.cancel": "Cancel",
        "warn.no_note_types": (
            "<b>No AnkiChess note type found.</b> Install the AnkiChess template "
            "(apkg or Companion add-on) before importing."
        ),
        "warn.read_file": "Could not read the file:\n{error}",
        "warn.invalid_url": "Enter a Lichess study link (lichess.org/study/…).",
        "warn.no_chapters": "No chapters found in the PGN.",
        "warn.no_selection": "No chapters selected.",
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
        # --- Chess.com game import ---
        "menu.import_chesscom": "Import Chess.com game...",
        "cc.title": "Import Chess.com game",
        "cc.url_placeholder": "https://www.chess.com/game/live/…  (or the analysis link)",
        "cc.load_link": "Load link",
        "cc.open_file": "Open exported .pgn…",
        "cc.paste": "Paste PGN…",
        "cc.paste_title": "Paste PGN",
        "cc.paste_label": "Paste the PGN exported from the Chess.com analysis board:",
        "cc.none": "No game loaded. For the Game Review labels, export the PGN from the analysis board (Share > PGN).",
        "cc.loading": "Downloading game…",
        "cc.summary": "<b>{white} vs {black}</b> — {date}, {result}. {labels}",
        "cc.labels_found": "Game Review labels found: {count} (blunders, mistakes, misses, inaccuracies).",
        "cc.labels_missing": "No Game Review labels in this PGN: errors are classified by Stockfish.",
        "cc.side": "Your side:",
        "cc.side_white": "White ({name})",
        "cc.side_black": "Black ({name})",
        "cc.cards": "Cards:",
        "cc.move_time": "Seconds per move:",
        "cc.analyze": "Analyze",
        "cc.analyzing": "Analyzing move {done} of {total}…",
        "cc.no_cards": "No cards for the selected types in this game.",
        "cc.undo": "Import Chess.com game",
        "cc.result": "Chess.com: {created} created, {updated} updated, {skipped} already imported (skipped).",
        "cc.table.move": "Game move",
        "cc.table.solution": "Solution",
        "cc.table.eval": "Eval",
        "cc.engine_found": "Stockfish: {path}",
        "cc.engine_missing": "Stockfish not found (needed for errors and missed mates).",
        "cc.engine_download": "Download Stockfish",
        "cc.engine_choose": "Choose…",
        "cc.engine_ask_download": "Stockfish is needed to find the best moves. Download it now (about 80 MB)?",
        "cc.engine_downloading": "Downloading Stockfish… {done} of {total} MB",
        "kind.opening": "Opening",
        "kind.book": "Book move",
        "kind.book_line": "Book lines",
        "kind.blunder": "Blunder",
        "kind.mistake": "Mistake",
        "kind.miss": "Miss",
        "kind.inaccuracy": "Inaccuracy",
        "kind.missed_mate": "Missed mate",
        "card.opening": "Opening: {opening}",
        "card.opening_moves": "{count} book moves",
        "card.book": "{number} Book move ({opening})",
        "card.book_comment": "Book: {opening}",
        "card.book_line": "Book line: {opening}",
        "card.book_line_until": "Book line: {opening} (until {move})",
        "card.played_comment": "Played in the game: {move}",
        "card.played_comment_eval": "Played in the game: {move} ({score})",
        "card.solution_comment": "Best: {move} ({score})",
        "card.error": "{number} Better than {move} ({label})",
        "card.missed_mate": "{number} Missed mate in {mate}",
        "chesscom.not_found": "Game not found on Chess.com (it must be finished and public).",
        "chesscom.rate_limited": "Too many requests to Chess.com. Wait a minute and try again.",
        "chesscom.http": "HTTP error {code} while downloading the game.",
        "chesscom.connection": "Could not connect to Chess.com: {reason}",
        "chesscom.invalid_pgn": "Could not read a game from this PGN.",
        "chesscom.invalid_url": "Enter a Chess.com game link (chess.com/game/live/… or the analysis link).",
        "engine.unsupported_platform": "No Stockfish download for this system ({platform}). Choose an executable instead.",
        "engine.download_failed": "Could not download Stockfish: {reason}",
        "engine.not_in_archive": "The Stockfish download did not contain an executable.",
        "engine.start_failed": "Could not start Stockfish: {reason}",
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
            "<b>{study}</b> — {total} capítulos: {exercises} exercícios, {lines} linhas de abertura, "
            "{games} partidas, {empty} vazios."
        ),
        "filter.include_games": "Incluir partidas completas",
        "filter.check_exercises": "Marcar exercícios e linhas",
        "filter.uncheck_all": "Desmarcar tudo",
        "table.chapter": "Capítulo",
        "table.kind": "Tipo",
        "table.mode": "Modo",
        "table.moves": "Lances",
        "kind.exercise": "Exercício",
        "kind.game": "Partida",
        "kind.line": "Linha de abertura",
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
        "form.deck_root": "Deck raiz:",
        "form.deck_root_tip": "Os cartões vão para <raiz>::Aberturas::<família>, ::Táticas::<estudo>, ::Partidas comentadas::<estudo> e ::Minhas partidas::<tipo de erro>.",
        "table.deck": "Deck",
        "deck.root": "Xadrez",
        "deck.openings": "Aberturas",
        "deck.other_openings": "Outras",
        "deck.tactics": "Táticas",
        "deck.games": "Partidas comentadas",
        "deck.my_games": "Minhas partidas",
        "deck.unnamed_study": "Estudo",
        "deck.kind.blunder": "Capivaradas",
        "deck.kind.mistake": "Erros",
        "deck.kind.miss": "Chances perdidas",
        "deck.kind.inaccuracy": "Imprecisões",
        "deck.kind.missed_mate": "Mates perdidos",
        "tag.opening": "abertura",
        "form.update_existing": "Atualizar notas já importadas (senão, pula)",
        "button.import": "Importar",
        "button.cancel": "Cancelar",
        "warn.no_note_types": (
            "<b>Nenhum note type AnkiChess encontrado.</b> Instale o template AnkiChess "
            "(apkg ou Companion Add-on) antes de importar."
        ),
        "warn.read_file": "Não foi possível ler o arquivo:\n{error}",
        "warn.invalid_url": "Informe um link de estudo do Lichess (lichess.org/study/…).",
        "warn.no_chapters": "Nenhum capítulo encontrado no PGN.",
        "warn.no_selection": "Nenhum capítulo selecionado.",
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
        # --- Importação de partidas do Chess.com ---
        "menu.import_chesscom": "Importar partida do Chess.com...",
        "cc.title": "Importar partida do Chess.com",
        "cc.url_placeholder": "https://www.chess.com/game/live/…  (ou o link da análise)",
        "cc.load_link": "Carregar link",
        "cc.open_file": "Abrir .pgn exportado…",
        "cc.paste": "Colar PGN…",
        "cc.paste_title": "Colar PGN",
        "cc.paste_label": "Cole o PGN exportado do tabuleiro de análise do Chess.com:",
        "cc.none": "Nenhuma partida carregada. Para usar as marcações da Game Review, exporte o PGN no tabuleiro de análise (Compartilhar > PGN).",
        "cc.loading": "Baixando partida…",
        "cc.summary": "<b>{white} vs {black}</b> — {date}, {result}. {labels}",
        "cc.labels_found": "Marcações da Game Review encontradas: {count} (capivaradas, erros, chances perdidas, imprecisões).",
        "cc.labels_missing": "Este PGN não tem marcações da Game Review: os erros serão classificados pelo Stockfish.",
        "cc.side": "Seu lado:",
        "cc.side_white": "Brancas ({name})",
        "cc.side_black": "Pretas ({name})",
        "cc.cards": "Cartões:",
        "cc.move_time": "Segundos por lance:",
        "cc.analyze": "Analisar",
        "cc.analyzing": "Analisando lance {done} de {total}…",
        "cc.no_cards": "Nenhum cartão dos tipos selecionados nesta partida.",
        "cc.undo": "Importar partida do Chess.com",
        "cc.result": "Chess.com: {created} criadas, {updated} atualizadas, {skipped} já existentes puladas.",
        "cc.table.move": "Lance da partida",
        "cc.table.solution": "Solução",
        "cc.table.eval": "Avaliação",
        "cc.engine_found": "Stockfish: {path}",
        "cc.engine_missing": "Stockfish não encontrado (necessário para erros e mates perdidos).",
        "cc.engine_download": "Baixar Stockfish",
        "cc.engine_choose": "Escolher…",
        "cc.engine_ask_download": "O Stockfish é necessário para achar os melhores lances. Baixar agora (cerca de 80 MB)?",
        "cc.engine_downloading": "Baixando Stockfish… {done} de {total} MB",
        "kind.opening": "Abertura",
        "kind.book": "Lance de livro",
        "kind.book_line": "Linhas de livro",
        "kind.blunder": "Capivarada",
        "kind.mistake": "Erro",
        "kind.miss": "Chance perdida",
        "kind.inaccuracy": "Imprecisão",
        "kind.missed_mate": "Mate perdido",
        "card.opening": "Abertura: {opening}",
        "card.opening_moves": "{count} lances de livro",
        "card.book": "{number} Lance de livro ({opening})",
        "card.book_comment": "Livro: {opening}",
        "card.book_line": "Linha de livro: {opening}",
        "card.book_line_until": "Linha de livro: {opening} (até {move})",
        "card.played_comment": "Jogado na partida: {move}",
        "card.played_comment_eval": "Jogado na partida: {move} ({score})",
        "card.solution_comment": "Melhor: {move} ({score})",
        "card.error": "{number} Melhor que {move} ({label})",
        "card.missed_mate": "{number} Mate em {mate} perdido",
        "chesscom.not_found": "Partida não encontrada no Chess.com (precisa estar finalizada e ser pública).",
        "chesscom.rate_limited": "Muitas requisições ao Chess.com. Aguarde um minuto e tente novamente.",
        "chesscom.http": "Erro HTTP {code} ao baixar a partida.",
        "chesscom.connection": "Falha de conexão com o Chess.com: {reason}",
        "chesscom.invalid_pgn": "Não foi possível ler uma partida deste PGN.",
        "chesscom.invalid_url": "Informe um link de partida do Chess.com (chess.com/game/live/… ou o link da análise).",
        "engine.unsupported_platform": "Não há download do Stockfish para este sistema ({platform}). Escolha um executável.",
        "engine.download_failed": "Não foi possível baixar o Stockfish: {reason}",
        "engine.not_in_archive": "O download do Stockfish não continha um executável.",
        "engine.start_failed": "Não foi possível iniciar o Stockfish: {reason}",
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
