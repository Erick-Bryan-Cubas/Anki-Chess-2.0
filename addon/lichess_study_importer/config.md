- **language**: interface language. `"en"` (default), `"pt-BR"`, or `"auto"` to follow Anki's interface language. The menu entry updates after restarting Anki; the dialog updates the next time it opens.
- **deck_prefix**: prefix for the suggested deck (`Lichess::<study name>`). Empty = just the study name.
- **include_games**: select full-game chapters (no FEN) by default.
- **update_existing**: on re-import, update notes already imported instead of skipping them.
- **strip_anno**: remove the `[%anno ...]` markers Lichess leaves in comments.
- **base_note_type**: last base note type used (Flipped/Study note types are cloned from it).
- **lichess_token**: personal token (`study:read` scope) to download private studies. Stored as plain text.

**Chess.com games** (`Tools > Import Chess.com game...`):

- **chesscom_deck**: deck for the generated cards.
- **chesscom_usernames**: your usernames; used to pick your side automatically.
- **chesscom_kinds**: card types selected last time (empty = default selection).
- **analysis_time**: Stockfish seconds per move (the positions that become cards get 3x more).
- **stockfish_path**: Stockfish executable. Empty = the one downloaded by the add-on (`user_files/stockfish`) or `stockfish` on the PATH.
