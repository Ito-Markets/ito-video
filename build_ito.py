#!/usr/bin/env python3
"""
build_ito.py — narrative assembler for the ItoMarkets institutional brand film.
1920x1080, 30fps, zero-repeat scheduler.
Reads edl.json, renders each select with motion + grade, concatenates to out/rough_cut.mp4.
"""
import json, os, subprocess

BUILD = os.path.dirname(os.path.abspath(__file__))
TRIMS = os.path.join(BUILD, "trims")
OUT = os.path.join(BUILD, "out")
os.makedirs(TRIMS, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

edl = json.load(open(os.path.join(BUILD, "edl.json")))
POOL = {s["id"]: s for s in edl["pool"]}
CW, CH = 1920, 1080
MW, MH = 2208, 1242
TAG = "format=yuv420p,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709"

# Narrative sections: name -> (target_seconds, motion_zoom, cut_intensity)
# Timed to the 76s ElevenLabs voiceover.
SECTIONS = [
    ("open",      8,  0.04, 0.0),
    ("history",  10,  0.06, 0.0),
    ("math",     12,  0.07, 0.0),
    ("problem",   8,  0.08, 0.0),
    ("solution", 14,  0.09, 0.0),
    ("product",  14,  0.08, 0.0),
    ("close",    10,  0.05, 0.0),
]


def resolve_src(s):
    src = s["src"]
    if src.startswith("/"):
        return src
    # Try relative to project root, then to assets/raw/
    for base in [BUILD, os.path.join(BUILD, "assets", "raw")]:
        p = os.path.join(base, src)
        if os.path.exists(p):
            return p
    return os.path.join(BUILD, src)


def pick_for_section(used, used_src, sec_name, prefs):
    def score(s):
        sc = s["rating"] * 10
        if s.get("section") == sec_name:
            sc += 15
        if s.get("family") in prefs:
            sc += 5
        if s.get("src") not in used_src:
            sc += 8
        return sc

    cands = [s for s in edl["pool"] if s["id"] not in used]
    if not cands:
        return None
    return max(cands, key=score)


def motion_expr(idx, D, zoom):
    dw = int(MW - MW / (1 + zoom))
    dh = int(MH - MH / (1 + zoom))
    p = f"min(t/{max(D, 0.3):.4f},1)"
    style = idx % 4
    cx, cy = "(iw-ow)/2", "(ih-oh)/2"
    if style == 0:
        w = f"{MW}-{dw}*{p}"; h = f"{MH}-{dh}*{p}"
    elif style == 1:
        w = f"{MW-dw}+{dw}*{p}"; h = f"{MH-dh}+{dh}*{p}"
    elif style == 2:
        w = f"{MW-dw//2}"; h = f"{MH-dh//2}"
        cx = f"(iw-ow)*(0.25+0.50*{p})"
    else:
        w = f"{MW-dw//2}"; h = f"{MH-dh//2}"
        cx = f"(iw-ow)*(0.65-0.30*{p})"
        cy = f"(ih-oh)*(0.35+0.30*{p})"
    return f"crop=w='{w}':h='{h}':x='{cx}':y='{cy}'"


def grade_chain(tags):
    chain = ["eq=contrast=1.12:saturation=0.95:gamma=0.98"]
    if "crush_black" in tags:
        chain.append("curves=all='0/0 0.10/0.02 0.5/0.52 1/1'")
    if "mono" in tags:
        chain.append("colorchannelmixer=.299:.587:.114:0:.299:.587:.114:0:.299:.587:.114")
    if "gold" in tags:
        chain.append("colorbalance=rs=.04:gs=.02:bs=-.04")
    if "cool" in tags:
        chain.append("colorbalance=rs=-.03:gs=.01:bs=.05")
    chain.append("vignette=angle=PI/5:mode=backward")
    chain.append("noise=alls=4:allf=t")
    return ",".join(chain)


def render(s, idx, T, out_path):
    src = resolve_src(s)
    if not os.path.exists(src):
        print(f"  MISSING {src}")
        return False

    # Materialize iCloud/evicted files before ffmpeg
    subprocess.run(["bash", "-c", f"cat '{src}' >/dev/null 2>&1"])

    t_in = s["in"]
    avail = max(0.2, s["out"] - s["in"] - 0.05)
    speed = s.get("speed", 1.0)
    if T * speed > avail:
        speed = max(0.12, avail / T)
    ptsf = 1.0 / speed
    dur_src = T * speed

    rot = "transpose=2," if s.get("rotate") else ""
    sec_name = s.get("section", "flex")
    sec_cfg = next((cfg for cfg in SECTIONS if cfg[0] == sec_name), SECTIONS[-1])
    zoom = sec_cfg[2]

    fc = (f"[0:v]{rot}scale={MW}:{MH}:force_original_aspect_ratio=increase,"
          f"crop={MW}:{MH},setsar=1,setpts={ptsf:.4f}*PTS,fps=30,"
          f"{motion_expr(idx, T, zoom)},scale={CW}:{CH},setsar=1,format=gbrp,"
          f"{grade_chain(s.get('grade', []))},{TAG}[v]")

    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
           "-ss", f"{t_in:.3f}", "-t", f"{dur_src:.3f}", "-i", src,
           "-filter_complex", fc, "-map", "[v]", "-an",
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
           "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out_path), r.stderr


def main():
    used = set()
    used_src = set()
    timeline = []
    idx = 0

    for sec_name, target_sec, zoom, _ in SECTIONS:
        run = 0.0
        prefs = {
            "open": ["space", "wallstreet", "founder"],
            "history": ["history", "archive", "exchange"],
            "math": ["math", "geometry", "animation"],
            "problem": ["market", "data", "fragment"],
            "solution": ["founder", "product", "basket"],
            "product": ["market", "data", "basket"],
            "close": ["founder", "space", "wallstreet"],
        }.get(sec_name, [])

        while run < target_sec - 0.3:
            remaining = target_sec - run
            s = pick_for_section(used, used_src, sec_name, prefs)
            if s is None:
                break
            T = min(remaining, max(1.0, target_sec / 3.0))
            # shorter cuts for high-energy sections, longer for history/math
            if sec_name in ("drop", "product"):
                T = min(T, 2.5)
            elif sec_name in ("history", "math"):
                T = min(T, 4.5)
            else:
                T = min(T, 3.5)

            outp = os.path.join(TRIMS, f"{idx:03d}_{sec_name}_{s['id']}.mp4")
            ok, err = render(s, idx, T, outp)
            if ok:
                used.add(s["id"])
                used_src.add(s["src"])
                timeline.append((sec_name, s["id"], T))
                concat = f"file '{outp}'"
                run += T
                print(f"{idx:03d} {sec_name:8} {s['id']:6} {T:4.1f}s")
                idx += 1
            else:
                print(f"  FAIL {s['id']}: {err.strip()[:120]}")
                used.add(s["id"])  # don't retry
                break

    concat_file = os.path.join(BUILD, "concat.txt")
    open(concat_file, "w").write("\n".join(
        f"file '{os.path.join(TRIMS, f'{i:03d}_{sec}_{sid}.mp4')}'"
        for i, (sec, sid, _) in enumerate(timeline)
    ) + "\n")

    final = os.path.join(OUT, "rough_cut.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", concat_file, "-c", "copy", final], check=False)
    total = sum(T for _, _, T in timeline)
    print(f"\nsegs: {len(timeline)}  TIMELINE: {total:.1f}s -> {final}")


if __name__ == "__main__":
    main()
