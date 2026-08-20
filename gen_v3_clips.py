#!/usr/bin/env python3
"""
gen_v3_clips.py — Generate all visual clips for the sub-30s Ito brand film v3.

Uses:
  - Pillow for branded typography cards, Ken Burns, overlays
  - FFmpeg for glitch effects (chromatic aberration, scanlines, grain)
  - Manim for math animations (Ito's lemma, stochastic paths, SDE)
  - NumPy for particle/data buffer generation

Brand spec (from ito-cloud-runtime):
  - Fonts: Libre Baskerville (serif headlines), IBM Plex Mono (labels)
  - Colors: BG #0A0E17, Gold #8D7A50, Ink #111827, White #E8E4DE
  - Art: Japanese gold-leaf screens, Hokusai, Fuji woodblock
"""
import json
import math
import os
import random
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
GEN = ASSETS / "gen"
ART = ASSETS / "art"
BRAND = ASSETS / "brand"
FONTS = ASSETS / "fonts"
STILLS = ASSETS / "stills"
REF_BROLL = ASSETS / "ref_broll"
CLIPS = ROOT / "clips_v3"

GEN.mkdir(parents=True, exist_ok=True)
CLIPS.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
FPS = 30

# Brand colors
BG = (10, 14, 23)
GOLD = (141, 122, 80)
WHITE = (232, 228, 222)
INK = (17, 24, 39)
ACCENT_BLUE = (54, 95, 146)
GAIN_GREEN = (4, 120, 87)
LOSS_RED = (220, 38, 38)

BG_HEX = "#0A0E17"
GOLD_HEX = "#8D7A50"
WHITE_HEX = "#E8E4DE"

SERIF_FONT = str(FONTS / "LibreBaskerville.ttf")
MONO_FONT = str(FONTS / "IBMPlexMono-Regular.ttf")
MONO_BOLD = str(FONTS / "IBMPlexMono-Bold.ttf")
MONO_MED = str(FONTS / "IBMPlexMono-Medium.ttf")


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()


def make_bg(w: int = W, h: int = H) -> Image.Image:
    """Dark background with subtle radial gradient."""
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    max_r = math.sqrt(cx**2 + cy**2)
    for r in range(int(max_r), 0, -4):
        t = r / max_r
        c = tuple(int(BG[i] + (20 - BG[i]) * (1 - t) * 0.3) for i in range(3))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return img


def add_grain(img: Image.Image, amount: int = 12) -> Image.Image:
    """Add subtle film grain."""
    arr = np.array(img)
    noise = np.random.randint(-amount, amount + 1, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def add_scanlines(img: Image.Image, opacity: float = 0.08) -> Image.Image:
    """Add CRT-style horizontal scanlines."""
    arr = np.array(img, dtype=np.float32)
    for y in range(0, arr.shape[0], 2):
        arr[y] *= (1.0 - opacity)
    return Image.fromarray(arr.astype(np.uint8))


def add_vignette(img: Image.Image, strength: float = 0.4) -> Image.Image:
    """Darkened corners vignette."""
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / np.sqrt(cx**2 + cy**2)
    mask = 1.0 - np.clip(dist * strength, 0, 1)
    mask = mask[..., np.newaxis]
    arr = arr * (mask * 0.7 + 0.3)
    return Image.fromarray(arr.astype(np.uint8))


def ken_burns_frame(
    img: Image.Image,
    t: float,
    zoom_start: float = 1.0,
    zoom_end: float = 1.15,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
) -> Image.Image:
    """Extract a Ken Burns cropped frame from image at time t in [0,1]."""
    zoom = zoom_start + (zoom_end - zoom_start) * t
    iw, ih = img.size
    cw = int(W * zoom)
    ch = int(H * zoom)
    # Scale image to fit
    scale = max(cw / iw, ch / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)

    cx = nw // 2 + int(pan_x * t * nw * 0.1)
    cy = nh // 2 + int(pan_y * t * nh * 0.1)
    left = max(0, cx - cw // 2)
    top = max(0, cy - ch // 2)
    left = min(left, nw - cw)
    top = min(top, nh - ch)

    cropped = resized.crop((left, top, left + cw, top + ch))
    return cropped.resize((W, H), Image.LANCZOS)


def frames_to_clip(frames_dir: str, output: str, duration: float, fps: int = FPS):
    """Convert a directory of frame PNGs to an mp4 clip."""
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        output,
    ]
    subprocess.run(cmd, check=True)


def render_pillow_clip(
    frame_gen,
    output: str,
    duration: float,
    fps: int = FPS,
):
    """Render frames from a generator function to an mp4 clip.
    frame_gen(frame_idx, total_frames) -> PIL.Image
    """
    total = int(duration * fps)
    with tempfile.TemporaryDirectory() as td:
        for i in range(total):
            img = frame_gen(i, total)
            img.save(os.path.join(td, f"frame_{i:05d}.png"))
        frames_to_clip(td, output, duration, fps)
    print(f"  -> {output}")


# ── Typography cards ─────────────────────────────────────────────

def gen_typography_card(
    headline: str,
    subtitle: str,
    label: str,
    output: str,
    duration: float = 1.5,
):
    """Branded typography card with animated text reveal."""
    serif_big = load_font(SERIF_FONT, 72)
    serif_med = load_font(SERIF_FONT, 36)
    mono_sm = load_font(MONO_FONT, 14)

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        img = make_bg()
        draw = ImageDraw.Draw(img)

        # Label (mono, uppercase, gold, top-left area)
        label_alpha = min(1.0, t * 4)
        if label:
            lbl = label.upper()
            draw.text(
                (160, H // 2 - 120),
                lbl,
                font=mono_sm,
                fill=tuple(int(GOLD[j] * label_alpha) for j in range(3)),
            )

        # Headline — slide in from left
        offset_x = int((1 - min(1.0, t * 3)) * -60)
        headline_alpha = min(1.0, t * 3)
        fill = tuple(int(WHITE[j] * headline_alpha) for j in range(3))

        # Word-wrap headline
        words = headline.split()
        lines = []
        line = ""
        for w in words:
            test = f"{line} {w}".strip()
            bbox = draw.textbbox((0, 0), test, font=serif_big)
            if bbox[2] - bbox[0] > W - 400:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)

        y = H // 2 - len(lines) * 45
        for ln in lines:
            draw.text((160 + offset_x, y), ln, font=serif_big, fill=fill)
            y += 90

        # Subtitle
        if subtitle:
            sub_alpha = max(0, min(1.0, (t - 0.3) * 3))
            sub_fill = tuple(
                int((WHITE[j] * 0.6) * sub_alpha) for j in range(3)
            )
            draw.text((160, y + 20), subtitle, font=serif_med, fill=sub_fill)

        # Gold accent line
        line_w = int(min(1.0, t * 2) * 80)
        if line_w > 0:
            draw.rectangle(
                [160, H // 2 - 140, 160 + line_w, H // 2 - 137],
                fill=GOLD,
            )

        img = add_scanlines(img, 0.05)
        img = add_grain(img, 8)
        return img

    render_pillow_clip(frame, output, duration)


def gen_endcard(output: str, duration: float = 2.0):
    """Final endcard: Ito logo + tagline + URL."""
    serif = load_font(SERIF_FONT, 64)
    serif_sm = load_font(SERIF_FONT, 28)
    mono = load_font(MONO_FONT, 16)

    # Try to load logo
    logo_path = BRAND / "ito_lockup_horizontal_transparent.png"
    logo = None
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        # Scale logo to fit
        lw = 300
        lh = int(logo.height * lw / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        img = make_bg()
        draw = ImageDraw.Draw(img)

        alpha = min(1.0, t * 2.5)
        fill_w = tuple(int(WHITE[j] * alpha) for j in range(3))
        fill_g = tuple(int(GOLD[j] * alpha) for j in range(3))

        # Logo or text fallback
        cy = H // 2 - 80
        if logo:
            logo_fade = logo.copy()
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(logo_fade)
            logo_fade = enhancer.enhance(alpha)
            lx = (W - logo.width) // 2
            img.paste(logo_fade, (lx, cy - logo.height // 2), logo)
        else:
            # Text fallback
            bbox = draw.textbbox((0, 0), "Ito", font=serif)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, cy - 30), "Ito", font=serif, fill=fill_w)

        # Tagline
        tagline = "The ETF layer for prediction markets."
        tag_alpha = max(0, min(1.0, (t - 0.2) * 3))
        tag_fill = tuple(int(WHITE[j] * tag_alpha * 0.9) for j in range(3))
        bbox = draw.textbbox((0, 0), tagline, font=serif_sm)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, H // 2 + 40), tagline, font=serif_sm, fill=tag_fill)

        # Subtitle
        sub = "Geopolitics, AI, custom baskets, and execution in one system."
        sub_alpha = max(0, min(1.0, (t - 0.35) * 3))
        sub_fill = tuple(int(WHITE[j] * sub_alpha * 0.5) for j in range(3))
        bbox = draw.textbbox((0, 0), sub, font=mono)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, H // 2 + 90), sub, font=mono, fill=sub_fill)

        # URL button
        url_alpha = max(0, min(1.0, (t - 0.5) * 3))
        if url_alpha > 0:
            url = "itomarkets.com"
            bbox = draw.textbbox((0, 0), url, font=mono)
            uw = bbox[2] - bbox[0]
            ux = (W - uw) // 2 - 20
            uy = H // 2 + 140
            border_col = tuple(int(GOLD[j] * url_alpha) for j in range(3))
            draw.rounded_rectangle(
                [ux, uy, ux + uw + 40, uy + 36],
                radius=18,
                outline=border_col,
                width=1,
            )
            draw.text(
                (ux + 20, uy + 8), url, font=mono,
                fill=tuple(int(WHITE[j] * url_alpha * 0.8) for j in range(3)),
            )

        img = add_scanlines(img, 0.04)
        img = add_grain(img, 6)
        return img

    render_pillow_clip(frame, output, duration)


# ── Art clips with Ken Burns ─────────────────────────────────────

def gen_art_kb_clip(
    image_path: str,
    output: str,
    duration: float = 1.5,
    zoom_start: float = 1.0,
    zoom_end: float = 1.12,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    color_grade: str = "dark",
):
    """Ken Burns on art image with cinematic grade."""
    src = Image.open(image_path).convert("RGB")

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        img = ken_burns_frame(src, t, zoom_start, zoom_end, pan_x, pan_y)

        if color_grade == "dark":
            # Crush blacks, desaturate slightly, add gold tint
            arr = np.array(img, dtype=np.float32)
            # Desaturate 20%
            gray = arr.mean(axis=2, keepdims=True)
            arr = arr * 0.8 + gray * 0.2
            # Gold tint in shadows
            mask = (gray < 80).astype(np.float32) * 0.15
            arr[..., 0] += mask[..., 0] * 30  # R
            arr[..., 1] += mask[..., 0] * 25  # G
            arr = np.clip(arr, 0, 255)
            img = Image.fromarray(arr.astype(np.uint8))
        elif color_grade == "warm":
            arr = np.array(img, dtype=np.float32)
            arr[..., 0] = np.clip(arr[..., 0] * 1.05, 0, 255)
            arr[..., 2] = np.clip(arr[..., 2] * 0.92, 0, 255)
            img = Image.fromarray(arr.astype(np.uint8))

        img = add_vignette(img, 0.5)
        img = add_grain(img, 10)
        img = add_scanlines(img, 0.06)
        return img

    render_pillow_clip(frame, output, duration)


# ── Mathematician portrait clips ──────────────────────────────────

def gen_portrait_clip(
    image_path: str,
    name: str,
    years: str,
    output: str,
    duration: float = 1.2,
):
    """Portrait with name/years overlay, Ken Burns, dark grade."""
    src = Image.open(image_path).convert("RGB")
    mono = load_font(MONO_FONT, 14)
    mono_name = load_font(MONO_MED, 18)

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        img = ken_burns_frame(src, t, 1.0, 1.08, -0.3, 0.2)

        # Cinematic dark grade
        arr = np.array(img, dtype=np.float32)
        gray = arr.mean(axis=2, keepdims=True)
        arr = arr * 0.65 + gray * 0.35  # partial desaturation
        arr = np.clip(arr * 0.85, 0, 255)  # darken
        img = Image.fromarray(arr.astype(np.uint8))
        img = add_vignette(img, 0.6)

        draw = ImageDraw.Draw(img)
        # Name label bottom-left
        name_alpha = max(0, min(1.0, (t - 0.15) * 4))
        fill = tuple(int(WHITE[j] * name_alpha) for j in range(3))
        gold_fill = tuple(int(GOLD[j] * name_alpha) for j in range(3))

        draw.text((80, H - 100), name.upper(), font=mono_name, fill=fill)
        draw.text((80, H - 75), years, font=mono, fill=gold_fill)

        img = add_scanlines(img, 0.07)
        img = add_grain(img, 12)
        return img

    render_pillow_clip(frame, output, duration)


# ── Platform UI B-roll ────────────────────────────────────────────

def gen_ui_clip(
    image_path: str,
    output: str,
    duration: float = 1.0,
    pan_dir: str = "right",
):
    """Platform UI screenshot with subtle pan and glow effect."""
    src = Image.open(image_path).convert("RGB")

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        px = 0.3 if pan_dir == "right" else -0.3
        img = ken_burns_frame(src, t, 1.02, 1.08, px, 0.1)

        # Slight blue tint for UI shots
        arr = np.array(img, dtype=np.float32)
        arr[..., 2] = np.clip(arr[..., 2] * 1.04, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))

        img = add_vignette(img, 0.3)
        img = add_scanlines(img, 0.04)
        img = add_grain(img, 6)
        return img

    render_pillow_clip(frame, output, duration)


# ── Data buffer / glitch overlay ──────────────────────────────────

def gen_data_buffer_clip(output: str, duration: float = 1.0):
    """Floating hex/binary data streams on dark background."""
    mono = load_font(MONO_FONT, 12)
    rng = random.Random(42)

    # Pre-generate data positions
    n_items = 120
    positions = [(rng.randint(20, W - 100), rng.randint(20, H - 30)) for _ in range(n_items)]
    speeds = [(rng.uniform(-0.3, 0.3), rng.uniform(0.5, 2.0)) for _ in range(n_items)]
    data_strs = [
        f"0x{rng.randint(0, 0xFFFF):04X}" if rng.random() > 0.5
        else f"{rng.uniform(40, 100):.2f}"
        for _ in range(n_items)
    ]
    flash_phases = [rng.uniform(0, 2 * math.pi) for _ in range(n_items)]

    def frame(i: int, total: int) -> Image.Image:
        t = i / max(total - 1, 1)
        img = make_bg()
        draw = ImageDraw.Draw(img)

        for j in range(n_items):
            x = int(positions[j][0] + speeds[j][0] * i)
            y = int((positions[j][1] + speeds[j][1] * i) % H)

            flash = 0.3 + 0.7 * max(0, math.sin(t * 8 + flash_phases[j]))
            if rng.random() < 0.02:
                flash = 1.0  # random flash

            alpha = flash * min(1.0, t * 4) * max(0, 1 - (t - 0.8) * 5 if t > 0.8 else 1)
            color_choice = rng.choice([GOLD, WHITE, ACCENT_BLUE, GAIN_GREEN])
            fill = tuple(int(color_choice[k] * alpha) for k in range(3))

            draw.text((x % W, y), data_strs[j], font=mono, fill=fill)

        img = add_scanlines(img, 0.1)
        return img

    render_pillow_clip(frame, output, duration)


# ── Chromatic aberration post-process ─────────────────────────────

def apply_chromatic_aberration(input_path: str, output_path: str, shift: int = 4):
    """Apply chromatic aberration via FFmpeg channel shift."""
    fc = (
        f"split=3[r][g][b];"
        f"[r]lutrgb=g=0:b=0,crop=iw-{shift}:ih:{shift}:0,pad=iw+{shift}:ih:0:0[rv];"
        f"[g]lutrgb=r=0:b=0[gv];"
        f"[b]lutrgb=r=0:g=0,crop=iw-{shift}:ih:0:0,pad=iw+{shift}:ih:{shift}:0[bv];"
        f"[rv][gv]blend=all_mode=addition[rg];"
        f"[rg][bv]blend=all_mode=addition"
    )
    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", input_path,
        "-vf", fc,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  chromatic aberration failed, copying original: {r.stderr[:200]}")
        shutil.copy2(input_path, output_path)


# ── Stochastic particles overlay ──────────────────────────────────

def gen_particle_clip(output: str, duration: float = 1.0):
    """Floating gold particles with organic motion (Perlin-like)."""
    n_particles = 200
    rng = np.random.RandomState(77)
    pos = rng.rand(n_particles, 2) * np.array([W, H])
    vel = rng.randn(n_particles, 2) * 0.5
    sizes = rng.uniform(1, 4, n_particles)
    brightness = rng.uniform(0.3, 1.0, n_particles)

    def frame(i: int, total: int) -> Image.Image:
        nonlocal pos
        t = i / max(total - 1, 1)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Perlin-like smooth motion via sine waves
        time_factor = i / FPS
        for j in range(n_particles):
            dx = math.sin(time_factor * 0.5 + j * 0.1) * 1.2
            dy = math.cos(time_factor * 0.3 + j * 0.07) * 0.8
            pos[j, 0] = (pos[j, 0] + dx + vel[j, 0]) % W
            pos[j, 1] = (pos[j, 1] + dy + vel[j, 1]) % H

            alpha_t = min(1.0, t * 3) * max(0, 1 - max(0, t - 0.85) * 7)
            a = int(brightness[j] * alpha_t * 180)
            s = int(sizes[j])
            x, y = int(pos[j, 0]), int(pos[j, 1])
            col = (*GOLD, a)
            draw.ellipse([x - s, y - s, x + s, y + s], fill=col)

        # Convert to RGB on dark bg
        bg = make_bg()
        bg.paste(img, (0, 0), img)
        return bg

    render_pillow_clip(frame, output, duration)


# ── Main generation ───────────────────────────────────────────────

def main():
    print("=== Generating v3 brand film clips ===\n")

    # 1. Typography cards
    print("[1/8] Typography cards...")
    cards = [
        {
            "headline": "Hedge geopolitical risk.",
            "subtitle": "Build conviction across Polymarket and Kalshi.",
            "label": "Indices",
            "output": str(CLIPS / "card_hedge.mp4"),
            "duration": 1.5,
        },
        {
            "headline": "Trade thematic repricing.",
            "subtitle": "",
            "label": "Execution",
            "output": str(CLIPS / "card_trade.mp4"),
            "duration": 1.2,
        },
        {
            "headline": "Construct custom baskets.",
            "subtitle": "Build custom indices across Polymarket and\nKalshi. Track them like products.",
            "label": "Construction",
            "output": str(CLIPS / "card_construct.mp4"),
            "duration": 1.5,
        },
    ]
    for c in cards:
        gen_typography_card(c["headline"], c["subtitle"], c["label"], c["output"], c["duration"])

    # 2. Endcard
    print("[2/8] Endcard...")
    gen_endcard(str(CLIPS / "endcard.mp4"), duration=2.5)

    # 3. Japanese art clips
    print("[3/8] Japanese art Ken Burns...")
    art_clips = [
        (ART / "ito-fuji-red.webp", "art_fuji_red.mp4", 1.2, 1.0, 1.1, 0.2, -0.1, "warm"),
        (ART / "gold_screen_plum.jpg", "art_gold_screen.mp4", 1.2, 1.0, 1.12, -0.3, 0.0, "warm"),
        (ART / "winter_fuji.jpg", "art_winter_fuji.mp4", 1.0, 1.0, 1.08, 0.1, -0.2, "dark"),
        (ART / "peony_garden_screen.jpg", "art_peony.mp4", 1.0, 1.0, 1.1, 0.2, 0.1, "warm"),
        (ART / "mudcloth_pattern.jpg", "art_mudcloth.mp4", 0.8, 1.0, 1.15, 0.0, 0.3, "dark"),
    ]
    for path, name, dur, zs, ze, px, py, grade in art_clips:
        if path.exists():
            gen_art_kb_clip(str(path), str(CLIPS / name), dur, zs, ze, px, py, grade)
        else:
            print(f"  SKIP: {path} not found")

    # 4. Mathematician portraits
    print("[4/8] Mathematician portraits...")
    portraits = [
        (STILLS / "ito.jpg", "Kiyoshi Ito", "1915-2008", "portrait_ito.mp4", 1.2),
        (STILLS / "euler.jpg", "Leonhard Euler", "1707-1783", "portrait_euler.mp4", 1.0),
        (STILLS / "riemann.jpg", "Bernhard Riemann", "1826-1866", "portrait_riemann.mp4", 1.0),
        (STILLS / "al_khwarizmi.jpg", "Al-Khwarizmi", "c. 780-850", "portrait_alkhwarizmi.mp4", 1.0),
        (STILLS / "jim_simons.jpg", "Jim Simons", "1938-2024", "portrait_simons.mp4", 1.0),
    ]
    for path, name, years, outname, dur in portraits:
        if path.exists():
            gen_portrait_clip(str(path), name, years, str(CLIPS / outname), dur)
        else:
            print(f"  SKIP: {path} not found")

    # 5. Platform UI B-roll
    print("[5/8] Platform UI clips...")
    ui_clips = [
        ("ui_index_dash.jpg", "ui_dash.mp4", 1.0, "right"),
        ("ui_trade_modal.jpg", "ui_trade.mp4", 1.0, "left"),
        ("ui_ai_tech_index.jpg", "ui_ai_index.mp4", 1.0, "right"),
        ("ui_construct_baskets.jpg", "ui_baskets.mp4", 1.0, "left"),
        ("ui_dashboard_strategies.jpg", "ui_strategies.mp4", 1.0, "right"),
        ("ui_all_indices.jpg", "ui_indices.mp4", 1.0, "left"),
        ("ui_endcard.jpg", "ui_logo_shot.mp4", 1.0, "right"),
    ]
    for src_name, out_name, dur, pan in ui_clips:
        src_path = REF_BROLL / src_name
        if src_path.exists():
            gen_ui_clip(str(src_path), str(CLIPS / out_name), dur, pan)
        else:
            print(f"  SKIP: {src_path} not found")

    # 6. Data buffer overlay
    print("[6/8] Data buffer...")
    gen_data_buffer_clip(str(CLIPS / "data_buffer.mp4"), duration=1.2)

    # 7. Gold particles
    print("[7/8] Gold particles...")
    gen_particle_clip(str(CLIPS / "particles.mp4"), duration=1.0)

    # 8. Apply chromatic aberration to select clips
    print("[8/8] Post-processing chromatic aberration...")
    ca_targets = ["data_buffer.mp4", "card_trade.mp4"]
    for name in ca_targets:
        src = CLIPS / name
        if src.exists():
            tmp = str(src) + ".tmp.mp4"
            apply_chromatic_aberration(str(src), tmp, shift=3)
            os.replace(tmp, str(src))
            print(f"  CA applied: {name}")

    print(f"\nAll v3 clips generated in {CLIPS}/")
    print(f"Total clips: {len(list(CLIPS.glob('*.mp4')))}")


if __name__ == "__main__":
    main()
