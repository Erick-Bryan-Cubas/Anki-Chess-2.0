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
        "source.url_placeholder": "https://lichess.org/study/XXXXXXXX  (or /chapter; several links separated by spaces)",
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
        "table.side": "You play",
        "table.note_type": "Note type",
        "table.moves": "Moves",
        "kind.exercise": "Exercise",
        "kind.game": "Full game",
        "kind.line": "Opening line",
        "kind.empty": "Empty",
        "side.white": "White",
        "side.black": "Black",
        "side.both": "Both sides",
        "side.tooltip": "Your side in the chapter (its orientation on Lichess). First to move: {side}.",
        "side.to_move.w": "White",
        "side.to_move.b": "Black",
        "note_type.new": "(new)",
        "note_type.new_tip": "Created on import from the base note type.",
        "table.kind_tip": "Decides the subdeck: opening lines, tactics or annotated games.",
        "table.side_tip": (
            "Your side in the chapter, from its orientation on Lichess (guessed for exported "
            "files). Changing it picks the note type."
        ),
        "table.note_type_tip": (
            "{base}: you make the first move.\n"
            "{base} Flipped: the first move is the opponent's, played automatically, with the "
            "board turned to your side.\n"
            "{base} Study: you play both sides.\n"
            "Missing ones are created from {base}."
        ),
        "table.deck_tip": (
            "Subdeck inside the study deck (field above). Double-click a cell or press F2 to "
            "rename it: \"::\" creates more levels (Games::Tal), and an empty name puts the "
            "chapter in the study deck itself. With several rows selected, F2 renames them all.\n"
            "Hover a cell for the full deck and tags."
        ),
        "table.open_tip": "Double-click to open it on Lichess.",
        "table.hint": (
            "<small>Hover the column titles for help. Select several chapters (Ctrl/Shift+click) "
            "and change one of their lists, or press F2 on a Deck cell, to change them all. "
            "Drag the column borders to resize them; right-click the titles to show or hide "
            "columns.</small>"
        ),
        "form.study_deck": "Study deck:",
        "form.study_deck_tip": (
            "Deck for this study's chapters, which go to its subdecks (Deck column). \"::\" "
            "separates the levels, e.g. Chess::Courses::Sicilian; spaces around each level are "
            "removed and empty levels dropped. Anki ignores upper/lower case in deck names, so a "
            "deck with the same name is reused. Renamed decks are kept for the next import of "
            "this study."
        ),
        "form.study_deck_reset": "Default names",
        "form.study_deck_reset_tip": "Back to the study name from Lichess and the default subdecks.",
        "token.show": "Private study?",
        "button.import_count": "Import {count}",
        "table.deck": "Deck",
        "deck.root": "Chess",
        "deck.openings": "Openings",
        "deck.lines": "Opening lines",
        "deck.study_itself": "(study deck)",
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
        "tag.study": "study",
        "info.opening": "Opening",
        "info.author": "Author",
        "info.game": "Original game",
        "deck.key_moves": "Key moves",
        "card.main_line": "main line",
        "kind.unsupported": "Unsupported variant",
        "kind.unsupported_tip": "{variant}: the board only plays standard chess.",
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
            "Lichess: {created} created, {updated} updated, {unchanged} up to date, "
            "{skipped} already imported (skipped)."
        ),
        "result.other_type": (
            "{count} chapters had been imported before in another note type than the one chosen "
            "now: {targets}. Importing again doesn't change the note type, so their board stays "
            "on the old side.\n\nTo change it, select them in the Browser and use Notes › Change "
            "Note Type. The review history is kept, but Anki will ask for a full sync (upload "
            "from this computer, then download on AnkiDroid).\n\nOpen these notes in the Browser now?"
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
        "menu.import_chesscom": "Import game (Chess.com / Lichess)...",
        "cc.title": "Import game (Chess.com / Lichess)",
        "cc.url_placeholder": "https://www.chess.com/game/live/…  or  https://lichess.org/…",
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
        "cc.result": "{created} created, {updated} updated, {unchanged} up to date, {skipped} already imported (skipped).",
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
        "chesscom.invalid_url": "Enter a Chess.com game link (chess.com/game/live/… or the analysis link) or a Lichess game link (lichess.org/…).",
        "engine.unsupported_platform": "No Stockfish download for this system ({platform}). Choose an executable instead.",
        "engine.download_failed": "Could not download Stockfish: {reason}",
        "engine.not_in_archive": "The Stockfish download did not contain an executable.",
        "engine.start_failed": "Could not start Stockfish: {reason}",
        # --- More import features ---
        "button.close": "Close",
        "source.paste": "Paste PGN…",
        "source.pasted": "Pasted PGN",
        "source.user_studies": "User's studies…",
        "study.downloading_n": "Downloading study {done} of {total}…",
        "study.load_errors": "Some studies couldn't be loaded:\n{errors}",
        "study.summary_many": "<b>{count} studies</b> — {total} chapters: {exercises} exercises, {lines} opening lines, {games} full games, {empty} empty or unsupported.",
        "study.status_counts": "In your collection: {new} new, {changed} changed, {same} imported.",
        "study.removed": "<a href=\"removed\">{count} imported chapters are no longer in the study</a>.",
        "table.status": "Status",
        "table.status_tip": "Whether the chapter is already in your collection, and up to date with Lichess.",
        "status.new": "New",
        "status.same": "Imported",
        "status.changed": "Changed",
        "status.new_tip": "Not in your collection yet.",
        "status.same_tip": "Already in your collection, up to date.",
        "status.changed_tip": "In your collection, but different from Lichess (or partly imported): check \"Update notes already imported\" to update it.",
        "status.cards": "{count} notes from this chapter",
        "filter.placeholder": "Filter chapters…",
        "filter.check_new": "Select new and changed",
        "option.split_lines": "One note per variation (opening lines)",
        "option.split_lines_tip": "Each branch of an opening line becomes its own note, from the start to the end of the branch, to drill every variation of a repertoire.",
        "option.key_moves": "Exercises from the ! and !! moves (games)",
        "option.key_moves_tip": "Besides the game, each move marked ! or !! becomes a \"find the move\" note, in the study's Key moves subdeck. The other tries the author analysed there are wrong answers that show their comment.",
        "preview.none": "Select a chapter to see where you start playing.",
        "user_studies.title": "Studies of a Lichess user",
        "user_studies.username": "Username:",
        "user_studies.list": "List",
        "user_studies.load": "Load the selected",
        "user_studies.loading": "Loading the studies…",
        "user_studies.found": "{count} studies. Check the ones to load.",
        "user_studies.none": "No studies found.",
        "user_studies.private_hint": "Private studies are listed with your token (study:read scope).",
        "menu.update_studies": "Update imported Lichess studies",
        "update.none": "No imported Lichess study in the collection.",
        "update.progress": "Downloading the imported studies… {done} of {total}",
        "update.summary": "{studies} studies checked: {updated} notes updated, {unchanged} already up to date.",
        "update.removed": "{count} notes come from chapters no longer in their study (see the tag lichess::study::<id>).",
        "update.new_chapters": "New chapters, not imported:\n{studies}",
        "update.open_new": "Open the import window with these studies?",
        "update.undo": "Update Lichess studies",
        "cc.server_analysis": "Lichess analysis found: {count} errors marked, no Stockfish needed.",
        "menu.import_puzzles": "Import Lichess puzzles...",
        "puzzle.title": "Import Lichess puzzles",
        "puzzle.token_placeholder": "Lichess token with the puzzle:read scope",
        "puzzle.token_tip": "Your puzzle activity needs a personal token (lichess.org/account/oauth/token) with the puzzle:read scope. Puzzle links don't need it.",
        "puzzle.token_needed": "Enter a Lichess token with the puzzle:read scope to load your puzzle activity.",
        "puzzle.last": "Last",
        "puzzle.failed_only": "Only the failed ones",
        "puzzle.load_activity": "Load my puzzles",
        "puzzle.links_placeholder": "Puzzle links or ids: https://lichess.org/training/XXXXX …",
        "puzzle.invalid_links": "Enter puzzle links (lichess.org/training/…) or puzzle ids.",
        "puzzle.none": "No puzzles loaded.",
        "puzzle.loading": "Loading puzzle {done} of {total}…",
        "puzzle.summary": "{count} puzzles, {failed} failed.",
        "puzzle.no_cards": "No puzzles to import.",
        "puzzle.table.puzzle": "Puzzle",
        "puzzle.table.rating": "Rating",
        "puzzle.table.themes": "Themes",
        "puzzle.table.result": "You",
        "puzzle.solved": "Solved",
        "puzzle.failed": "Failed",
        "puzzle.deck": "Deck: <b>{deck}</b>",
        "puzzle.name": "Puzzle {id} ({rating})",
        "puzzle.themes": "Themes: {themes}",
        "puzzle.result": "Lichess puzzles: {created} created, {updated} updated, {unchanged} up to date, {skipped} skipped.",
        "puzzle.undo": "Import Lichess puzzles",
        "deck.puzzles": "Lichess puzzles",
    },
    "pt-BR": {
        "menu.import": "Importar estudo do Lichess...",
        "dialog.title": "Importar estudo do Lichess",
        "source.url_placeholder": "https://lichess.org/study/XXXXXXXX  (ou /capítulo; vários links separados por espaço)",
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
        "table.side": "Você joga",
        "table.note_type": "Tipo de nota",
        "table.moves": "Lances",
        "kind.exercise": "Exercício",
        "kind.game": "Partida",
        "kind.line": "Linha de abertura",
        "kind.empty": "Vazio",
        "side.white": "Brancas",
        "side.black": "Pretas",
        "side.both": "Os dois lados",
        "side.tooltip": "O seu lado no capítulo (a orientação do capítulo no Lichess). Primeiro a jogar: {side}.",
        "side.to_move.w": "brancas",
        "side.to_move.b": "pretas",
        "note_type.new": "(novo)",
        "note_type.new_tip": "Criado na importação a partir do tipo de nota base.",
        "table.kind_tip": "Decide o subdeck: linhas de abertura, táticas ou partidas comentadas.",
        "table.side_tip": (
            "O seu lado no capítulo, pela orientação do capítulo no Lichess (estimado em "
            "arquivos exportados). Mudar o lado escolhe o tipo de nota."
        ),
        "table.note_type_tip": (
            "{base}: o 1º lance é seu.\n"
            "{base} Flipped: o 1º lance é do adversário, jogado sozinho, com o tabuleiro "
            "virado para o seu lado.\n"
            "{base} Study: você joga os dois lados.\n"
            "Os que não existem são criados a partir do {base}."
        ),
        "table.deck_tip": (
            "Subdeck dentro do deck do estudo (campo acima). Clique duas vezes na célula ou "
            "aperte F2 para renomear: \"::\" cria mais níveis (Partidas::Tal), e um nome vazio "
            "põe o capítulo no próprio deck do estudo. Com várias linhas selecionadas, o F2 "
            "renomeia todas.\nPasse o mouse na célula para ver o deck completo e as tags."
        ),
        "table.open_tip": "Clique duas vezes para abrir no Lichess.",
        "table.hint": (
            "<small>Passe o mouse nos títulos das colunas para ver a ajuda. Selecione vários "
            "capítulos (Ctrl/Shift+clique) e mude uma das listas, ou aperte F2 numa célula de "
            "Deck, para mudar todos. Arraste a borda das colunas para ajustar a largura; clique "
            "com o botão direito nos títulos para mostrar ou esconder colunas.</small>"
        ),
        "form.study_deck": "Deck do estudo:",
        "form.study_deck_tip": (
            "Deck dos capítulos deste estudo, que vão para os subdecks dele (coluna Deck). "
            "\"::\" separa os níveis, ex.: Xadrez::Cursos::Siciliana; os espaços em volta de cada "
            "nível são removidos e níveis vazios descartados. O Anki não diferencia maiúsculas "
            "de minúsculas nos nomes de deck, então um deck com o mesmo nome é reaproveitado. "
            "Os nomes editados ficam guardados para a próxima importação deste estudo."
        ),
        "form.study_deck_reset": "Nomes padrão",
        "form.study_deck_reset_tip": "Volta para o nome do estudo no Lichess e os subdecks padrão.",
        "token.show": "Estudo privado?",
        "button.import_count": "Importar {count}",
        "table.deck": "Deck",
        "deck.root": "Xadrez",
        "deck.openings": "Aberturas",
        "deck.lines": "Linhas de abertura",
        "deck.study_itself": "(deck do estudo)",
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
        "tag.study": "estudo",
        "info.opening": "Abertura",
        "info.author": "Autor",
        "info.game": "Partida original",
        "deck.key_moves": "Lances das partidas",
        "card.main_line": "linha principal",
        "kind.unsupported": "Variante não suportada",
        "kind.unsupported_tip": "{variant}: o tabuleiro só joga xadrez clássico.",
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
            "Lichess: {created} criadas, {updated} atualizadas, {unchanged} já em dia, "
            "{skipped} já existentes puladas."
        ),
        "result.other_type": (
            "{count} capítulos já tinham sido importados num tipo de nota diferente do escolhido "
            "agora: {targets}. Importar de novo não troca o tipo de nota, então o tabuleiro deles "
            "continua do lado antigo.\n\nPara trocar, selecione-os no Navegador e use Notas › "
            "Mudar tipo de nota. O histórico de revisões é mantido, mas o Anki vai pedir uma "
            "sincronização completa (envie deste computador e depois baixe no AnkiDroid)."
            "\n\nAbrir essas notas no Navegador agora?"
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
        "menu.import_chesscom": "Importar partida (Chess.com / Lichess)...",
        "cc.title": "Importar partida (Chess.com / Lichess)",
        "cc.url_placeholder": "https://www.chess.com/game/live/…  ou  https://lichess.org/…",
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
        "cc.result": "{created} criadas, {updated} atualizadas, {unchanged} já em dia, {skipped} já existentes puladas.",
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
        # --- More import features ---
        "button.close": "Fechar",
        "source.paste": "Colar PGN…",
        "source.pasted": "PGN colado",
        "source.user_studies": "Estudos de um usuário…",
        "study.downloading_n": "Baixando o estudo {done} de {total}…",
        "study.load_errors": "Alguns estudos não puderam ser carregados:\n{errors}",
        "study.summary_many": "<b>{count} estudos</b> — {total} capítulos: {exercises} exercícios, {lines} linhas de abertura, {games} partidas, {empty} vazios ou não suportados.",
        "study.status_counts": "Na sua coleção: {new} novos, {changed} alterados, {same} importados.",
        "study.removed": "<a href=\"removed\">{count} capítulos importados não estão mais no estudo</a>.",
        "table.status": "Situação",
        "table.status_tip": "Se o capítulo já está na sua coleção, e em dia com o Lichess.",
        "status.new": "Novo",
        "status.same": "Importado",
        "status.changed": "Alterado",
        "status.new_tip": "Ainda não está na sua coleção.",
        "status.same_tip": "Já está na sua coleção, em dia.",
        "status.changed_tip": "Está na sua coleção, mas diferente do Lichess (ou importado em parte): marque \"Atualizar notas já importadas\" para atualizar.",
        "status.cards": "{count} notas deste capítulo",
        "filter.placeholder": "Filtrar capítulos…",
        "filter.check_new": "Marcar novos e alterados",
        "option.split_lines": "Uma nota por variante (linhas de abertura)",
        "option.split_lines_tip": "Cada ramo de uma linha de abertura vira uma nota, do início ao fim do ramo, para treinar cada variante do repertório.",
        "option.key_moves": "Exercícios dos lances ! e !! (partidas)",
        "option.key_moves_tip": "Além da partida, cada lance marcado com ! ou !! vira uma nota \"encontre o lance\", no subdeck Lances das partidas do estudo. As outras tentativas que o autor analisou ali são respostas erradas que mostram o comentário dele.",
        "preview.none": "Selecione um capítulo para ver onde você começa a jogar.",
        "user_studies.title": "Estudos de um usuário do Lichess",
        "user_studies.username": "Usuário:",
        "user_studies.list": "Listar",
        "user_studies.load": "Carregar os marcados",
        "user_studies.loading": "Carregando os estudos…",
        "user_studies.found": "{count} estudos. Marque os que quer carregar.",
        "user_studies.none": "Nenhum estudo encontrado.",
        "user_studies.private_hint": "Estudos privados aparecem com o seu token (escopo study:read).",
        "menu.update_studies": "Atualizar estudos importados do Lichess",
        "update.none": "Nenhum estudo do Lichess importado na coleção.",
        "update.progress": "Baixando os estudos importados… {done} de {total}",
        "update.summary": "{studies} estudos verificados: {updated} notas atualizadas, {unchanged} já em dia.",
        "update.removed": "{count} notas são de capítulos que não estão mais no estudo (veja a tag lichess::study::<id>).",
        "update.new_chapters": "Capítulos novos, não importados:\n{studies}",
        "update.open_new": "Abrir a janela de importação com esses estudos?",
        "update.undo": "Atualizar estudos do Lichess",
        "cc.server_analysis": "Análise do Lichess encontrada: {count} erros marcados, sem precisar do Stockfish.",
        "menu.import_puzzles": "Importar puzzles do Lichess...",
        "puzzle.title": "Importar puzzles do Lichess",
        "puzzle.token_placeholder": "Token do Lichess com o escopo puzzle:read",
        "puzzle.token_tip": "A sua atividade de puzzles precisa de um token pessoal (lichess.org/account/oauth/token) com o escopo puzzle:read. Links de puzzles não precisam.",
        "puzzle.token_needed": "Informe um token do Lichess com o escopo puzzle:read para carregar a sua atividade de puzzles.",
        "puzzle.last": "Últimos",
        "puzzle.failed_only": "Só os que errei",
        "puzzle.load_activity": "Carregar meus puzzles",
        "puzzle.links_placeholder": "Links ou ids de puzzles: https://lichess.org/training/XXXXX …",
        "puzzle.invalid_links": "Informe links de puzzles (lichess.org/training/…) ou ids de puzzles.",
        "puzzle.none": "Nenhum puzzle carregado.",
        "puzzle.loading": "Carregando o puzzle {done} de {total}…",
        "puzzle.summary": "{count} puzzles, {failed} errados.",
        "puzzle.no_cards": "Nenhum puzzle para importar.",
        "puzzle.table.puzzle": "Puzzle",
        "puzzle.table.rating": "Rating",
        "puzzle.table.themes": "Temas",
        "puzzle.table.result": "Você",
        "puzzle.solved": "Acertou",
        "puzzle.failed": "Errou",
        "puzzle.deck": "Deck: <b>{deck}</b>",
        "puzzle.name": "Puzzle {id} ({rating})",
        "puzzle.themes": "Temas: {themes}",
        "puzzle.result": "Puzzles do Lichess: {created} criados, {updated} atualizados, {unchanged} já em dia, {skipped} pulados.",
        "puzzle.undo": "Importar puzzles do Lichess",
        "deck.puzzles": "Puzzles do Lichess",
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
