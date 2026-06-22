#!/usr/bin/env python3
"""
assemble_final.py — combine rough_cut.mp4 + voiceover + music bed into final brand film.
"""
import os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(BUILD, "out", "rough_cut.mp4")
VOICE = os.path.join(BUILD, "assets", "gen", "voiceover.mp3")
MUSIC = os.path.join(BUILD, "assets", "gen", "music_bed.mp3")
OUT = os.path.join(BUILD, "out", "ito_brand_film_v1.mp4")


def main():
    if not os.path.exists(VIDEO):
        raise FileNotFoundError(VIDEO)
    if not os.path.exists(VOICE):
        raise FileNotFoundError(VOICE)
    if not os.path.exists(MUSIC):
        raise FileNotFoundError(MUSIC)

    # Mix voiceover full, music bed at -22dB, duck music slightly during voiceover if desired
    # For first pass: simple mix with music bed low and ducking via sidechain not required
    fc = (
        f"[0:v]copy[v];"
        f"[1:a]volume=1.0[vo];"
        f"[2:a]volume=-22dB,afade=t=in:ss=0:d=4,afade=t=out:st=70:d=6[mu];"
        f"[vo][mu]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", VIDEO, "-i", VOICE, "-i", MUSIC,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-movflags", "+faststart", OUT,
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
