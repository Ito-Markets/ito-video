#!/usr/bin/env python3
"""
fx_glitch.py — subtle FX for the ItoMarkets brand film.
Reused from Shenzhen MV but tuned down: light feedback, slow drift, clean pixelsort.
NOT the heavy angelcore datamosh. This is for tasteful transitions and texture.

Usage: fx_glitch.py <in.mp4> <start_s> <dur_s> <out.mp4> <seed> [mode]
Modes: mosh | pixelsort | feedback | drift
"""
import sys, subprocess, numpy as np

SRC, START, DUR, OUT, SEED = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], int(sys.argv[5])
MODE = sys.argv[6] if len(sys.argv) > 6 else "drift"
W, H, FPS = 1920, 1080, 30
rng = np.random.default_rng(SEED)

dec = subprocess.Popen(
    ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{START:.3f}", "-t", f"{DUR:.3f}",
     "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-"],
    stdout=subprocess.PIPE)
enc = subprocess.Popen(
    ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
     "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", OUT],
    stdin=subprocess.PIPE)

frame_bytes = W * H * 3
prev = None
acc = None
n = 0

def fx_pixelsort(f, p):
    from pixelsort import pixelsort
    from PIL import Image
    lo = max(0.08, 0.45 - 0.35 * p)
    img = pixelsort(Image.fromarray(f), interval_function="threshold",
                    sorting_function="lightness", lower_threshold=lo,
                    upper_threshold=0.95, angle=90, randomness=8)
    return np.asarray(img.convert("RGB"))

def fx_feedback(f, p):
    global acc
    from PIL import Image
    if acc is None:
        acc = f.astype(np.float32)
    z = Image.fromarray(acc.astype(np.uint8)).resize((int(W * 1.008), int(H * 1.008))))
    x0 = (z.width - W) // 2; y0 = (z.height - H) // 2
    zoomed = np.asarray(z.crop((x0, y0, x0 + W, y0 + H)), dtype=np.float32)
    decay = 0.90 + 0.06 * p
    acc = np.maximum(f.astype(np.float32), zoomed * decay)
    return acc.astype(np.uint8)

def fx_drift(f, p):
    # subtle horizontal shift + RGB separation, very light
    shift = int(rng.integers(2, 18) * p) * (1 if rng.random() < 0.5 else -1)
    f = f.copy()
    f[:, :, 0] = np.roll(f[:, :, 0], shift, axis=1)
    f[:, :, 2] = np.roll(f[:, :, 2], -shift // 2, axis=1)
    return f

while True:
    buf = dec.stdout.read(frame_bytes)
    if len(buf) < frame_bytes:
        break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
    total = max(1, int(DUR * FPS))
    p = min(1.0, (n + 1) / (total * 0.6))

    if MODE == "pixelsort":
        out = fx_pixelsort(f, p)
    elif MODE == "feedback":
        out = fx_feedback(f, p)
    elif MODE == "drift":
        out = fx_drift(f, p)
    else:
        # very light mosh
        out = f
        y = 0
        while y < H:
            bh = int(rng.integers(8, 28))
            if rng.random() < 0.12 * p:
                shift = int(rng.integers(4, 40) * p) * (1 if rng.random() < .5 else -1)
                out[y:y+bh] = np.roll(out[y:y+bh], shift, axis=1)
            y += bh
        if p > 0.2:
            r = int(2 + 8 * p); b = int(1 + 6 * p)
            out[:, :, 0] = np.roll(out[:, :, 0], r, axis=1)
            out[:, :, 2] = np.roll(out[:, :, 2], -b, axis=1)
    enc.stdin.write(out.tobytes())
    prev = f
    n += 1

enc.stdin.close(); dec.stdout.close()
enc.wait(); dec.wait()
print(f"{MODE} {n} frames -> {OUT}")
