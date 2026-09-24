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
- Every chapter is listed with a suggested mode, which you can change:
  - **Puzzle**: you play the side to move.
  - **Flipped**: the first move belongs to the opponent ("Jogam as brancas").
  - **Study**: you play both sides. Used for full games, which are optional and unchecked by default.
- Each mode uses its own note type (`<base>`, `<base> Flipped`, `<base> Study`). Missing ones are cloned from the base note type with `flipBoard`/`playBothSides` set.
- Re-importing skips chapters already imported (matched by chapter URL), or updates them if you choose.

```bash
npm run test:addon    # unit tests (pytest)
npm run build:addon   # dist-anki/lichess_study_importer.ankiaddon
```

Install the `.ankiaddon` with `Tools > Add-ons > Install from file...`, or for development link the folder into `addons21`:

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\Anki2\addons21\lichess_study_importer" -Target "$PWD\addon\lichess_study_importer"
```

