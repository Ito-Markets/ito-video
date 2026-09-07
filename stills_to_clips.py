#!/usr/bin/env python3
"""Ito historical-image selections; rendering is provided by installed ECC."""

import argparse
from pathlib import Path

from tasteforge.media.stills import make_clip as render_clip

BUILD = Path(__file__).resolve().parent
SRC = BUILD / "assets" / "stills"
OUT = BUILD / "assets" / "gen"

CLIPS = [
    (
        "euler.jpg",
        4.0,
        (0.20, 0.10, 0.60, 0.80),
        (0.10, 0.00, 0.80, 1.00),
        "euler",
        "math",
    ),
    (
        "riemann.jpg",
        4.0,
        (0.25, 0.05, 0.50, 0.70),
        (0.15, 0.00, 0.70, 0.90),
        "riemann",
        "math",
    ),
    ("ito.jpg", 4.0, (0.20, 0.05, 0.60, 0.75), (0.15, 0.00, 0.70, 0.90), "ito", "math"),
    (
        "al_khwarizmi.jpg",
        4.0,
        (0.20, 0.05, 0.60, 0.80),
        (0.10, 0.00, 0.80, 0.95),
        "alkhwarizmi",
        "math",
    ),
    (
        "jim_simons.jpg",
        4.0,
        (0.25, 0.10, 0.50, 0.70),
        (0.15, 0.05, 0.70, 0.85),
        "simons",
        "solution",
    ),
    (
        "atlas_farnese.jpg",
        5.0,
        (0.20, 0.10, 0.60, 0.80),
        (0.30, 0.20, 0.40, 0.60),
        "atlas",
        "close",
    ),
    (
        "atlas_globe.jpg",
        5.0,
        (0.10, 0.05, 0.80, 0.90),
        (0.25, 0.15, 0.50, 0.70),
        "globe",
        "close",
    ),
]


def make_clip(img, dur, start_crop, end_crop, name, section, **options):
    return render_clip(
        SRC / img,
        OUT / f"still_{name}.mp4",
        duration=dur,
        start_crop=start_crop,
        end_crop=end_crop,
        **options,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SRC)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=float, default=30)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for image, duration, start, end, name, _section in CLIPS:
        render_clip(
            args.source_dir / image,
            args.output_dir / f"still_{name}.mp4",
            duration,
            start,
            end,
            args.width,
            args.height,
            args.fps,
            args.overwrite,
        )


if __name__ == "__main__":
    main()
