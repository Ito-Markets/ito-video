#!/usr/bin/env python3
"""
build_edl.py — generate a curated edl.json for the ItoMarkets brand film.
Pulls from local footage and generated assets.
"""
import json, os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))


def dur(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out or 0)
    except Exception:
        return 0


def clip(id, src, t_in, t_out, section, family, rating, subject, grade, note):
    return {
        "id": id,
        "src": src,
        "in": t_in,
        "out": t_out,
        "speed": 1.0,
        "section": section,
        "family": family,
        "rating": rating,
        "subject": subject,
        "grade": grade,
        "note": note
    }


def main():
    pool = []

    # Generated still clips
    stills = [
        ("h_euler", "assets/gen/still_euler.mp4", "history", "math", 5, "euler", ["mono", "gold"], "Euler portrait"),
        ("h_alkhwarizmi", "assets/gen/still_alkhwarizmi.mp4", "history", "math", 4, "alkhwarizmi", ["mono", "gold"], "Al-Khwarizmi"),
        ("h_riemann", "assets/gen/still_riemann.mp4", "history", "math", 5, "riemann", ["mono", "cool"], "Riemann portrait"),
        ("h_ito", "assets/gen/still_ito.mp4", "history", "math", 5, "ito", ["mono", "cool"], "Ito Kiyoshi"),
        ("h_simons", "assets/gen/still_simons.mp4", "history", "math", 4, "simons", ["crush_black"], "Jim Simons"),
        ("c_atlas", "assets/gen/still_atlas.mp4", "close", "myth", 5, "atlas", ["gold"], "Atlas Farnese"),
        ("c_globe", "assets/gen/still_globe.mp4", "close", "myth", 4, "globe", ["gold"], "Atlas globe"),
    ]
    for id, src, sec, fam, rating, sub, grade, note in stills:
        if os.path.exists(os.path.join(BUILD, src)):
            pool.append(clip(id, src, 0.0, dur(os.path.join(BUILD, src)), sec, fam, rating, sub, grade, note))

    # Generated Manim clips
    manim = [
        ("m_sacred", "assets/gen/sacred_geo.mp4", "history", "geometry", 4, ["crush_black", "gold"], "Sacred geometry"),
        ("m_basket", "assets/gen/basket.mp4", "history", "geometry", 4, ["crush_black", "gold"], "Basket convergence"),
        ("m_web", "assets/gen/market_web.mp4", "solution", "network", 4, ["cool"], "Market network"),
    ]
    for id, src, sec, fam, rating, grade, note in manim:
        if os.path.exists(os.path.join(BUILD, src)):
            pool.append(clip(id, src, 0.0, dur(os.path.join(BUILD, src)), sec, fam, rating, fam, grade, note))

    # ItoMarkets existing brand video
    ito_vid = "/Users/affoon/Downloads/itovault/ito_vid.mp4"
    if os.path.exists(ito_vid):
        d = dur(ito_vid)
        pool.append(clip("p_ito", ito_vid, 0.0, min(d, 8.0), "solution", "product", 4, "product", ["crush_black"], "ito brand video"))

    # Talking clips
    talking = [
        ("/Users/affoon/Downloads/rawtalkingclips/2026-05-26 01-31-25.mov", "founder1"),
        ("/Users/affoon/Downloads/rawtalkingclips/IMG_0212.MOV", "founder2"),
        ("/Users/affoon/Downloads/rawtalkingclips/IMG_4763.MOV", "founder3"),
    ]
    for i, (path, label) in enumerate(talking):
        if os.path.exists(path):
            d = dur(path)
            pool.append(clip(f"f_{label}", path, 0.0, min(d, 6.0), "solution", "founder", 3, "founder", ["crush_black"], f"talking clip {label}"))

    # Screen recordings / taste clips
    screens = [
        ("/Users/affoon/Downloads/clipsfortaste/ScreenRecording_06-07-2026 07-55-27_1.mp4", "screen1", "problem"),
        ("/Users/affoon/Downloads/clipsfortaste/ScreenRecording_06-07-2026 08-04-44_1.mp4", "screen2", "problem"),
        ("/Users/affoon/Downloads/clipsfortaste/ScreenRecording_06-07-2026 08-53-06_1.mp4", "screen3", "problem"),
        ("/Users/affoon/Downloads/clipsfortaste/ScreenRecording_06-07-2026 09-29-14_1.mp4", "screen4", "product"),
        ("/Users/affoon/Downloads/clipsfortaste/ScreenRecording_06-07-2026 09-38-13_1.mp4", "screen5", "product"),
    ]
    for path, label, sec in screens:
        if os.path.exists(path):
            d = dur(path)
            pool.append(clip(f"s_{label}", path, 0.0, min(d, 5.0), sec, "screen", 3, "screen", ["crush_black"], f"screen recording {label}"))

    # Free stock footage downloads
    stock = [
        ("assets/raw/dareful_nyse_entrance.mp4", "nyse_entrance", "open", 4),
        ("assets/raw/vidsplay_stock_exchange.mp4", "stock_exchange", "history", 4),
        ("assets/raw/vidsplay_business_graph.mp4", "business_graph", "product", 3),
        ("assets/raw/vidsplay_office_building.mp4", "office_building", "close", 3),
    ]
    for src, label, sec, rating in stock:
        path = os.path.join(BUILD, src)
        if os.path.exists(path):
            d = dur(path)
            pool.append(clip(f"st_{label}", src, 0.0, min(d, 5.0), sec, "stock", rating, "broll", ["crush_black"], f"free stock {label}"))

    # Raw footage selects — small subset of the best/unknown
    raw = [
        ("/Users/affoon/Downloads/allrawfootageunsorted/ito_markets_intro.mp4", "ito_intro", "open"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/video-75_singular_display.mov", "pov1", "open"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/video-235_singular_display.mov", "pov2", "open"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/dji_export_20260604_094245_1780580565393_compose_0.mov", "drone1", "close"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/dji_export_20260604_101202_1780582322354_compose_0.mov", "drone2", "close"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/IMG_0225.MOV", "city1", "open"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/IMG_0590.MOV", "city2", "open"),
        ("/Users/affoon/Downloads/allrawfootageunsorted/IMG_3842.MOV", "city3", "close"),
    ]
    for path, label, sec in raw:
        if os.path.exists(path):
            d = dur(path)
            pool.append(clip(f"r_{label}", path, 0.0, min(d, 5.0), sec, "clip", 3, "broll", ["crush_black"], f"raw footage {label}"))

    edl = {
        "project": "itomarkets-brand-film",
        "fps": 30,
        "canvas": [1920, 1080],
        "grade_base": "ito: deep contrast, warm-neutral highlights, cool shadows, subtle grain",
        "pool": pool
    }
    with open(os.path.join(BUILD, "edl.json"), "w") as fh:
        json.dump(edl, fh, indent=1)
    print(f"wrote edl.json with {len(pool)} selects")


if __name__ == "__main__":
    main()
