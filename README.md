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

Keep project footage and references in local directories configured by the
project's input manifests. Raw footage, generated media and editor projects
are not supplied by the engine package.

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

Install the exact ECC engine pinned for this example:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements-tasteforge.txt
python3 -m tasteforge --help
python3 -m unittest discover -s tests
```

Project footage references use `footage://` paths. Set `ITO_FOOTAGE_ROOT` (or
`--footage-root`) to the directory containing the source footage folders;
the default is `assets/raw`. Use a new output path for regenerated manifests,
or explicitly pass `--overwrite` to replace an existing generated result.
CapCut always requires a fresh draft name. Original media is never an output
destination.

Project-specific assembly remains in `build_ito.py`, `edl.json`, `script.md`
and `storyboard.md`. Configure local source files before rendering. Reusable
media effects, still animation and editor export helpers are imported from ECC;
the scripts here supply this project's defaults and preserve their entry points.

## TasteForge engine ownership

ECC owns the reusable engine: interviews, schema and strict multimodal
contracts, style-pack validation, offline distillation and cadence planning,
asset provenance, EDL/FCPXML export, and the verified Resolve adapter.
`Ito-Markets/ito-video` is an example project consuming that installed package.
There is no second `tasteforge/` runtime in this repository.

The existing `python3 -m tasteforge` CLI works from this project or any directory
after installation. Offline commands refuse provider execution. Actual
reference measurement and explicitly authorized generation use ECC's original
`taste-distillation` and `taste-application` skills.

For a local ECC package extracted from an npm tarball, install it instead of the
Git pin with `python3 -m pip install /path/to/package/skills/taste-application/scripts`.
The engine's operator guide is bundled as `tasteforge/README.md` in the Python
package. See [PROVENANCE.md](PROVENANCE.md) for sanitized source lineage.

## Notes

- `assets/raw/` is gitignored; copy or symlink source clips here.
- Rendered outputs remain local under `out/`; supported media extensions are gitignored.
- Keys are read from `.env.hermes` (gitignored).
