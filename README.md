# ItoMarkets Brand Film — `ito-video`

Institutional brand film for ItoMarkets, built in-house with the same Python + FFmpeg + Remotion + CapCut pipeline as the Shenzhen MV project.

## Goal

~90–120 second brand film that positions ItoMarkets as the ETF layer for prediction markets.
Tone: classy, serious, historical, high-finance (Rolex / Anthropic brand-film references).
Not consumer/gambling. Not hype.

## Core motifs

- History of financial instruments: first ETF launched on the Toronto Stock Exchange
- Mathematical lineage: Al-Khwarizmi, Euler, Riemann, Itō, Jim Simons
- Greek mythology: Atlas holding the world of markets
- Wall Street / New York City institutional presence
- Prediction markets as the new primitive; ItoMarkets as the basket/ETF layer

## Source material

- Local footage in `/Users/affoon/Downloads/`:
  - `allrawfootageunsorted/` — raw iPhone, DJI, Meta Ray-Ban POV, screen recordings
  - `clipsfortaste/` — taste/reference clips
  - `itovault/ito_vid.mp4` — existing ItoMarkets video
  - `rawtalkingclips/` — talking-head clips of founders
- Historical/archival footage from deep research + web scraping
- Generated assets: ElevenLabs voiceover, fal.ai b-roll, Manim/Blender math animations

## Pipeline

```text
edl.json (pool of selects)
  -> make_sheets.sh (contact sheets/proxies)
  -> build_ito.py (narrative scheduler, 1920x1080, zero-repeat)
  -> fx_*.py (subtle transitions, data-viz, Manim/Blender passes)
  -> export_capcut.py (CapCut draft for final polish)
```

## Key files

| File | Purpose |
|------|---------|
| `edl.json` | Pool of selects with in/out, rating, section, grade, notes |
| `build_ito.py` | Narrative assembly scheduler |
| `make_sheets.sh` | Generate contact sheets for review |
| `fx_glitch.py` | Subtle datamosh/pixelsort/feedback effects (reused from Shenzhen) |
| `export_capcut.py` | Export assembled timeline to CapCut |
| `gen/manim_geo.py` | Manim math/geometry animations |
| `storyboard.md` | Beat-by-beat visual plan |
| `script.md` | Voiceover script |

## Quickstart

```bash
source venv/bin/activate
bash make_sheets.sh /Users/affoon/Downloads/rawtalkingclips/*.mov
python3 build_ito.py
python3 export_capcut.py
```

## Notes

- `assets/raw/` is gitignored; copy or symlink source clips here.
- `out/` is gitignored; rendered outputs live here.
- Keys are read from `.env.hermes` (gitignored).
