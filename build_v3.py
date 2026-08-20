#!/usr/bin/env python3
"""
build_v3.py — Assemble the sub-30s Ito brand film v3.

Takes clips from clips_v3/ and assembles them into a fast-cut montage
with xfade transitions, audio (voiceover + music bed), and final mix.

Structure (30s total, ~1-1.5s per shot):
  0.0s  - Gold screen art reveal
  1.2s  - Red Fuji (Hokusai)
  2.4s  - Ito portrait
  3.6s  - Data buffer flash
  4.6s  - Card: "Hedge geopolitical risk."
  6.1s  - UI: Index dashboard
  7.1s  - UI: Trading modal
  8.1s  - Euler portrait
  9.1s  - Stochastic paths (Manim)
 10.3s  - Card: "Trade thematic repricing."
 11.5s  - UI: AI Technology index
 12.5s  - Riemann portrait
 13.5s  - Winter Fuji art
 14.5s  - UI: Custom baskets
 15.5s  - Card: "Construct custom baskets."
 17.0s  - UI: Dashboard strategies
 18.0s  - Al-Khwarizmi portrait
 19.0s  - Mudcloth pattern
 19.8s  - Gold particles
 20.8s  - Simons portrait
 21.8s  - UI: All indices
 22.8s  - Peony garden screen
 23.8s  - Ito lemma (Manim)
 25.0s  - SDE (Manim)
 26.2s  - UI: Logo shot
 27.2s  - Endcard
 29.7s  - END
"""
import os
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIPS = ROOT / "clips_v3"
GEN = ROOT / "assets" / "gen"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

XFADE_DUR = 0.15  # fast, punchy crossfades

# Edit sequence: (clip_filename, duration_seconds)
# Total target: ~28-30s with xfade overlaps (~3.5s eaten by 23 x 0.15s xfades)
EDIT_SEQUENCE = [
    # -- OPEN: art + identity (0-5s)
    ("art_gold_screen.mp4", 1.5),        # gold leaf screen pan
    ("art_fuji_red.mp4", 1.2),           # Hokusai Red Fuji
    ("portrait_ito.mp4", 1.5),           # Kiyoshi Ito portrait
    # -- MATH + DATA (5-11s)
    ("data_buffer.mp4", 1.0),            # flashing hex data
    ("manim_stochastic_paths.mp4", 1.5), # Brownian motion paths
    ("portrait_euler.mp4", 1.0),         # Euler
    ("manim_ito_lemma.mp4", 1.5),        # Ito's lemma formula
    # -- HEDGE (11-15s)
    ("card_hedge.mp4", 1.5),             # "Hedge geopolitical risk."
    ("ui_dash.mp4", 1.0),               # Index dashboard
    ("ui_trade.mp4", 1.0),              # Trading modal
    # -- TRADE (15-19s)
    ("card_trade.mp4", 1.5),             # "Trade thematic repricing."
    ("ui_ai_index.mp4", 1.0),           # AI Technology index
    ("portrait_riemann.mp4", 1.0),       # Riemann
    ("art_winter_fuji.mp4", 1.0),        # Winter Fuji
    # -- CONSTRUCT (19-24s)
    ("card_construct.mp4", 1.5),         # "Construct custom baskets."
    ("ui_baskets.mp4", 1.0),            # Custom baskets UI
    ("ui_strategies.mp4", 1.0),         # Dashboard strategies
    ("portrait_alkhwarizmi.mp4", 1.0),   # Al-Khwarizmi
    # -- CLOSE (24-30s)
    ("manim_sde_reveal.mp4", 1.5),       # SDE formula
    ("particles.mp4", 1.0),             # Gold particles
    ("portrait_simons.mp4", 1.0),        # Jim Simons
    ("art_peony.mp4", 1.0),             # Peony garden screen
    ("ui_indices.mp4", 1.0),            # All indices
    ("endcard.mp4", 3.0),               # Logo + tagline + URL
]


def get_clip_path(name: str) -> str:
    """Find clip in clips_v3/ or assets/gen/ (for manim clips)."""
    p = CLIPS / name
    if p.exists():
        return str(p)
    p = GEN / name
    if p.exists():
        return str(p)
    # Manim outputs are prefixed with manim_
    if not name.startswith("manim_"):
        p = GEN / f"manim_{name}"
        if p.exists():
            return str(p)
    return ""


def trim_clip(src: str, duration: float, output: str):
    """Trim clip to exact duration, re-encoding for consistent format."""
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", src,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-s", "1920x1080",
        "-an",
        output,
    ]
    subprocess.run(cmd, check=True)


def xfade_assemble(trim_paths: list, durations: list, xfade_dur: float, output: str):
    """Use ffmpeg xfade filter chain for smooth crossfade transitions."""
    n = len(trim_paths)
    if n == 0:
        return
    if n == 1:
        shutil.copy2(trim_paths[0], output)
        return

    inputs = []
    for p in trim_paths:
        inputs.extend(["-i", p])

    filters = []
    cumulative = 0.0
    for i in range(n - 1):
        offset = cumulative + durations[i] - xfade_dur
        cumulative = offset

        src_a = "[0:v]" if i == 0 else f"[v{i - 1}{i}]"
        src_b = f"[{i + 1}:v]"
        out_label = f"[v{i}{i + 1}]" if i < n - 2 else "[vout]"

        filters.append(
            f"{src_a}{src_b}xfade=transition=fade:duration={xfade_dur:.2f}:"
            f"offset={offset:.3f}{out_label}"
        )

    fc = ";".join(filters)
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", fc,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30",
        output,
    ]
    print(f"  xfade assembly: {n} clips...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  xfade failed: {r.stderr[:300]}")
        concat_fallback(trim_paths, output)
    else:
        print(f"  xfade OK")


def concat_fallback(paths: list, output: str):
    """Simple concat demuxer fallback."""
    concat_file = str(OUT / "v3_concat.txt")
    with open(concat_file, "w") as f:
        for p in paths:
            f.write(f"file '{p}'\n")
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30",
        output,
    ]
    subprocess.run(cmd, check=True)
    print(f"  concat fallback OK")


def mix_audio(video: str, voice: str, music: str, output: str):
    """Mix voiceover + music with sidechain ducking onto video.
    Truncates all audio to video duration for tight sync."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True,
    )
    vid_dur = float(probe.stdout.strip()) if probe.returncode == 0 and probe.stdout.strip() else 30.0
    fade_out_start = max(0, vid_dur - 3)

    # atrim truncates both audio streams to video duration
    fc = (
        f"[0:v]copy[v];"
        f"[1:a]atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS,volume=1.0,asplit[vo][vo_sc];"
        f"[2:a]atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS,volume=-14dB,"
        f"afade=t=in:ss=0:d=1.5,"
        f"afade=t=out:st={fade_out_start:.1f}:d=3[mu_raw];"
        f"[mu_raw][vo_sc]sidechaincompress=threshold=0.02:ratio=4:attack=50:release=300:level_sc=1[mu];"
        f"[vo][mu]amix=inputs=2:duration=shortest:dropout_transition=1:weights=1 0.5[a]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", video, "-i", voice, "-i", music,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-movflags", "+faststart", output,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  sidechain failed, trying simple mix: {r.stderr[:200]}")
        fc_simple = (
            f"[0:v]copy[v];"
            f"[1:a]atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS,volume=1.0[vo];"
            f"[2:a]atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS,volume=-16dB,"
            f"afade=t=in:ss=0:d=1.5,"
            f"afade=t=out:st={fade_out_start:.1f}:d=3[mu];"
            f"[vo][mu]amix=inputs=2:duration=shortest:dropout_transition=1:weights=1 0.5[a]"
        )
        cmd2 = [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-i", video, "-i", voice, "-i", music,
            "-filter_complex", fc_simple,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-movflags", "+faststart", output,
        ]
        subprocess.run(cmd2, check=True)
    else:
        print("  sidechain ducking OK")


def main():
    print("=== Building Ito Brand Film v3 ===\n")

    # 1. Collect and trim clips
    print("[1/3] Trimming clips...")
    trim_dir = OUT / "v3_trims"
    trim_dir.mkdir(exist_ok=True)

    trim_paths = []
    durations = []
    skipped = []

    for idx, (name, dur) in enumerate(EDIT_SEQUENCE):
        src = get_clip_path(name)
        if not src:
            print(f"  SKIP #{idx}: {name} not found")
            skipped.append(name)
            continue

        trimmed = str(trim_dir / f"t{idx:02d}_{name}")
        trim_clip(src, dur, trimmed)
        trim_paths.append(trimmed)
        durations.append(dur)
        print(f"  #{idx:02d} {name} ({dur}s)")

    if skipped:
        print(f"\n  Skipped {len(skipped)} clips: {skipped}")

    # 2. Assemble with xfade
    print(f"\n[2/3] Assembling {len(trim_paths)} clips with xfade...")
    rough_cut = str(OUT / "rough_cut_v3.mp4")
    xfade_assemble(trim_paths, durations, XFADE_DUR, rough_cut)

    # Check duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", rough_cut],
        capture_output=True, text=True,
    )
    dur = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    print(f"  Rough cut: {dur:.1f}s")

    # 3. Mix audio
    voice = str(ROOT / "assets" / "gen" / "voiceover.mp3")
    music = str(ROOT / "assets" / "gen" / "music_bed_v2.mp3")
    final = str(OUT / "ito_brand_film_v3.mp4")

    if os.path.exists(voice) and os.path.exists(music):
        print(f"\n[3/3] Mixing audio (voiceover + music)...")
        mix_audio(rough_cut, voice, music, final)
    else:
        print(f"\n[3/3] No audio sources found, video-only output...")
        shutil.copy2(rough_cut, final)

    sz = os.path.getsize(final) / 1024 / 1024
    print(f"\n=== DONE: {final} ({sz:.1f} MB, {dur:.1f}s) ===")


if __name__ == "__main__":
    main()
