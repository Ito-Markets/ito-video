#!/usr/bin/env python3
"""
stills_to_clips.py — turn static historical images into 1920x1080 Ken Burns clips.
Usage: python3 stills_to_clips.py
"""
import os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BUILD, "assets", "stills")
OUT = os.path.join(BUILD, "assets", "gen")
os.makedirs(OUT, exist_ok=True)

# image, duration, start crop, end crop, start center, end center
# all coordinates in relative 0..1
CLIPS = [
    ("euler.jpg",   4.0, (0.20, 0.10, 0.60, 0.80), (0.10, 0.00, 0.80, 1.00), "euler", "math"),
    ("riemann.jpg", 4.0, (0.25, 0.05, 0.50, 0.70), (0.15, 0.00, 0.70, 0.90), "riemann", "math"),
    ("ito.jpg",     4.0, (0.20, 0.05, 0.60, 0.75), (0.15, 0.00, 0.70, 0.90), "ito", "math"),
    ("al_khwarizmi.jpg", 4.0, (0.20, 0.05, 0.60, 0.80), (0.10, 0.00, 0.80, 0.95), "alkhwarizmi", "math"),
    ("jim_simons.jpg", 4.0, (0.25, 0.10, 0.50, 0.70), (0.15, 0.05, 0.70, 0.85), "simons", "solution"),
    ("atlas_farnese.jpg", 5.0, (0.20, 0.10, 0.60, 0.80), (0.30, 0.20, 0.40, 0.60), "atlas", "close"),
    ("atlas_globe.jpg", 5.0, (0.10, 0.05, 0.80, 0.90), (0.25, 0.15, 0.50, 0.70), "globe", "close"),
]


def crop_expr(crop):
    x, y, w, h = crop
    return f"crop=w=iw*{w}:h=ih*{h}:x=iw*{x}:y=ih*{y}"


def make_clip(img, dur, start_crop, end_crop, name, section):
    inp = os.path.join(SRC, img)
    out = os.path.join(OUT, f"still_{name}.mp4")
    if not os.path.exists(inp):
        print(f"missing {inp}")
        return None
    fc = (
        f"[0:v]scale=2560:1440:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,"
        f"zoompan=z='min(zoom+0.0005,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur*30)}:s=1920x1080:fps=30,"
        f"format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-loop", "1", "-i", inp,
        "-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.2f}",
        "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {name}: {r.stderr.strip()[:120]}")
        return None
    print(f"OK {out} {dur:.1f}s")
    return out


def main():
    for img, dur, sc, ec, name, section in CLIPS:
        make_clip(img, dur, sc, ec, name, section)


if __name__ == "__main__":
    main()
