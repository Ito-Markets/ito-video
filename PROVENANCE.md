# TasteForge provenance and generation lineage

This repository's `tasteforge/` package canonicalizes a recovered TasteForge /
FAL-video workflow so it is repeatable, inspectable, and testable. This file
records exactly where the recovered material came from, what was kept, and
what was deliberately left out of Git.

## Canonical recovered source (read-only)

`/Users/affoon/Movies/Ito/tasteforge-flow-20260818`

- Same-filesystem relocation of a cross-device copy; per-file path, byte
  count, and SHA-256 manifests matched at copy time (copy verification
  digest `dbb3fcd05dc08ab06739b26e5f313fbe14303d93d9d7b7938b7aa5981306e888`).
- Contains screen recordings of the original flow (`Documents/*.mp4`),
  recovered outputs (`FINAL_canvas.mp4`, proof/contact sheets), and five
  implementation archive generations under `Downloads/`.
- It is a source of record, not a working tree: nothing in this repo writes
  there, and the raw media never enters Git.

## Implementation archives (generation lineage)

Recovered under `Downloads/` in the canonical source. Each generation is a
zip of the working implementation at successive points; behavior below is
inferred from version deltas, source, and outputs.

| Archive | SHA-256 | Status | Delta from previous |
|---|---|---|---|
| `tasteforge.zip` | `a504480ce1963370f47ac7fc338c97f561fa762c0bb60218c88c667b8b215c9c` | prior (gen 0) | Initial pipeline: mint/distill/apply/resolve_ingest stages; `taste` package (pack, frames, grade, cadence, falapi, timeline); single-reference `flashethereal` pack with LUT, grade, cadence, 9 stills. |
| `tasteforge (1).zip` | `ef7ff52da211e63ab538818f36b22ddc736b4cecaf4f31c98bd7e9205c109a99` | prior (gen 1) | Added `grounding.txt` (measured-ground-truth VLM preamble); adaptive threshold sweep + shared-stats single-decode in cadence; content masking / outlier rejection in frames and grade; references grew to 3 (14 stills). |
| `tasteforge (2).zip` | `0d227f27750805ecf88d29bf00a7f1d6605b287c5750a05fe3f3ea84fe2c3534` | prior (gen 2) | distill gains strict-JSON retry, spec validation and repair; apply gains take grouping (`plan_takes`) and prompt refinements; first prop mesh (GLB) minted. |
| `tasteforge (3).zip` | `2f3a10d95c3c9c02da390a2f1cb9f21499b88de2650e813f66cabe9346a41875` | prior (gen 3) | Regenerated EDL/FCPXML cut outputs from the distilled cadence; grade fixes in LUT baking. |
| `tasteforge (4).zip` | `ef06a606d3b528fbd939b05fadc25bf6674073a1e05a01e3aa6b9c9416fd6284` | **latest (gen 4)** | grade adds `_post_tone_anchor`: a baked 3D LUT reconstructs source luminance quantiles from the stored CDF instead of stretching a uniform lattice; pack.json / spec.json / look.cube regenerated. |

The latest generation is the implementation canonicalized here. Earlier
generations were inspected to reconstruct intent and avoid regressions; they
are not vendored.

## Claude cloud session

- Session ID (user-supplied, confirmed by local metadata as the selected
  video/taste-flow session): `cse_01Tmgz8ezNwk64Zx7MUgsiUy`.
- The full transcript is **not** available locally. Nothing in this repo
  claims otherwise: all behavior above is inferred from version deltas,
  source code, tests, manifests, and recovered outputs — never invented.

## What ships in this repo

`tasteforge/fixtures/flashethereal/` carries six metadata files selected from
the latest generation, byte-identical to the archive copies (verified by
SHA-256 at canonicalization time):

- `pack.json`, `grade.json`, `cadence.json`, `spec.json`, `grounding.txt`,
  and `flashethereal-cut.edl`

Deliberately excluded from Git (recoverable from the canonical source):

- `look.cube` (970 KB binary LUT), all `stills/*.png` (14 files),
  `props/*.glb` meshes, `plates/`, `__pycache__/`, `.ruff_cache/`,
  `.DS_Store`, and every recovered video (`Documents/*.mp4`,
  `FINAL_canvas.mp4`, proof/contact PNGs).
- Reference media paths inside `pack.json` (`refs/*.mov`) do not resolve in
  this repo; they are provenance, not assets.

## Provider boundary (read this before touching Fal)

- The recovered implementation called Fal endpoints (VLM distillation,
  image-to-3D, reference-to-video, hosted ffmpeg). In this package those are
  **optional adapters that fail closed**: the registry ships empty, provider
  lookup raises before any network-capable import, and no credentials are
  read anywhere.
- The existence of a local Fal reference (endpoint id, dry-run URL, endpoint
  name in `pack.json`) is **never** evidence that a Fal-side workflow was
  saved, persisted, or is authorized to run. See
  `tasteforge/provenance.provider_reference()`, which encodes a reference as
  pointer-only.
- Any live provider execution requires explicit separately authorized
  execution outside this package; `distill --live` and `apply --live` exit
  with code 2 and refuse.
