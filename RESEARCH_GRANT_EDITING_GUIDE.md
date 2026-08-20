# Itô Research Grant — Post-Editing Guide

## Output package

- Reference cut: `out/ito_research_grant.mp4`
- Timeline manifest: `timeline/edl.json`
- Editable clips: `timeline/clips/*.mp4`
- Music stem: `timeline/audio/music_stem.mp3`
- Generator: `gen_research_grant.py`

## Reference assembly

The reference cut is 24.9s at 1920x1080, 30fps.

| Time | Clip | Purpose |
|---:|---|---|
| 0.0 | `001_void_gold_line.mp4` | Cold open: negative space + gold ignition line |
| 3.0 | `002_grant_title.mp4` | Itô Research Grant title |
| 5.5 | `003_problem.mp4` | “Most of the data is inaccessible.” |
| 8.5 | `005_offerings.mp4` | L2 orderbooks, basket indices, hosted backtesting |
| 12.0 | `006_brownian.mp4` | Brownian paths / math texture |
| 14.5 | `007_endpoints.mp4` | “23 endpoints.” hero card |
| 17.5 | `008_audience.mp4` | Researchers, students, quants, builders |
| 20.5 | `012_url.mp4` | Apply URL |
| 23.0 | `013_endcard.mp4` | Logo resolve |

Use 0.2s crossfades between clips if rebuilding manually.

## Extra clips available

The package also includes optional inserts not used in the 24.9s reference assembly:

- `004_scroll_texture.mp4` — Japanese silent-film scroll texture from Itô site
- `009_research_areas.mp4` — research area list
- `010_ito_portrait.mp4` — Kiyoshi Itô portrait texture
- `011_api_scopes.mp4` — API scopes card

## CapCut import

1. Import all `timeline/clips/*.mp4` files.
2. Sort by filename.
3. Place the reference assembly clips in the order above.
4. Add `timeline/audio/music_stem.mp3` under the clips.
5. Add 0.2s crossfades or hard cuts where you want more austerity.
6. Keep the grade monochrome + gold; avoid saturated colors.

## Regeneration

```bash
# Optional: point to the original music file if it is not in assets/music/
export ITO_RESEARCH_MUSIC_PATH=/path/to/onlyHope_KLICKAUD.mp3
python3 gen_research_grant.py
```

The script is repo-relative and rebuilds all clips, `timeline/edl.json`, `timeline/audio/music_stem.mp3`, and `out/ito_research_grant.mp4`.
