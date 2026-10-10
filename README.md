# Anki Chess Note Template

#### Features:

- Works on desktop and ankidroid/anki mobile
- Robust PGN functionality, including multi line support, and embedded shapes. 
- Local stockfish analysis for back side.
- Built in configuration menu to design cards of many types.
  - Puzzle mode: Solve a tactic defined by a PGN.
  - Study mode: Play both sides of a given PGN.
  - play FEN position vs AI.
- A [Companion Addon](https://ankiweb.net/shared/info/1300975327) to streamline updating and managing configurations

![Demo Gif](./Gifs/demo.gif)

# installation

download the apkg in [releases](https://github.com/TowelSniffer/Anki-Chess-2.0/releases) and import to anki. 

## Updating 

Can be handled automatically via the [Companion Addon](https://ankiweb.net/shared/info/1300975327). Otherwise watch for new releases if you want to manage this yourself. 


## Help

Refer to configuration tool tips or 'About' menu for information on config options, and helpful information for using the ankiChess note template. 

![paste](images/tooltips.png)

> Join the [discord](https://discord.gg/YPj4Pz2Qzw).

# Table of Contents

- [Companion Addon](src/assets/docs/_CompanionAddon.md)
- [Board Modes](src/assets/docs/_BoardModes.md)
- [Config Options](src/assets/docs/_ConfigOptions.md)
- [Support](src/assets/docs/_Support.md)
- [Recent Changelog](src/assets/docs/_ChangeLog.md)

# Build

```bash
npm install
npm run build
```

## build ankiChess note template (apkg file/media files)

[uv](https://docs.astral.sh/uv/getting-started/installation/) is required for building the apkg file

```bash
uv venv
uv pip install genanki
```

Then run:
```bash
npm run build:anki
```

Build media only (no uv requirement)
```bash
npm run build:anki-media
```


files generated in 'dist-anki'

# Lichess Study Importer (add-on)

`addon/lichess_study_importer` is a separate Anki add-on that creates AnkiChess notes from Lichess studies, analysed games (Chess.com or Lichess) and Lichess puzzles.

- Menus in `Tools` (also in the Companion's `AnkiChess` menu when installed): **Import Lichess study…**, **Update imported Lichess studies**, **Import game (Chess.com / Lichess)…** and **Import Lichess puzzles…**.
- Interface in English (default) or Brazilian Portuguese: set `"language"` to `"en"`, `"pt-BR"` or `"auto"` (follow Anki's language) in `Tools > Add-ons > Config`.

## Studies

`Tools > Import Lichess study...` creates **one note per chapter**.

- Sources: study or chapter links (several at once, separated by spaces), **User's studies…** (lists the studies of a Lichess user to pick from), `.pgn` files (several at once), or **Paste PGN…**. Private studies need a personal token with the `study:read` scope (**Private study?**).
- Every chapter shows its **Status** in your collection (new, imported, changed on Lichess), the side you play (**You play**) and its **Note type**, all at a glance before importing:
  - The side is the chapter's orientation on Lichess (studies loaded by link). For exported files it is guessed from the comments ("Jogam as brancas") or the result; opening lines and games without it are played on both sides.
  - The note type follows the side: `AnkiChess` when you make the first move, `AnkiChess Flipped` when the first move is the opponent's (played automatically, the board turned to your side), `AnkiChess Study` to play both sides. Missing ones are cloned from `AnkiChess` (or `base_note_type` in the add-on config) with `flipBoard`/`playBothSides` set; any other chess note type can also be picked.
  - New and changed chapters are selected; full games only with **Include full games**. Chapters of other chess variants (Chess960…) can't be imported.
- **Gamebook** chapters work as on Lichess: only the main line is the answer, a variation you play is a wrong move that shows its comment, and the opponent keeps to the main line. The template reads `[ChapterMode "gamebook"]` from the PGN.
- Options:
  - **One note per variation**: each branch of an opening line becomes its own note, to drill every variation of a repertoire.
  - **Exercises from the ! and !! moves**: besides each full game, a "find the move" note for every move marked ! or !!, in the study's **Key moves** subdeck (a gamebook card: the other tries the author analysed are wrong answers with their comment).
- The table: filter box, sort by clicking a column title, columns resized by dragging and shown or hidden by right-clicking the titles (kept with the window size), a board preview of where you start playing the selected chapter, several chapters selected with Ctrl/Shift+click changed together, and a double-click opens a chapter on Lichess. The window stays open after importing, to import more.
- Notes keep an `[AnkiChessId]` in their PGN, so importing again finds them: it skips them, or updates them with **Update notes already imported** (only the ones that changed; your own tags are kept). PGNs from other sources (ChessBase, pasted…) are identified by the game itself, so they aren't duplicated either. Chapters deleted on Lichess are listed, with a link to see their notes in the Browser.
- Chapters imported before keep their note type when imported again (changing it needs a full sync): the importer lists them and offers to open them in the Browser, for `Notes > Change Note Type`.
- **Update imported Lichess studies** downloads again every study already in the collection and updates the notes whose chapter changed (they keep their note type and deck). New chapters are only reported, with an offer to open them in the import window.
- The note's text field shows the chapter and study names, the opening (ECO and name), the players and event of games, the author and a link to the original Lichess game when the PGN has them.
- PGNs pasted in the editor with wrapped lines (Chess.com exports) are fixed without touching the note template: `{{text:PGN}}` drops `<br>` without a space, gluing moves and comments together (`Qg3<br>b5` → `Qg3b5`). The add-on shows those cards with their line breaks, and adds a space before each line break of the `PGN` field when the profile opens and before every sync, so AnkiDroid reads them too.

## Deck layout and tags

All the importers file cards under one root deck, set in the add-on config (`deck_root`, default `Chess`, or `Xadrez` in pt-BR):

```
<root>::<study>::Opening lines       Lichess opening lines
<root>::<study>::Tactics             Lichess chapters set up from a position
<root>::<study>::Annotated games     Lichess full games (a result such as 1-0)
<root>::<study>::Key moves           "find the move" notes from the games' ! and !! moves
<root>::Openings::<family>           opening, book moves and book lines of your games
<root>::My games::<error type>       blunders, mistakes, misses, inaccuracies, missed mates of your games
<root>::Lichess puzzles              Lichess puzzles
```

- Each Lichess study gets its own deck, named after the study (`StudyName`; the file name for PGNs without it). Once loaded, its deck can be renamed (**Study deck** field, a list picks the study when several are loaded) and so can each chapter's subdeck (double-click a **Deck** cell or press F2; with several rows selected, F2 renames them all). `::` creates levels, e.g. `Chess::Courses::Sicilian`; spaces around each level are trimmed and empty levels dropped, as Anki would otherwise name them `blank`. An empty subdeck files the chapter in the study deck itself. Renamed decks are kept for the next import of the same study (`study_decks` / `chapter_decks` in the config).
- Lichess chapters are classified automatically: from a `[FEN]` → tactics, unless the position is in the opening catalog; no FEN and no result (`*`) → opening line; no FEN with a result → annotated game. The type can be changed per chapter.
- Tags are hierarchical (`::` separates the levels, `_` replaces spaces): `<study>::<study name>::<chapter name>` (e.g. `estudo::#C105_-_Siciliana_O'Kelly:_Outras_opções::Capítulo_1`), `<opening>::<family>::<variation>` (e.g. `opening::Slav_Defense::Czech_Variation`, from the opening Lichess writes in the chapter or the catalog), `eco::<code>`, and the source (`lichess::study::<id>`, `lichess::puzzle::<theme>`…). When updating a note, the importer replaces the tags it wrote before and keeps yours.

## Games (Chess.com and Lichess)

`Tools > Import game (Chess.com / Lichess)...` turns one of your games into cards:

| Card | When | Mode |
|---|---|---|
| Opening | The game's book moves (Lichess opening catalog, bundled offline) | Study |
| Book move | You left theory while the catalog had a continuation; any book move is accepted | Flipped |
| Book lines | Every named catalog line from where the game left theory (any move order), even lines not played; the line name is the prompt and you play your side. Keyed by the line, so other games in the same opening don't duplicate them | Flipped |
| Blunder / Mistake / Miss / Inaccuracy | Position before your error; the solution is the best move (from the analysis), close alternatives are also accepted | Flipped |
| Missed mate | You had a forced mate and did not play it; the whole mating line, any final mate accepted | Flipped |

- Sources: the PGN exported from the Chess.com analysis board (`Share > PGN`) keeps the **Game Review** labels, which decide which moves become cards; a Chess.com game link also works (public API), with errors classified by Stockfish (Lichess thresholds on the drop of the win chance).
- A **Lichess game link** brings the server analysis when it was requested on Lichess: its `?`/`??`/`?!` marks, "X was best" comments and best lines give the errors and their solutions, **without Stockfish**.
- Your game move stays in the card marked as bad (`$4`, `$2`...), so repeating it fails the puzzle and shows its evaluation.
- Stockfish is downloaded on first use into `user_files/stockfish` (official release, ~80 MB), or set `stockfish_path`.

## Lichess puzzles

`Tools > Import Lichess puzzles...` imports puzzles as cards: the opponent's last move is played first, then you play the solution (any mate is accepted on the last move).

- **Load my puzzles**: your latest puzzles (by default only the ones you failed), with a personal token that has the `puzzle:read` scope.
- Or puzzle links (`lichess.org/training/…`) or ids.
- Tags: `lichess::puzzle`, one per theme (`lichess::puzzle::mateIn3`…) and `lichess::puzzle::failed`.

## Build

- Bundled: [python-chess](https://github.com/niklasf/python-chess) (GPL-3.0) in `vendor/`, and the [Lichess opening catalog](https://github.com/lichess-org/chess-openings) (CC0) in `data/openings/`.

```bash
npm run test:addon    # unit tests (pytest)
npm run build:addon   # dist-anki/lichess_study_importer.ankiaddon
```

Install the `.ankiaddon` with `Tools > Add-ons > Install from file...`, or for development link the folder into `addons21`:

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\Anki2\addons21\lichess_study_importer" -Target "$PWD\addon\lichess_study_importer"
```
