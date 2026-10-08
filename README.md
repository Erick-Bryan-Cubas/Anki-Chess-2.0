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

`addon/lichess_study_importer` is a separate Anki add-on that creates **one AnkiChess note per chapter** of a Lichess study.

- Menu: `Tools > Import Lichess study...` (also added to the Companion's `AnkiChess` menu when installed).
- Interface in English (default) or Brazilian Portuguese: set `"language"` to `"en"`, `"pt-BR"` or `"auto"` (follow Anki's language) in `Tools > Add-ons > Config`.
- Source: an exported study `.pgn` file, or a study/chapter URL (public API; private studies need a personal token with the `study:read` scope).
- Every chapter shows the side you play (**You play**) and its **Note type**, both editable:
  - The side is the chapter's orientation on Lichess (studies loaded by URL). For exported files it is guessed from the comments ("Jogam as brancas") or the result; opening lines and games without it are played on both sides.
  - The note type follows the side: `AnkiChess` when you make the first move, `AnkiChess Flipped` when the first move is the opponent's (played automatically, the board turned to your side), `AnkiChess Study` to play both sides. Missing ones are cloned from `AnkiChess` (or `base_note_type` in the add-on config) with `flipBoard`/`playBothSides` set; any other chess note type can also be picked.
  - Full games are optional and unchecked by default.
- Chapters imported before keep their note type when imported again (changing it needs a full sync): the importer lists them and offers to open them in the Browser, for `Notes > Change Note Type`.
- Re-importing skips chapters already imported (matched by chapter URL), or updates them if you choose.
- PGNs pasted in the editor with wrapped lines (Chess.com exports) are fixed without touching the note template: `{{text:PGN}}` drops `<br>` without a space, gluing moves and comments together (`Qg3<br>b5` → `Qg3b5`). The add-on shows those cards with their line breaks, and adds a space before each line break of the `PGN` field when the profile opens and before every sync, so AnkiDroid reads them too.

## Deck layout

Both importers file cards under one root deck, set in the add-on config (`deck_root`, default `Chess`, or `Xadrez` in pt-BR):

```
<root>::<study>::Opening lines       Lichess opening lines
                                     (tag <opening>::<family>::<variation>, e.g. opening::slav_defense::czech_variation)
<root>::<study>::Tactics             Lichess chapters set up from a position
<root>::<study>::Annotated games     Lichess full games (a result such as 1-0)
<root>::Openings::<family>           Chess.com opening, book moves, book lines (same tag)
<root>::My games::<error type>       Chess.com blunders, mistakes, misses, inaccuracies, missed mates
```

- Each Lichess study gets its own deck, named after the study (`StudyName`; the file name for PGNs without it). The root deck is the same for every study.
- Lichess chapters are classified automatically: from a `[FEN]` → tactics, unless the position is in the opening catalog; no FEN and no result (`*`) → opening line; no FEN with a result → annotated game. The type can be changed per chapter; the **Deck** column shows where each card goes.
- Opening lines are tagged with the family of the catalog name (`Slav Defense`, `Semi-Slav Defense`...), so the same opening can be reviewed across studies with a tag search; Chess.com opening cards are filed by that family.
- Re-importing with **Update notes already imported** also moves older notes into this layout.

## Chess.com games

`Tools > Import Chess.com game...` turns one of your games into cards:

| Card | When | Mode |
|---|---|---|
| Opening | The game's book moves (Lichess opening catalog, bundled offline) | Study |
| Book move | You left theory while the catalog had a continuation; any book move is accepted | Flipped |
| Book lines | Every named catalog line from where the game left theory (any move order), even lines not played; the line name is the prompt and you play your side. Keyed by the line, so other games in the same opening don't duplicate them | Flipped |
| Blunder / Mistake / Miss / Inaccuracy | Position before your error; the solution is a move you explored in the analysis board, otherwise Stockfish's best move (close alternatives are also accepted) | Flipped |
| Missed mate | You had a forced mate and did not play it; the whole mating line, any final mate accepted | Flipped |

- Source: the PGN exported from the Chess.com analysis board (`Share > PGN`) keeps the **Game Review** labels, which decide which moves become cards. A game link also works (public API), but then errors are classified by Stockfish (Lichess thresholds on the drop of the win chance).
- Your game move stays in the card marked as bad (`$4`, `$2`...), so repeating it fails the puzzle and shows its evaluation.
- Stockfish is downloaded on first use into `user_files/stockfish` (official release, ~80 MB), or set `stockfish_path`.
- Bundled: [python-chess](https://github.com/niklasf/python-chess) (GPL-3.0) in `vendor/`, and the [Lichess opening catalog](https://github.com/lichess-org/chess-openings) (CC0) in `data/openings/`.

```bash
npm run test:addon    # unit tests (pytest)
npm run build:addon   # dist-anki/lichess_study_importer.ankiaddon
```

Install the `.ankiaddon` with `Tools > Add-ons > Install from file...`, or for development link the folder into `addons21`:

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\Anki2\addons21\lichess_study_importer" -Target "$PWD\addon\lichess_study_importer"
```

