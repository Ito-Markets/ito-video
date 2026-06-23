#!/usr/bin/env python3
"""
assemble_final.py — combine rough_cut.mp4 + voiceover + music bed into final brand film.
v2 changes:
- Uses refined music_bed_v2.mp3 (layered cinematic composition)
- Sidechain-style ducking: music dips during voiceover
- Better mix levels: voiceover dominant, music subtle but present
- Proper fade envelope on music
- Output as ito_brand_film_v2.mp4
"""
import os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(BUILD, "out", "rough_cut.mp4")
VOICE = os.path.join(BUILD, "assets", "gen", "voiceover.mp3")
MUSIC_V2 = os.path.join(BUILD, "assets", "gen", "music_bed_v2.mp3")
MUSIC_V1 = os.path.join(BUILD, "assets", "gen", "music_bed.mp3")
OUT = os.path.join(BUILD, "out", "ito_brand_film_v2.mp4")


def main():
    if not os.path.exists(VIDEO):
        raise FileNotFoundError(VIDEO)
    if not os.path.exists(VOICE):
        raise FileNotFoundError(VOICE)

    music = MUSIC_V2 if os.path.exists(MUSIC_V2) else MUSIC_V1
    if not os.path.exists(music):
        raise FileNotFoundError(f"No music bed found: tried {MUSIC_V2} and {MUSIC_V1}")

    # Get video duration for proper fade timing
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", VIDEO],
        capture_output=True, text=True,
    )
    vid_dur = float(probe.stdout.strip()) if probe.stdout.strip() else 90.0

    # v2: Sidechain ducking mix
    # - Voiceover at full volume
    # - Music bed at -20dB normally, ducked further when VO is active via sidechaincompress
    # - Music fades in over 4s, fades out starting 8s before end
    fade_out_start = max(0, vid_dur - 8)
    fc = (
        f"[0:v]copy[v];"
        f"[1:a]volume=1.0,apad=whole_dur={vid_dur}[vo];"
        f"[2:a]volume=-18dB,"
        f"afade=t=in:ss=0:d=4,"
        f"afade=t=out:st={fade_out_start:.1f}:d=8,"
        f"apad=whole_dur={vid_dur}[mu_raw];"
        f"[mu_raw][vo]sidechaincompress=threshold=0.02:ratio=4:attack=50:release=300:level_sc=1[mu];"
        f"[vo][mu]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.6[a]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", VIDEO, "-i", VOICE, "-i", music,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-movflags", "+faststart", OUT,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"sidechaincompress failed, falling back to simple mix: {r.stderr[:200]}")
        # Fallback: simple mix without sidechain
        fc_simple = (
            f"[0:v]copy[v];"
            f"[1:a]volume=1.0,apad=whole_dur={vid_dur}[vo];"
            f"[2:a]volume=-20dB,"
            f"afade=t=in:ss=0:d=4,"
            f"afade=t=out:st={fade_out_start:.1f}:d=8,"
            f"apad=whole_dur={vid_dur}[mu];"
            f"[vo][mu]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.5[a]"
        )
        cmd_simple = [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-i", VIDEO, "-i", VOICE, "-i", music,
            "-filter_complex", fc_simple,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-movflags", "+faststart", OUT,
        ]
        subprocess.run(cmd_simple, check=True)

    sz = os.path.getsize(OUT)
    print(f"wrote {OUT} ({sz / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
