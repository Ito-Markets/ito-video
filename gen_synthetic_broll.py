#!/usr/bin/env python3
"""
gen_synthetic_broll.py — generate synthetic b-roll clips using pure FFmpeg.
Produces abstract geometry, data-viz, particle effects, and typography plates.
"""
import os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BUILD, "assets", "gen")
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1920, 1080, 30


def ffmpeg_gen(name, dur, fc, extra_args=None):
    out = os.path.join(OUT, f"{name}.mp4")
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", fc,
        "-t", f"{dur:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out,
    ]
    if extra_args:
        cmd = cmd[:-1] + extra_args + [out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK {name} ({dur}s)")
    else:
        print(f"FAIL {name}: {r.stderr.strip()[:200]}")
    return r.returncode == 0


def gen_sacred_geo():
    """Sacred geometry: golden spiral / rotating Fibonacci lattice on black."""
    fc = (
        f"color=c=black:s={W}x{H}:r={FPS},"
        f"drawtext=text='∞':fontcolor=0xC8A84E@0.15:fontsize=400:"
        f"x='(w-text_w)/2+50*sin(2*PI*t/8)':y='(h-text_h)/2+30*cos(2*PI*t/6)',"
        f"drawtext=text='φ':fontcolor=0xC8A84E@0.12:fontsize=300:"
        f"x='(w-text_w)/2-120+80*cos(2*PI*t/10)':y='(h-text_h)/2+60*sin(2*PI*t/7)',"
        f"drawtext=text='Σ':fontcolor=0x8090B0@0.10:fontsize=350:"
        f"x='(w-text_w)/2+100+40*sin(2*PI*t/12)':y='(h-text_h)/2-80+50*cos(2*PI*t/9)',"
        f"drawtext=text='∫':fontcolor=0x8090B0@0.08:fontsize=280:"
        f"x='(w-text_w)/2-200+60*cos(2*PI*t/6)':y='(h-text_h)/2+120+40*sin(2*PI*t/11)',"
        f"drawtext=text='∂':fontcolor=0xC8A84E@0.10:fontsize=250:"
        f"x='(w-text_w)/2+180+70*sin(2*PI*t/9)':y='(h-text_h)/2-150+60*cos(2*PI*t/8)',"
        f"vignette=angle=PI/4:mode=backward"
    )
    ffmpeg_gen("sacred_geo", 7.6, fc)


def gen_basket():
    """Basket convergence: blocks of text converging to center (ETF basket motif)."""
    fc = (
        f"color=c=black:s={W}x{H}:r={FPS},"
        f"drawtext=text='EQUITY':fontcolor=0xC8A84E99:fontsize='40+10*sin(t)':"
        f"x='w/4-text_w/2+200*(1-min(t/3\\,1))':y='h/3-text_h/2',"
        f"drawtext=text='BOND':fontcolor=0x8090B099:fontsize='40+8*cos(t)':"
        f"x='3*w/4-text_w/2-200*(1-min(t/3\\,1))':y='h/3-text_h/2',"
        f"drawtext=text='COMMODITY':fontcolor=0xC8A84E99:fontsize='40+6*sin(t+1)':"
        f"x='w/4-text_w/2+200*(1-min(t/3\\,1))':y='2*h/3-text_h/2',"
        f"drawtext=text='PREDICTION':fontcolor=0x8090B099:fontsize='40+12*cos(t+2)':"
        f"x='3*w/4-text_w/2-200*(1-min(t/3\\,1))':y='2*h/3-text_h/2',"
        f"drawtext=text='BASKET':fontcolor=0xFFFFFFCC:fontsize='60+20*min(1\\,(t-2)/3)':"
        f"x='(w-text_w)/2':y='(h-text_h)/2',"
        f"vignette=angle=PI/5:mode=backward"
    )
    ffmpeg_gen("basket", 5.9, fc)


def gen_market_web():
    """Market network: simulated node connections radiating from center."""
    fc = (
        f"color=c=0x0A0A14:s={W}x{H}:r={FPS},"
        f"drawtext=text='●':fontcolor=0x4488CC@0.5:fontsize=24:"
        f"x='w/2+200*cos(2*PI*t/5)':y='h/2+120*sin(2*PI*t/5)',"
        f"drawtext=text='●':fontcolor=0x44CC88@0.5:fontsize=20:"
        f"x='w/2+300*cos(2*PI*t/7+1)':y='h/2+180*sin(2*PI*t/7+1)',"
        f"drawtext=text='●':fontcolor=0xCC8844@0.5:fontsize=22:"
        f"x='w/2+250*cos(2*PI*t/6+2)':y='h/2+150*sin(2*PI*t/6+2)',"
        f"drawtext=text='●':fontcolor=0x4488CC@0.4:fontsize=18:"
        f"x='w/2+350*cos(2*PI*t/8+3)':y='h/2+200*sin(2*PI*t/8+3)',"
        f"drawtext=text='●':fontcolor=0xCC4488@0.4:fontsize=16:"
        f"x='w/2+150*cos(2*PI*t/4+4)':y='h/2+100*sin(2*PI*t/4+4)',"
        f"drawtext=text='⬡':fontcolor=0xC8A84E@0.3:fontsize=60:"
        f"x='(w-text_w)/2':y='(h-text_h)/2',"
        f"vignette=angle=PI/4:mode=backward,"
        f"noise=alls=3:allf=t"
    )
    ffmpeg_gen("market_web", 8.8, fc)


def gen_ticker_overlay():
    """Scrolling ticker tape: financial data scrolling across screen."""
    fc = (
        f"color=c=0x0A0A14:s={W}x{H}:r={FPS},"
        f"drawtext=text='  AAPL 189.52 ▲2.1   MSFT 421.80 ▲0.8   GOOG 178.34 ▼0.3   BTC 67420 ▲3.2   ETH 3842 ▲1.7   SPX 5423.10 ▲0.4  ':"
        f"fontcolor=0x00CC66@0.7:fontsize=28:"
        f"x='w-mod(t*120\\,w+text_w)':y='h-60',"
        f"drawtext=text='  ITO-S3 1.042 ▲1.2   ITO-S7 0.987 ▼0.4   ITO-B1 2.341 ▲0.8  ':"
        f"fontcolor=0xC8A84E@0.6:fontsize=24:"
        f"x='w-mod(t*80\\,w+text_w)':y='60',"
        f"vignette=angle=PI/6:mode=backward,"
        f"noise=alls=2:allf=t"
    )
    ffmpeg_gen("ticker_overlay", 6.0, fc)


def gen_stochastic_paths():
    """Stochastic calculus visualization: Brownian motion paths."""
    fc = (
        f"color=c=black:s={W}x{H}:r={FPS},"
        f"drawtext=text='dXt = uXtdt + sXtdWt':fontcolor=0xC8A84EB3:fontsize=48:"
        f"x='(w-text_w)/2':y='h/4',"
        f"drawtext=text='Ito Lemma':fontcolor=0xFFFFFFCC:fontsize=36:"
        f"x='(w-text_w)/2':y='h/4+70',"
        f"drawtext=text='~':fontcolor=0x4488CC66:fontsize=200:"
        f"x='w/4+100*sin(2*PI*t/3)':y='h/2+50*cos(2*PI*t/4)',"
        f"drawtext=text='~':fontcolor=0x8090B04D:fontsize=180:"
        f"x='3*w/4+80*cos(2*PI*t/5)':y='h/2+40*sin(2*PI*t/3)',"
        f"drawtext=text='~':fontcolor=0xC8A84E40:fontsize=160:"
        f"x='w/2+120*sin(2*PI*t/7)':y='2*h/3+60*cos(2*PI*t/5)',"
        f"vignette=angle=PI/4:mode=backward,"
        f"noise=alls=4:allf=t"
    )
    ffmpeg_gen("stochastic_paths", 6.0, fc)


def gen_endcard():
    """End card: ItoMarkets branding on black."""
    out = os.path.join(OUT, "endcard.mp4")
    # Generate with full opacity then add fade-in
    fc = (
        f"color=c=black:s={W}x{H}:r={FPS},"
        f"drawtext=text='ItoMarkets':fontcolor=0xFFFFFF:fontsize=72:"
        f"x='(w-text_w)/2':y='(h-text_h)/2-40',"
        f"drawtext=text='ETF layer for prediction markets':fontcolor=0xC8A84E:fontsize=32:"
        f"x='(w-text_w)/2':y='(h-text_h)/2+50',"
        f"fade=t=in:st=0:d=2"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", fc,
        "-t", "8.00", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK endcard (8.0s)")
    else:
        print(f"FAIL endcard: {r.stderr.strip()[:200]}")


def gen_title_1990():
    """Opening title: '1990' / 'Toronto' text reveal."""
    out = os.path.join(OUT, "title_1990.mp4")
    fc = (
        f"color=c=black:s={W}x{H}:r={FPS},"
        f"drawtext=text='1990':fontcolor=0xFFFFFF:fontsize=120:"
        f"x='(w-text_w)/2':y='(h-text_h)/2-60',"
        f"drawtext=text='Toronto':fontcolor=0xC8A84E:fontsize=48:"
        f"x='(w-text_w)/2':y='(h-text_h)/2+60',"
        f"fade=t=in:st=0:d=1.5"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", fc,
        "-t", "5.00", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK title_1990 (5.0s)")
    else:
        print(f"FAIL title_1990: {r.stderr.strip()[:200]}")


def gen_names_montage():
    """Math names appearing in sequence — 4 separate clips crossfaded."""
    names = [
        ("Al-Khwarizmi", "0xC8A84E", 56),
        ("Euler", "0xC8A84E", 56),
        ("Riemann", "0x8090B0", 56),
        ("Ito", "0xFFFFFF", 72),
    ]
    parts = []
    for i, (name, color, size) in enumerate(names):
        part = os.path.join(OUT, f"name_part_{i}.mp4")
        fc = (
            f"color=c=black:s={W}x{H}:r={FPS},"
            f"drawtext=text='{name}':fontcolor={color}:fontsize={size}:"
            f"x='(w-text_w)/2':y='(h-text_h)/2',"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st=2.0:d=0.5"
        )
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", fc,
            "-t", "2.50", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-pix_fmt", "yuv420p", part,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            parts.append(part)
        else:
            print(f"FAIL name_part_{i}: {r.stderr.strip()[:200]}")
    if parts:
        concat_file = os.path.join(OUT, "names_concat.txt")
        with open(concat_file, "w") as f:
            for p in parts:
                f.write(f"file '{p}'\n")
        out = os.path.join(OUT, "names_montage.mp4")
        subprocess.run([
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy", out
        ], check=False)
        print(f"OK names_montage ({len(parts) * 2.5}s)")
        # Clean up temp part files
        for p in parts:
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.remove(concat_file)
        except OSError:
            pass


def gen_fragment_venues():
    """Fragmented venues: glitchy tiling of prediction market names."""
    fc = (
        f"color=c=0x0A0A14:s={W}x{H}:r={FPS},"
        f"drawtext=text='POLYMARKET':fontcolor=0xFF444480:fontsize='30+5*sin(4*t)':x='w/6+10*sin(8*t)':y='h/4+5*cos(6*t)',"
        f"drawtext=text='KALSHI':fontcolor=0x4444FF80:fontsize='28+4*cos(3*t)':x='4*w/6+8*cos(7*t)':y='h/3+4*sin(5*t)',"
        f"drawtext=text='METACULUS':fontcolor=0x44FF4466:fontsize='26+3*sin(5*t)':x='w/3+12*sin(6*t)':y='2*h/3+6*cos(4*t)',"
        f"drawtext=text='MANIFOLD':fontcolor=0xFFFF4466:fontsize='24+4*cos(4*t)':x='2*w/3+6*cos(9*t)':y='h/2+8*sin(3*t)',"
        f"drawtext=text='FRAGMENTED':fontcolor=0xFF6644B3:fontsize=48:x='(w-text_w)/2':y='3*h/4',"
        f"noise=alls=8:allf=t,"
        f"vignette=angle=PI/3:mode=backward"
    )
    ffmpeg_gen("fragment_venues", 8.0, fc)


def gen_stock_exchange_trim():
    """Trim usable segments from the Internet Archive NYSE footage."""
    src = os.path.join(BUILD, "assets", "raw", "archive_behind_ticker_tape_open.mp4")
    if not os.path.exists(src):
        print("SKIP stock_exchange_trim: no source")
        return
    for name, ss, dur in [
        ("vidsplay_stock_exchange", 30, 5),
        ("archive_vista_nyse_floor", 60, 5),
        ("archive_vista_nyse_open", 120, 5),
        ("problem_traders", 180, 8),
        ("solution_floor", 240, 8),
        ("solution_trading", 300, 8),
        ("product_exchange", 360, 6),
    ]:
        out = os.path.join(OUT, f"broll_{name}.mp4")
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-ss", str(ss), "-t", str(dur), "-i", src,
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                   f"eq=contrast=1.15:saturation=0.85:gamma=0.95,"
                   f"vignette=angle=PI/5,noise=alls=4:allf=t,format=yuv420p",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-an", "-pix_fmt", "yuv420p", out,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"OK broll_{name} ({dur}s)")
        else:
            print(f"FAIL broll_{name}: {r.stderr.strip()[:200]}")


def gen_tmx_still_clip():
    """Generate a Ken Burns clip from the TMX ETF still."""
    src = os.path.join(BUILD, "assets", "stills", "tmx_etf.jpg")
    if not os.path.exists(src):
        print("SKIP tmx_still: no source")
        return
    out = os.path.join(OUT, "still_tmx.mp4")
    fc = (
        f"[0:v]scale=2560:1440:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,"
        f"zoompan=z='min(zoom+0.0005,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={int(5 * 30)}:s=1920x1080:fps=30,"
        f"format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-loop", "1", "-i", src,
        "-filter_complex", fc, "-map", "[v]", "-an", "-t", "5.00",
        "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK still_tmx (5s)")
    else:
        print(f"FAIL still_tmx: {r.stderr.strip()[:200]}")


def gen_nyse_floor_still_clip():
    """Generate Ken Burns from NYSE 1963 floor still (if downloaded)."""
    src = os.path.join(BUILD, "assets", "stills", "nyse_floor_1963.jpg")
    if not os.path.exists(src):
        print("SKIP nyse_floor_still: no source")
        return
    out = os.path.join(OUT, "still_nyse_floor.mp4")
    fc = (
        f"[0:v]scale=2560:1440:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,"
        f"zoompan=z='min(zoom+0.0004,1.4)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={int(5 * 30)}:s=1920x1080:fps=30,"
        f"format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-loop", "1", "-i", src,
        "-filter_complex", fc, "-map", "[v]", "-an", "-t", "5.00",
        "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK still_nyse_floor (5s)")
    else:
        print(f"FAIL still_nyse_floor: {r.stderr.strip()[:200]}")


if __name__ == "__main__":
    gen_sacred_geo()
    gen_basket()
    gen_market_web()
    gen_ticker_overlay()
    gen_stochastic_paths()
    gen_endcard()
    gen_title_1990()
    gen_names_montage()
    gen_fragment_venues()
    gen_stock_exchange_trim()
    gen_tmx_still_clip()
    gen_nyse_floor_still_clip()
