#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Télécharge les icônes (items/gemmes/enchantements) et les place dans static/icons/.
Fonctionne quel que soit le CWD.
"""

import json, time, urllib.request, functools, builtins, sys
from pathlib import Path

# --- stdout immédiat pour le GUI ---
print = functools.partial(builtins.print, flush=True)

# --- BASES (indépendant du CWD) ---
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent  # -> /var/www/html

# --- DOSSIERS ---
ITEMS_DIR     = BASE_DIR / "static" / "item"
GEMS_DIR      = BASE_DIR / "static" / "enchant"   # <= tu as dit que les gemmes sont ici
ENCHANTS_DIR  = BASE_DIR / "static" / "enchant"éé
OUTPUT_DIR    = BASE_DIR / "static" / "icons"

BASE_URL      = "https://wow.zamimg.com/images/wow/icons/large/{icon}.jpg"
DELAY, RETRIES, TIMEOUT = 0.15, 3, 15

def banner():
    print("[FETCH] Démarrage fetch_items_icons.py")
    print(f"[PY] {sys.executable}")
    print(f"[FILE] {Path(__file__).resolve()}")
    print(f"[CWD]  {Path.cwd()}")
    print(f"[BASE] {BASE_DIR}")
    for d in (ITEMS_DIR, GEMS_DIR, ENCHANTS_DIR, OUTPUT_DIR):
        print(f"[DIR]  {d} exist={d.exists()}")

def scan_json_icons(json_dir: Path, key="icon") -> set[str]:
    icons = set()
    if not json_dir.exists():
        print(f"[WARN] Dossier absent: {json_dir}")
        return icons
    files = list(json_dir.glob("*.json"))
    print(f"[SCAN] {json_dir} -> {len(files)} fichiers")
    for jf in files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            icon = (data.get(key) or "").strip().lower()
            if icon:
                icons.add(icon)
        except Exception as e:
            print(f"[WARN] {jf.name}: {e}")
    return icons

def already_downloaded() -> set[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return {p.stem.lower() for p in OUTPUT_DIR.glob("*.jpg")}

def download_with_retries(url: str, dest: Path) -> bool:
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r, dest.open("wb") as f:
                f.write(r.read())
            return True
        except Exception as e:
            print(f"  [TRY {attempt}/{RETRIES}] {e}")
            if attempt < RETRIES:
                time.sleep(0.8)
    return False

def main():
    banner()

    icons = set()
    icons |= scan_json_icons(ITEMS_DIR,    "icon")
    icons |= scan_json_icons(GEMS_DIR,     "icon")
    icons |= scan_json_icons(ENCHANTS_DIR, "icon")

    print(f"[INFO] Icônes uniques trouvées: {len(icons)}")
    present = already_downloaded()
    missing = sorted(i for i in icons if i not in present)
    print(f"[INFO] Déjà présents: {len(present & icons)}")
    print(f"[INFO] À télécharger: {len(missing)}")

    ok = fail = 0
    total = len(missing)
    for idx, icon in enumerate(missing, start=1):
        url  = BASE_URL.format(icon=icon)
        dest = OUTPUT_DIR / f"{icon}.jpg"
        print(f"[{idx}/{total}] {icon}.jpg")
        print(f"  [DL] {url}")
        if download_with_retries(url, dest):
            print("  [OK]")
            ok += 1
        else:
            print("  [ERROR]")
            fail += 1
        print(f"[PROGRESS] {ok+fail}/{total} (ok={ok}, fail={fail})")
        time.sleep(DELAY)

    print(f"[SUMMARY] OK={ok}  FAIL={fail}  OUT={OUTPUT_DIR}")
    print("[DONE] Terminé.")

if __name__ == "__main__":
    main()

