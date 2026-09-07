#!/usr/bin/env python3
"""
scan_sources.py — scan the provided source folders and generate an initial edl.json.
Only writes duration and basic metadata; ratings/sections/notes are filled in later.
"""
import argparse
import json, os, subprocess
from pathlib import Path
from project_paths import footage_root, portable_source, manifest_output

BUILD = os.path.dirname(os.path.abspath(__file__))
FOLDER_NAMES = ["allrawfootageunsorted", "clipsfortaste", "itovault", "rawtalkingclips"]

# Placeholder tags per filename pattern
FAMILY_HINTS = {
    "singular_display": "pov",
    "dji": "drone",
    "ScreenRecording": "screen",
    "Screen Recording": "screen",
    "ito": "product",
    "IMG_": "clip",
}

SECTION_HINTS = {
    "ito": "product",
    "intro": "open",
    "talking": "solution",
    "founder": "solution",
    "singular": "open",
}


def duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out or 0)
    except Exception:
        return 0


def classify(name):
    family = "clip"
    section = "flex"
    for k, v in FAMILY_HINTS.items():
        if k in name:
            family = v
            break
    for k, v in SECTION_HINTS.items():
        if k in name:
            section = v
            break
    # talking clips -> founder/solution
    if family == "clip" and "rawtalking" in name:
        family = "founder"
        section = "solution"
    return family, section


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--footage-root')
    parser.add_argument('--output', default=os.path.join(BUILD, 'edl.json'))
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    root = footage_root(Path(BUILD), args.footage_root)
    manifest_output(Path(args.output), args.overwrite)
    pool = []
    idx = 0
    seen = set()
    for folder in [root / name for name in FOLDER_NAMES]:
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            p = os.path.join(folder, f)
            if not os.path.isfile(p):
                continue
            if f.lower().endswith(('.ds_store', '.jpg', '.png', '.json', '.txt')):
                continue
            dur = duration(p)
            if dur < 0.5:
                continue
            rel = portable_source(Path(p), root)
            family, section = classify(f)
            pool.append({
                "id": f"s{idx:03d}",
                "src": rel,
                "in": 0.0,
                "out": dur,
                "speed": 1.0,
                "section": section,
                "family": family,
                "rating": 3,
                "subject": family,
                "grade": ["crush_black"],
                "note": f"{f} ({dur:.1f}s)"
            })
            idx += 1
            seen.add(p)

    edl = {
        "project": "itomarkets-brand-film",
        "fps": 30,
        "canvas": [1920, 1080],
        "grade_base": "ito: deep contrast, warm-neutral highlights, cool shadows, subtle grain",
        "pool": pool
    }
    out_path = args.output
    with open(out_path, "w") as fh:
        json.dump(edl, fh, indent=1)
    print(f"wrote {out_path}: {len(pool)} selects")


if __name__ == "__main__":
    main()
