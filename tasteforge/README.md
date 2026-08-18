# TasteForge — repeatable taste-driven video workflow

A stdlib-only Python package (no numpy/opencv/network dependencies) that
canonicalizes the recovered TasteForge flow into maintained, testable
tooling. Provider integrations (Fal) are optional adapters that **fail
closed**; every command here runs offline and deterministically. See
`PROVENANCE.md` at the repo root for the recovered-source lineage.

## Install

None required: Python 3.11+ standard library only. Run from the repo root.

## CLI

```bash
python3 -m tasteforge provenance                     # recovered-source lineage as JSON
python3 -m tasteforge inspect <pack-dir>             # validate + summarize a style pack
python3 -m tasteforge validate <pack-dir>            # exit 0 valid / 1 invalid
python3 -m tasteforge interview --answers a.json --genre NAME [--out profile.json]
python3 -m tasteforge distill --profile profile.json [--pack <pack-dir>] [--out spec.json]
python3 -m tasteforge apply --pack <pack-dir> --media media.json [--duration 20] [--out report.json]
python3 -m tasteforge export --events events.json [--out-dir out] [--fps 24] [--title cut]
```

`--live` on `distill`/`apply` is refused (exit 2): provider generation
requires explicit separately authorized execution outside this package.

Input shapes:

- answers: `{"<question-id>": "<free text>", ...}` — ids are listed by
  `tasteforge.interview.QUESTIONS` (palette, grain, lighting, focal_length,
  camera_motion, subject_framing, grade_description, mood_adjectives, avoid,
  brief).
- media/events: `{"clips": [{"path": "...", "duration": 6.2, "name": "..."}]}`.

Outputs:

- `interview` → taste profile (schema `TASTE_PROFILE_SCHEMA`)
- `distill` → style spec (schema `SPEC_SCHEMA`, always `dry_run: true`,
  `provider: "none"`) with measured grounding embedded when a pack is given
- `apply` → application report (schema `APPLICATION_REPORT_SCHEMA`; provider
  enum-locked to `"none"`) with planned shots and frame-exact timeline events
- `export` → CMX3600 `<title>.edl` + FCPXML 1.9 `<title>.fcpxml` with
  rational, frame-quantised times (NTSC-safe)

## Offline fixture

`tasteforge/fixtures/flashethereal/` is recovered pack metadata
(`pack.json`, `grade.json`, `cadence.json`, `spec.json`, `grounding.txt`,
`flashethereal-cut.edl`), byte-identical
to the latest recovered generation. It exercises the full offline path with
no provider and no media.

```bash
python3 -m tasteforge inspect tasteforge/fixtures/flashethereal
```

## Library

```python
from tasteforge import pack, interview, distill, apply, export, provenance, schema

sp = pack.load("tasteforge/fixtures/flashethereal")
report = apply.apply_local(sp, [{"path": "a.mov", "duration": 5.0}])
edl, fcpxml = export.write_timeline(report["timeline_events"], out_dir="out")
```

## Tests, lint, types

```bash
python3 -m unittest discover -s tests -v   # full suite (offline, deterministic)
ruff check tasteforge tests                # lint (pip install ruff)
mypy tasteforge                            # types (pip install mypy)
python3 -m compileall -q tasteforge        # syntax check
```

## Boundaries

- No network calls, no credentials, no provider account access — ever.
- A local Fal reference never means a provider workflow was saved; see
  `provenance.provider_reference()`.
- Raw recovered sources (videos, LUTs, stills, meshes) stay out of Git; the
  fixture is metadata-only and documented in `PROVENANCE.md`.
