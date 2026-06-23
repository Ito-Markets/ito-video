#!/usr/bin/env python3
"""
build_ito.py — narrative assembler for the ItoMarkets institutional brand film v2.
1920x1080, 30fps, zero-repeat scheduler.
Reads edl.json, renders each select with motion + grade, then uses xfade to
produce smooth crossfade transitions between clips in out/rough_cut.mp4.

v2 changes:
- Tighter section timing synced to voiceover beats
- Real crossfade transitions via xfade filter (not fade-to-black)
- Ordered asset placement for narrative flow
- More precise cut lengths
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

# v2: Narrative sections synced to the voiceover script beats.
# name, target_seconds, motion_zoom, crossfade_dur
# Total target: ~92s (voiceover ~76s + endcard breathing room)
SECTIONS = [
    ("open",      8,  0.04, 0.3),   # 0:00-0:08  "In 1990, the first ETF..."
    ("history",  18,  0.05, 0.4),   # 0:08-0:26  "Since then..." + "bundle the underlying..."
    ("math",     20,  0.06, 0.3),   # 0:26-0:46  "The math behind it..." + portraits
    ("problem",  12,  0.07, 0.2),   # 0:46-0:58  "Today, prediction markets..."
    ("solution", 20,  0.08, 0.3),   # 0:58-1:18  "ItoMarkets builds..." + "institutions can hedge"
    ("product",  10,  0.07, 0.3),   # 1:18-1:28  "We compose markets..." + "tokenize the baskets"
    ("close",    14,  0.04, 0.5),   # 1:28-1:42  "The next ETF..." + endcard
]

# v2: Ordered placement — specific clip order per section for narrative coherence
SECTION_ORDER = {
    "open":     ["t_1990", "st_tmx", "st_nyse_ticker"],
    "history":  ["st_nyse_floor", "st_nyse_open", "m_sacred", "m_basket"],
    "math":     ["h_alkhwarizmi", "h_euler", "h_riemann", "h_ito", "m_stochastic", "h_simons", "m_names"],
    "problem":  ["p_fragment", "broll_problem_traders"],
    "solution": ["m_web", "broll_solution_floor", "broll_solution_trading"],
    "product":  ["m_ticker", "broll_product_exchange"],
    "close":    ["c_atlas", "c_globe", "c_endcard"],
}

# Max clip duration per section — sparse sections get longer clips
SECTION_MAX_DUR = {
    "open": 4.0, "history": 5.0, "math": 3.5,
    "problem": 8.0, "solution": 8.8, "product": 6.0, "close": 8.0,
}

XFADE_DUR = 0.5  # crossfade duration between clips


def resolve_src(s):
    src = s["src"]
    if src.startswith("/"):
        return src
    for base in [BUILD, os.path.join(BUILD, "assets", "raw")]:
        p = os.path.join(base, src)
        if os.path.exists(p):
            return p
    return os.path.join(BUILD, src)


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
        return False, ""

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

    # Clips with grade tags get full motion pipeline (upscale, Ken Burns, color grade).
    # Clips with empty grade (titles, endcard) get simplified scale-only path.
    if s.get("grade"):
        fc = (f"[0:v]{rot}scale={MW}:{MH}:force_original_aspect_ratio=increase,"
              f"crop={MW}:{MH},setsar=1,setpts={ptsf:.4f}*PTS,fps=30,"
              f"{motion_expr(idx, T, zoom)},scale={CW}:{CH},setsar=1,format=gbrp,"
              f"{grade_chain(s.get('grade', []))},{TAG}[v]")
    else:
        fc = (f"[0:v]{rot}scale={CW}:{CH}:force_original_aspect_ratio=increase,"
              f"crop={CW}:{CH},setsar=1,setpts={ptsf:.4f}*PTS,fps=30,"
              f"format=gbrp,{TAG}[v]")

    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
           "-ss", f"{t_in:.3f}", "-t", f"{dur_src:.3f}", "-i", src,
           "-filter_complex", fc, "-map", "[v]", "-an",
           "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
           "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out_path), r.stderr


def xfade_concat(trim_paths, durations, xfade_dur, output):
    """Use ffmpeg xfade filter to crossfade between clips with real blending."""
    n = len(trim_paths)
    if n == 0:
        return
    if n == 1:
        subprocess.run(["cp", trim_paths[0], output], check=True)
        return

    # Build xfade filter chain: [0:v][1:v]xfade=...[v01]; [v01][2:v]xfade=...[v02]; ...
    inputs = []
    for p in trim_paths:
        inputs.extend(["-i", p])

    filters = []
    offsets = []
    cumulative = 0.0
    for i in range(n - 1):
        offset = cumulative + durations[i] - xfade_dur
        offsets.append(offset)
        cumulative = offset

        if i == 0:
            src_a = "[0:v]"
        else:
            src_a = f"[v{i-1}{i}]"

        src_b = f"[{i+1}:v]"
        out_label = f"[v{i}{i+1}]"

        if i == n - 2:
            out_label = "[vout]"

        filters.append(
            f"{src_a}{src_b}xfade=transition=fade:duration={xfade_dur:.2f}:"
            f"offset={offset:.3f}{out_label}"
        )

    fc = ";".join(filters)
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
    ] + inputs + [
        "-filter_complex", fc,
        "-map", "[vout]", "-an",
        "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", output,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  xfade failed ({r.stderr.strip()[:200]}), falling back to concat")
        concat_fallback(trim_paths, output)
    else:
        print(f"  xfade OK -> {output}")


def concat_fallback(trim_paths, output):
    """Simple concat fallback if xfade fails."""
    concat_file = os.path.join(BUILD, "concat.txt")
    with open(concat_file, "w") as f:
        for p in trim_paths:
            f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", concat_file,
                    "-c", "copy", output], check=False)


def main():
    used = set()
    timeline = []
    idx = 0

    for sec_name, target_sec, zoom, xfade_dur in SECTIONS:
        run = 0.0
        order = SECTION_ORDER.get(sec_name, [])
        order_idx = 0

        while run < target_sec - 0.3:
            remaining = target_sec - run

            # v2: Use ordered placement first, then fall back to scoring
            s = None
            while order_idx < len(order):
                cid = order[order_idx]
                order_idx += 1
                if cid in POOL and cid not in used:
                    s = POOL[cid]
                    break

            if s is None:
                # Fallback: only pick clips tagged for this section
                cands = [c for c in edl["pool"]
                         if c["id"] not in used and c.get("section") == sec_name]
                if not cands:
                    break
                s = max(cands, key=lambda c: c["rating"])

            # v2: Use section-specific max duration
            avail_dur = s["out"] - s["in"]
            max_dur = SECTION_MAX_DUR.get(sec_name, 4.0)
            if sec_name == "close" and s["id"] == "c_endcard":
                max_dur = 8.0
            T = min(remaining, avail_dur, max_dur)

            T = max(T, 1.0)

            outp = os.path.join(TRIMS, f"{idx:03d}_{sec_name}_{s['id']}.mp4")
            ok, err = render(s, idx, T, outp)
            if ok:
                used.add(s["id"])
                timeline.append((sec_name, s["id"], T, outp))
                run += T
                print(f"{idx:03d} {sec_name:10} {s['id']:18} {T:5.1f}s  [{run:5.1f}/{target_sec}s]")
                idx += 1
            else:
                print(f"  FAIL {s['id']}: {str(err).strip()[:120]}")
                used.add(s["id"])
                break

    # v2: Use xfade for real crossfade transitions between all clips
    trim_paths = [t[3] for t in timeline]
    durations = [t[2] for t in timeline]
    final = os.path.join(OUT, "rough_cut.mp4")

    print(f"\nassembling {len(timeline)} segments with xfade crossfades...")
    xfade_concat(trim_paths, durations, XFADE_DUR, final)

    total = sum(T for _, _, T, _ in timeline)
    effective = total - XFADE_DUR * max(0, len(timeline) - 1)
    print(f"segs: {len(timeline)}  raw: {total:.1f}s  effective (with xfade): {effective:.1f}s -> {final}")


if __name__ == "__main__":
    main()
