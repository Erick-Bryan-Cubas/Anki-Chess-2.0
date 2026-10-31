import json
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

from lsi import template_options as to  # noqa: E402


def front(config: dict) -> str:
    return (
        "<script>\n  window.CARD_CONFIG = {};\n"
        f"  window.USER_CONFIG = {json.dumps(config, indent=2)};\n</script>\n"
        '<script src="./_ankiChess1.3.00.js"></script>\n<div id="chessRs-root"></div>'
    )


def test_a_template_without_the_helps_gets_their_defaults():
    assert to.options_of(front({"flipBoard": True})) == to.DEFAULTS


def test_the_template_values_are_read():
    qfmt = front({"hints": False, "refutation": True, "autoGrade": "answer", "easyTime": 15})
    assert to.options_of(qfmt) == {"hints": False, "refutation": True, "autoGrade": "answer", "easyTime": 15}


def test_bad_values_fall_back_to_safe_ones():
    qfmt = front({"autoGrade": "always", "easyTime": "soon"})
    assert to.options_of(qfmt)["autoGrade"] == "suggest"
    assert to.options_of(qfmt)["easyTime"] == 0
    assert to.options_of(front({"easyTime": 999}))["easyTime"] == to.EASY_TIME_MAX


def test_a_template_without_settings_is_left_out():
    assert to.options_of('<script src="./_ankiChess1.3.00.js"></script>') is None
    # Settings that aren't plain JSON can't be rewritten safely
    assert to.options_of("<script>window.USER_CONFIG = { hints: false };</script>") is None


def test_writing_changes_only_the_helps():
    qfmt = front({"flipBoard": True, "timer": 10000, "hints": True})
    written = to.write_config(qfmt, {"hints": False, "autoGrade": "off"})
    config = to.read_config(written)
    assert config == {"flipBoard": True, "timer": 10000, "hints": False, "autoGrade": "off"}
    # The rest of the template stays
    assert written.startswith("<script>\n  window.CARD_CONFIG = {};")
    assert written.endswith('<div id="chessRs-root"></div>')
    assert to.options_of(written)["hints"] is False


def test_an_unfilled_placeholder_gets_the_settings():
    qfmt = "<script>\n  // __USER_CONFIG__\n</script>"
    assert to.options_of(qfmt) == to.DEFAULTS
    assert to.read_config(to.write_config(qfmt, {"refutation": False})) == {"refutation": False}


def test_a_template_without_settings_is_not_written():
    assert to.write_config('<script src="./_ankiChess1.3.00.js"></script>', {"hints": False}) is None
