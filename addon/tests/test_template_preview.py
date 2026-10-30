import copy
import os
import sys
import types

HERE = os.path.dirname(__file__)
ADDON_DIR = os.path.join(HERE, "..", "lichess_study_importer")

# Load the add-on modules as a package without running __init__ (it needs aqt)
if "lsi" not in sys.modules:
    pkg = types.ModuleType("lsi")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["lsi"] = pkg

from lsi import template_preview as tp  # noqa: E402

OFFICIAL = "_ankiChess1.3.00.js"
PREVIEW = "_ankiChess1.3.00-preview-20261030120000.js"
NEWER = "_ankiChess1.3.00-preview-20261101090000.js"


def front(script: str) -> str:
    return f'<script>window.USER_CONFIG = {{}};</script>\n<script src="./{script}"></script>\n<div id="chessRs-root"></div>'


def test_the_name_says_what_the_preview_builds_on():
    assert tp.preview_name("1.3.00", "20261030120000") == PREVIEW
    assert tp.preview_key(PREVIEW) < tp.preview_key(NEWER)
    assert tp.preview_key(NEWER) < tp.preview_key("_ankiChess1.3.01-preview-20260101000000.js")
    # The Companion add-on replaces _ankiChess<version>.js files only: not a preview
    assert not tp.OFFICIAL_RE.match(PREVIEW) and tp.OFFICIAL_RE.match(OFFICIAL)
    assert tp.official_of(NEWER) == OFFICIAL


def test_only_the_script_of_the_template_changes():
    html = front(OFFICIAL)
    assert tp.script_of(html) == OFFICIAL
    assert tp.with_script(html, PREVIEW) == html.replace(OFFICIAL, PREVIEW)
    assert tp.script_of("{{FrontSide}}") is None


def test_which_script_each_note_type_loads():
    everywhere, nowhere = (lambda _: True), (lambda _: False)
    # On: the official version the preview builds on, and older previews, take it
    assert tp.target(OFFICIAL, NEWER, nowhere) == NEWER
    assert tp.target(PREVIEW, NEWER, nowhere) == NEWER
    assert tp.target(NEWER, NEWER, nowhere) == NEWER
    # A newer official version (from the Companion) is kept, so is a newer preview
    assert tp.target("_ankiChess1.3.01.js", NEWER, nowhere) == "_ankiChess1.3.01.js"
    assert tp.target(NEWER, PREVIEW, nowhere) == NEWER
    # An older official version keeps its own HTML: the Companion updates it first
    assert tp.target("_ankiChess1.2.23.js", NEWER, nowhere) == "_ankiChess1.2.23.js"
    # Off: back to the official script, when it is in the media folder
    assert tp.target(NEWER, None, everywhere) == OFFICIAL
    assert tp.target(NEWER, None, nowhere) == NEWER
    assert tp.target(OFFICIAL, None, everywhere) == OFFICIAL


def test_bundled_is_the_newest_build_shipped(tmp_path, monkeypatch):
    monkeypatch.setattr(tp, "PREVIEW_DIR", str(tmp_path / "missing"))
    assert tp.bundled() is None  # a source checkout
    monkeypatch.setattr(tp, "PREVIEW_DIR", str(tmp_path))
    for name in (PREVIEW, NEWER, "README.md"):
        (tmp_path / name).write_text(name)
    assert tp.bundled() == NEWER


class FakeModels:
    def __init__(self, models):
        self.models = models

    def all(self):
        return copy.deepcopy(self.models)

    def update_dict(self, m):
        self.models = [m if old["name"] == m["name"] else old for old in self.models]

    def script(self, name):
        m = next(m for m in self.models if m["name"] == name)
        return tp.script_of(m["tmpls"][0]["qfmt"])


def collection(media, scripts: dict):
    """AnkiChess note types loading the scripts, and a note type of another kind."""
    models = [
        {
            "name": name,
            "ankiChessVersion": "2.0",
            "flds": [{"name": "PGN"}, {"name": "textField"}],
            "tmpls": [{"qfmt": front(script), "afmt": "{{FrontSide}}"}],
        }
        for name, script in scripts.items()
    ]
    models.append({"name": "Basic", "flds": [{"name": "Front"}], "tmpls": [{"qfmt": "{{Front}}", "afmt": ""}]})
    return types.SimpleNamespace(models=FakeModels(models), media=types.SimpleNamespace(dir=lambda: str(media)))


def test_the_preview_is_applied_and_follows_the_add_on(tmp_path, monkeypatch, anki_ops):
    shipped, media = tmp_path / "preview", tmp_path / "media"
    shipped.mkdir()
    media.mkdir()
    (shipped / PREVIEW).write_bytes(b"preview")
    (media / OFFICIAL).write_bytes(b"official")
    monkeypatch.setattr(tp, "PREVIEW_DIR", str(shipped))
    col = collection(media, {"AnkiChess": OFFICIAL, "AnkiChess Flipped": OFFICIAL})
    os.utime(media, (1, 1))

    assert anki_ops.apply_template_preview(col, True) == 2
    assert col.models.script("AnkiChess") == col.models.script("AnkiChess Flipped") == PREVIEW
    assert (media / PREVIEW).read_bytes() == b"preview" and (media / OFFICIAL).exists()
    assert os.path.getmtime(media) > 1  # Anki looks for changed media files
    assert col.models.models[-1]["tmpls"][0]["qfmt"] == "{{Front}}"
    assert anki_ops.apply_template_preview(col, True) == 0  # nothing left to do

    # An update of the add-on ships a newer build: it takes over, the old file goes
    (shipped / PREVIEW).unlink()
    (shipped / NEWER).write_bytes(b"newer")
    assert anki_ops.apply_template_preview(col, True) == 2
    assert col.models.script("AnkiChess") == NEWER
    assert sorted(os.listdir(media)) == sorted([OFFICIAL, NEWER])

    # Turned off: back to the official script, and the preview file goes
    assert anki_ops.apply_template_preview(col, False) == 2
    assert col.models.script("AnkiChess") == OFFICIAL
    assert os.listdir(media) == [OFFICIAL]


def test_a_newer_official_version_is_kept(tmp_path, monkeypatch, anki_ops):
    shipped, media = tmp_path / "preview", tmp_path / "media"
    shipped.mkdir()
    media.mkdir()
    (shipped / NEWER).write_bytes(b"newer")
    (media / NEWER).write_bytes(b"newer")
    monkeypatch.setattr(tp, "PREVIEW_DIR", str(shipped))
    # The Companion installed 1.3.01 over the preview
    col = collection(media, {"AnkiChess": "_ankiChess1.3.01.js"})
    assert anki_ops.apply_template_preview(col, True) == 0
    assert col.models.script("AnkiChess") == "_ankiChess1.3.01.js"
    assert os.listdir(media) == []  # the preview no note type loads


def test_nothing_happens_without_a_preview_shipped(tmp_path, monkeypatch, anki_ops):
    monkeypatch.setattr(tp, "PREVIEW_DIR", str(tmp_path / "missing"))
    col = collection(tmp_path, {"AnkiChess": OFFICIAL})
    assert anki_ops.apply_template_preview(col, True) == 0
    assert col.models.script("AnkiChess") == OFFICIAL
