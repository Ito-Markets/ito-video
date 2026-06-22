#!/usr/bin/env python3
"""
export_capcut.py — export the assembled ItoMarkets timeline as a native CapCut draft.
Reads concat.txt and writes "ito_brand_film" into the CapCut drafts folder.
"""
import os, subprocess, sys

BUILD = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
NAME = "ito_brand_film"

def dur_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out or 0)

files = []
concat_path = os.path.join(BUILD, "concat.txt")
if not os.path.exists(concat_path):
    print(f"missing {concat_path}")
    sys.exit(1)

for line in open(concat_path):
    line = line.strip()
    if line.startswith("file '"):
        files.append(line[6:-1])
print(f"{len(files)} segments")

import pycapcut as cc

df = cc.DraftFolder(DRAFTS)
script = df.create_draft(NAME, 1920, 1080, allow_replace=True)
script.add_track(cc.TrackType.video)

t = 0.0
ok = 0
for f in files:
    d = dur_of(f)
    if d <= 0:
        continue
    seg = cc.VideoSegment(f, cc.trange(f"{t:.6f}s", f"{d:.6f}s"))
    script.add_segment(seg)
    t += d
    ok += 1
script.save()
print(f"draft '{NAME}' written: {ok} segments, {t:.1f}s -> {DRAFTS}")
