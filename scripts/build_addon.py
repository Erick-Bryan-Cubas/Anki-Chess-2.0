"""
Package the Lichess Study Importer add-on as an .ankiaddon file.
"""

import os
import zipfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
ADDON_DIR = os.path.join(ROOT, "addon", "lichess_study_importer")
OUT_DIR = os.path.join(ROOT, "dist-anki")
OUT_PATH = os.path.join(OUT_DIR, "lichess_study_importer.ankiaddon")

os.makedirs(OUT_DIR, exist_ok=True)
with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in sorted(os.listdir(ADDON_DIR)):
        path = os.path.join(ADDON_DIR, name)
        # .ankiaddon files must not contain __pycache__ or the folder itself
        if os.path.isfile(path) and not name.endswith(".pyc"):
            zf.write(path, name)

print(f"Success: {os.path.relpath(OUT_PATH, ROOT)} created.")
