"""
Package the Lichess Study Importer add-on as an .ankiaddon file, with the preview of the
AnkiChess template built from this repository (npm run build:anki-media) in preview/.
"""

import importlib.util
import json
import os
import sys
import time
import zipfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
ADDON_DIR = os.path.join(ROOT, "addon", "lichess_study_importer")
OUT_DIR = os.path.join(ROOT, "dist-anki")
OUT_PATH = os.path.join(OUT_DIR, "lichess_study_importer.ankiaddon")

with open(os.path.join(ROOT, "package.json"), encoding="utf-8") as f:
    VERSION = json.load(f)["version"]
TEMPLATE_JS = os.path.join(OUT_DIR, "collection.media", f"_ankiChess{VERSION}.js")
if not os.path.isfile(TEMPLATE_JS):
    sys.exit(f"Template not built: {os.path.relpath(TEMPLATE_JS, ROOT)} (npm run build:anki-media)")

# The preview's name comes from the add-on itself (pure Python, loaded by its path)
spec = importlib.util.spec_from_file_location("template_preview", os.path.join(ADDON_DIR, "template_preview.py"))
template_preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template_preview)
PREVIEW = template_preview.preview_name(VERSION, time.strftime("%Y%m%d%H%M%S", time.gmtime()))

os.makedirs(OUT_DIR, exist_ok=True)
with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ADDON_DIR):
        rel_root = os.path.relpath(root, ADDON_DIR)
        # .ankiaddon files must not contain __pycache__, the folder itself, or user data.
        # Hidden folders and files (.pytest_cache, .DS_Store) are left out too, and the
        # preview comes from the template build below.
        dirs[:] = sorted(
            d
            for d in dirs
            if d != "__pycache__" and not d.startswith(".") and not (rel_root == "." and d in ("user_files", "preview"))
        )
        for name in sorted(files):
            if name.endswith(".pyc") or name.startswith(".") or (rel_root == "." and name == "meta.json"):
                continue
            path = os.path.join(root, name)
            zf.write(path, os.path.normpath(os.path.join(rel_root, name)).replace(os.sep, "/"))
    zf.write(TEMPLATE_JS, f"preview/{PREVIEW}")

print(f"Success: {os.path.relpath(OUT_PATH, ROOT)} created, with the template preview {PREVIEW}.")
