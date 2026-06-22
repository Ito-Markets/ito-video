#!/usr/bin/env python3
"""
gen_music_bed.py — generate a simple cinematic ambient bed for the brand film.
Uses ffmpeg to create a low drone + subtle texture. Replace with licensed music for final.
"""
import os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BUILD, "assets", "gen", "music_bed.mp3")
DUR = 76.0


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Low drone: 62 Hz + 93 Hz with slow amplitude modulation, reverb, low-pass
    fc = (
        f"aevalsrc=0.15*sin(2*PI*62*t)+0.08*sin(2*PI*93*t)+0.05*sin(2*PI*124*t):"
        f"c=stereo:s=48000:nb_samples=1024,"
        f"volume='0.18+0.04*sin(2*PI*0.07*t)':eval=frame,"
        f"afade=t=in:ss=0:d=4,afade=t=out:st={DUR-6}:d=6,"
        f"treble=g=-12:f=3000,lowpass=f=800,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", fc,
        "-t", f"{DUR:.2f}",
        "-c:a", "libmp3lame", "-q:a", "2", "-ar", "48000", OUT
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
