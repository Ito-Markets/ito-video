#!/usr/bin/env python3
"""
gen_music_v2.py — generate a refined cinematic ambient bed for the ItoMarkets brand film.
Layered composition: sub-bass pad + mid-range harmonic pad + high shimmer +
rhythmic pulse + subtle percussion texture. Much richer than v1's single drone.
Target: ~90s, orchestral/electronic hybrid, institutional tone.
"""
import os, subprocess, tempfile

BUILD = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BUILD, "assets", "gen", "music_bed_v2.mp3")
DUR = 92.0  # slightly longer than video to allow fade-out


def gen_layer(name, fc, dur):
    """Generate a single audio layer."""
    tmp = os.path.join(BUILD, "assets", "gen", f"_music_layer_{name}.wav")
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", fc,
        "-t", f"{dur:.2f}", "-ar", "48000", "-ac", "2", tmp,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL layer {name}: {r.stderr.strip()[:200]}")
        return None
    print(f"  layer {name} OK")
    return tmp


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    layers = []

    # Layer 1: Deep sub-bass pad (C1 ~32Hz + G1 ~49Hz) with slow LFO
    l1 = gen_layer("sub_bass", (
        f"aevalsrc="
        f"0.12*sin(2*PI*32.7*t)+0.06*sin(2*PI*49.0*t)+0.04*sin(2*PI*65.4*t)"
        f":c=stereo:s=48000,"
        f"volume='0.15+0.05*sin(2*PI*0.05*t)':eval=frame,"
        f"lowpass=f=120,treble=g=-18:f=2000,"
        f"afade=t=in:ss=0:d=6,afade=t=out:st={DUR-8}:d=8,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l1:
        layers.append(l1)

    # Layer 2: Mid-range harmonic pad (Am chord: A2+C3+E3) with stereo spread
    l2 = gen_layer("harmonic_pad", (
        f"aevalsrc="
        f"0.06*sin(2*PI*110*t)+0.05*sin(2*PI*130.8*t)+0.04*sin(2*PI*164.8*t)"
        f"+0.03*sin(2*PI*220*t)+0.02*sin(2*PI*329.6*t)"
        f":c=stereo:s=48000,"
        f"volume='0.10+0.04*sin(2*PI*0.08*t)':eval=frame,"
        f"lowpass=f=800,highpass=f=80,"
        f"afade=t=in:ss=0:d=8,afade=t=out:st={DUR-10}:d=10,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l2:
        layers.append(l2)

    # Layer 3: High shimmer (ethereal overtones, very quiet)
    l3 = gen_layer("shimmer", (
        f"aevalsrc="
        f"0.02*sin(2*PI*880*t+sin(2*PI*0.3*t))"
        f"+0.015*sin(2*PI*1320*t+cos(2*PI*0.2*t))"
        f"+0.01*sin(2*PI*1760*t+sin(2*PI*0.15*t))"
        f":c=stereo:s=48000,"
        f"volume='0.06+0.03*sin(2*PI*0.12*t)':eval=frame,"
        f"highpass=f=400,lowpass=f=4000,"
        f"afade=t=in:ss=0:d=10,afade=t=out:st={DUR-8}:d=8,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l3:
        layers.append(l3)

    # Layer 4: Rhythmic pulse (subtle heartbeat-like low thump every ~2s)
    l4 = gen_layer("pulse", (
        f"aevalsrc="
        f"0.08*exp(-8*mod(t\\,2.0))*sin(2*PI*55*t)"
        f"+0.04*exp(-12*mod(t\\,2.0))*sin(2*PI*82.5*t)"
        f":c=stereo:s=48000,"
        f"volume='0.12':eval=frame,"
        f"lowpass=f=200,"
        f"afade=t=in:ss=0:d=4,afade=t=out:st={DUR-6}:d=6,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l4:
        layers.append(l4)

    # Layer 5: Texture grain (filtered noise, very subtle)
    l5 = gen_layer("texture", (
        f"anoisesrc=d={DUR}:c=pink:r=48000:a=0.008,"
        f"highpass=f=200,lowpass=f=3000,"
        f"volume='0.04+0.02*sin(2*PI*0.06*t)':eval=frame,"
        f"afade=t=in:ss=0:d=8,afade=t=out:st={DUR-6}:d=6,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l5:
        layers.append(l5)

    # Layer 6: Rising tension (build from 30s to 60s, then resolve)
    l6 = gen_layer("tension_rise", (
        f"aevalsrc="
        f"0.03*sin(2*PI*(55+20*min(1\\,max(0\\,(t-30)/30)))*t)"
        f"+0.02*sin(2*PI*(82.5+15*min(1\\,max(0\\,(t-30)/30)))*t)"
        f":c=stereo:s=48000,"
        f"volume='0.08*min(1\\,max(0\\,(t-25)/10))*max(0\\,1-max(0\\,(t-65)/10))':eval=frame,"
        f"lowpass=f=400,"
        f"afade=t=in:ss=0:d=4,afade=t=out:st={DUR-6}:d=6,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ), DUR)
    if l6:
        layers.append(l6)

    if not layers:
        print("ERROR: no layers generated")
        return

    # Mix all layers
    inputs = []
    for l in layers:
        inputs.extend(["-i", l])
    n = len(layers)
    fc = ";".join(f"[{i}:a]aresample=48000[a{i}]" for i in range(n))
    fc += ";" + "".join(f"[a{i}]" for i in range(n))
    fc += f"amix=inputs={n}:duration=longest:dropout_transition=3[mix]"
    fc += ";[mix]alimiter=limit=0.9:level=false,loudnorm=I=-18:TP=-2:LRA=7[out]"

    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
    ] + inputs + [
        "-filter_complex", fc,
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2", "-ar", "48000", OUT,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        sz = os.path.getsize(OUT)
        print(f"wrote {OUT} ({sz} bytes)")
    else:
        print(f"FAIL mix: {r.stderr.strip()[:300]}")

    # Cleanup temp layers
    for l in layers:
        try:
            os.remove(l)
        except OSError:
            pass


if __name__ == "__main__":
    main()
