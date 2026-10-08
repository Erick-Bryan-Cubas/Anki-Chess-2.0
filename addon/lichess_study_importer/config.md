- **language**: interface language. `"en"` (default), `"pt-BR"`, or `"auto"` to follow Anki's interface language. The menu entry updates after restarting Anki; the dialog updates the next time it opens.
- **deck_root**: root deck for everything imported (set here; the import windows don't ask for it).
  Empty = `Chess` (English) or `Xadrez` (pt-BR). Each Lichess study goes to
  `<root>::<study>::Opening lines`, `::Tactics` and `::Annotated games` (opening lines are tagged
  `opening::<family>::<variation>`); Chess.com cards go to `<root>::Openings::<family>` and
  `<root>::My games::<error type>`. Re-importing with "update" moves older notes into this layout.
- **study_decks** / **chapter_decks**: deck names renamed in the import window (the study deck, and
  the subdeck of a chapter), by study and by chapter, so that importing the study again uses them.
  Filled by the window; remove an entry to go back to the default name.
- **include_games**: select full-game chapters (no FEN) by default.
- **update_existing**: on re-import, update notes already imported instead of skipping them.
- **strip_anno**: remove the `[%anno ...]` markers Lichess leaves in comments.
- **base_note_type**: note type the Flipped/Study ones are cloned from, when a chapter or card needs
  one that doesn't exist yet. Empty = `AnkiChess`, or the first chess note type set up as a puzzle.
- **lichess_token**: personal token (`study:read` scope) to download private studies. Stored as plain text.

**Chess.com games** (`Tools > Import Chess.com game...`):

- **chesscom_usernames**: your usernames; used to pick your side automatically.
- **chesscom_kinds**: card types selected last time (empty = default selection).
- **analysis_time**: Stockfish seconds per move (the positions that become cards get 3x more).
- **stockfish_path**: Stockfish executable. Empty = the one downloaded by the add-on (`user_files/stockfish`) or `stockfish` on the PATH.
