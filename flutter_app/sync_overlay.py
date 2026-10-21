#!/usr/bin/env python3
"""Copies overlay/lib into the already-generated app/lib.

Use this after pulling or editing files in overlay/ so you do not have to delete and regenerate `app/`.
    python sync_overlay.py
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
src, dst = HERE / "overlay" / "lib", HERE / "app" / "lib"
if not dst.parent.exists():
    raise SystemExit("flutter_app/app does not exist yet; run `python setup.py` first.")
shutil.copytree(src, dst, dirs_exist_ok=True)
print(f"copied {src} -> {dst}")
