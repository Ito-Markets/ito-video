#!/usr/bin/env python3
"""Generate Itô Research Grant announcement video — 15-30s.

Aesthetic: Oppenheimer-level quiet intensity. Deep negative space.
B&W/sepia with single gold accent. Rule of thirds composition.
Contemplative pacing. Ancient textures meeting modern data.

Outputs:
  timeline/clips/001_void_gold_line.mp4 ... 013_endcard.mp4
  timeline/audio/music_stem.mp3
  timeline/edl.json
  out/ito_research_grant.mp4  (reference assembly)
"""

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Brand constants ──────────────────────────────────────────────────
W, H = 1920, 1080
FPS = 30
BG = (10, 14, 23)          # #0A0E17
WHITE = (232, 228, 222)     # #E8E4DE
GOLD = (141, 122, 80)       # #8D7A50
DARK_GOLD = (100, 86, 56)
FAINT = (50, 48, 44)        # very dim text
INK = (17, 24, 39)          # #111827

REPO = Path("/home/ubuntu/repos/ito-video")
FONT_BASK = str(REPO / "assets/fonts/LibreBaskerville.ttf")
FONT_BASK_ITALIC = str(REPO / "assets/fonts/LibreBaskerville.ttf")
FONT_BASK_BOLD = str(REPO / "assets/fonts/LibreBaskerville.ttf")
FONT_MONO = str(REPO / "assets/fonts/IBMPlexMono-Regular.ttf")
FONT_MONO_LIGHT = str(REPO / "assets/fonts/IBMPlexMono-Light.ttf")
FONT_MONO_MEDIUM = str(REPO / "assets/fonts/IBMPlexMono-Medium.ttf")
FONT_MONO_BOLD = str(REPO / "assets/fonts/IBMPlexMono-Bold.ttf")

CLIPS_DIR = REPO / "timeline" / "clips"
AUDIO_DIR = REPO / "timeline" / "audio"
OUT_DIR = REPO / "out"

# Rule of thirds grid positions
THIRD_X1 = W // 3          # 640
THIRD_X2 = 2 * W // 3      # 1280
THIRD_Y1 = H // 3          # 360
THIRD_Y2 = 2 * H // 3      # 720


def ensure_dirs():
    for d in [CLIPS_DIR, AUDIO_DIR, OUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def make_bg(opacity_texture=0.0, texture_img=None):
    """Create background frame with optional texture overlay."""
    img = Image.new("RGB", (W, H), BG)
    if texture_img and opacity_texture > 0:
        tex = texture_img.copy().resize((W, H), Image.LANCZOS)
        tex = tex.convert("L")  # grayscale
        tex_rgb = Image.merge("RGB", [tex, tex, tex])
        # Blend at low opacity
        from PIL import ImageChops
        blended = Image.blend(img, tex_rgb, opacity_texture)
        return blended
    return img


def add_grain(img, intensity=12):
    """Add subtle film grain."""
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, intensity, arr.shape).astype(np.float32)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def add_vignette(img, strength=0.4):
    """Add radial vignette darkening."""
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - strength * (dist / max_dist) ** 2
    vignette = np.clip(vignette, 0, 1)
    arr *= vignette[:, :, np.newaxis]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def text_with_tracking(draw, pos, text, font, fill, tracking=0):
    """Draw text with letter-spacing (tracking)."""
    x, y = pos
    for ch in text:
        bbox = font.getbbox(ch)
        draw.text((x, y), ch, font=font, fill=fill)
        char_w = bbox[2] - bbox[0]
        x += char_w + tracking


def get_text_width_tracked(text, font, tracking=0):
    """Calculate total width of tracked text."""
    total = 0
    for i, ch in enumerate(text):
        bbox = font.getbbox(ch)
        total += bbox[2] - bbox[0]
        if i < len(text) - 1:
            total += tracking
    return total


def ease_in_out(t):
    """Smooth ease-in-out."""
    return t * t * (3 - 2 * t)


def ease_out(t):
    """Smooth ease-out."""
    return 1 - (1 - t) ** 3


def frames_to_mp4(frames_dir, output_path, fps=FPS):
    """Encode frames directory to mp4."""
    subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", f"{frames_dir}/frame_%05d.png",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path)
    ], check=True)


def gen_clip(name, duration, frame_func):
    """Generate a clip from a frame function."""
    n_frames = int(duration * FPS)
    tmp = Path(f"/tmp/clip_{name}")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    for i in range(n_frames):
        t = i / n_frames  # 0..1 progress
        frame = frame_func(i, t, n_frames)
        frame = add_grain(frame, intensity=8)
        frame.save(tmp / f"frame_{i:05d}.png")

    out_path = CLIPS_DIR / f"{name}.mp4"
    frames_to_mp4(tmp, out_path)
    shutil.rmtree(tmp)
    print(f"  ✓ {name}.mp4 ({duration:.1f}s, {n_frames} frames)")
    return out_path


# ── Load textures ────────────────────────────────────────────────────
def load_scroll_texture():
    """Load Japanese scroll art for background texture."""
    poster = REPO / "assets/art/scroll-video-poster.jpg"
    if poster.exists():
        return Image.open(poster).convert("RGB")
    return None

def load_ito_portrait():
    """Load Kiyoshi Itô portrait."""
    p = REPO / "assets/stills/ito.jpg"
    if p.exists():
        return Image.open(p).convert("RGB")
    return None

def load_gold_screen():
    """Load gold screen art for texture."""
    p = REPO / "assets/art/gold_screen_plum.jpg"
    if p.exists():
        return Image.open(p).convert("RGB")
    return None

def load_logo():
    """Load Itô logo PNG."""
    p = REPO / "assets/brand/ito_lockup_horizontal_transparent.png"
    if p.exists():
        return Image.open(p).convert("RGBA")
    return None


# ═══════════════════════════════════════════════════════════════════════
# CLIP GENERATORS
# ═══════════════════════════════════════════════════════════════════════

def gen_001_void_gold_line():
    """Pure black void. A single gold line draws across lower third."""
    duration = 3.0

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Gold line at lower third (y = 720)
        line_y = THIRD_Y2
        line_start_x = int(W * 0.15)
        line_end_x = int(W * 0.85)

        # Line draws from left to right with ease
        progress = ease_in_out(min(t / 0.7, 1.0))  # complete by 70% of clip
        current_x = line_start_x + int((line_end_x - line_start_x) * progress)

        if progress > 0.01:
            draw.line(
                [(line_start_x, line_y), (current_x, line_y)],
                fill=GOLD, width=2
            )
            # Subtle glow at the leading edge
            if progress < 0.98:
                for r in range(1, 6):
                    alpha = max(0, 40 - r * 8)
                    glow_color = (
                        GOLD[0], GOLD[1], GOLD[2]
                    )
                    draw.ellipse(
                        [current_x - r, line_y - r, current_x + r, line_y + r],
                        fill=glow_color
                    )

        return img

    return gen_clip("001_void_gold_line", duration, frame_func)


def gen_002_grant_title():
    """ITÔ RESEARCH GRANT — small caps, wide tracking, fades in."""
    duration = 2.5
    scroll_tex = load_scroll_texture()

    font = load_font(FONT_MONO_MEDIUM, 28)
    font_sub = load_font(FONT_MONO_LIGHT, 18)

    def frame_func(i, t, n):
        tex_opacity = 0.04 if scroll_tex else 0
        img = make_bg(tex_opacity, scroll_tex)
        draw = ImageDraw.Draw(img)

        alpha = ease_out(min(t / 0.5, 1.0))

        text = "I T Ô   R E S E A R C H   G R A N T"
        text_color = (
            int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
            int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
            int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
        )

        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = THIRD_Y1

        draw.text((x, y), text, font=font, fill=text_color)

        # Subtitle
        if t > 0.3:
            sub_alpha = ease_out(min((t - 0.3) / 0.4, 1.0)) * 0.6
            sub_c = (
                int(WHITE[0] * sub_alpha + BG[0] * (1 - sub_alpha)),
                int(WHITE[1] * sub_alpha + BG[1] * (1 - sub_alpha)),
                int(WHITE[2] * sub_alpha + BG[2] * (1 - sub_alpha)),
            )
            sub = "Open data for prediction market research."
            sbbox = font_sub.getbbox(sub)
            stw = sbbox[2] - sbbox[0]
            draw.text(((W - stw) // 2, y + 50), sub, font=font_sub, fill=sub_c)

        # Gold line at lower third
        line_y = THIRD_Y2
        line_c = (int(GOLD[0] * alpha * 0.5), int(GOLD[1] * alpha * 0.5), int(GOLD[2] * alpha * 0.5))
        draw.line([(int(W * 0.3), line_y), (int(W * 0.7), line_y)], fill=line_c, width=1)

        img = add_vignette(img, 0.25)
        return img

    return gen_clip("002_grant_title", duration, frame_func)


def gen_003_problem():
    """'Most of the data is inaccessible.' — contemplative typography."""
    duration = 3.0

    font_main = load_font(FONT_BASK_ITALIC, 72)
    font_label = load_font(FONT_MONO_LIGHT, 16)

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        alpha = ease_out(min(t / 0.35, 1.0))

        text = "Most of the data"
        text2 = "is inaccessible."

        text_color = (
            int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
            int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
            int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
        )

        x = int(W * 0.12)
        y_center = H // 2
        y1 = y_center - 50
        y2 = y_center + 30

        draw.text((x, y1), text, font=font_main, fill=text_color)
        draw.text((x, y2), text2, font=font_main, fill=text_color)

        # Section label
        label_alpha = ease_out(min(t / 0.25, 1.0))
        label_color = (
            int(GOLD[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(GOLD[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(GOLD[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        draw.text((x, y1 - 60), "THE PROBLEM", font=font_label, fill=label_color)

        img = add_vignette(img, 0.25)
        return img

    return gen_clip("003_problem", duration, frame_func)


def gen_004_scroll_texture():
    """Japanese scroll art with heavy dark overlay. Slow Ken Burns."""
    duration = 2.5
    scroll_tex = load_scroll_texture()
    gold_tex = load_gold_screen()

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)

        if scroll_tex:
            # Ken Burns: slow zoom 1.0 -> 1.08
            scale = 1.0 + 0.08 * ease_in_out(t)
            tex = scroll_tex.copy()
            tw, th = tex.size
            new_w = int(tw * scale)
            new_h = int(th * scale)
            tex = tex.resize((new_w, new_h), Image.LANCZOS)

            # Center crop to fill frame
            crop_x = (new_w - W) // 2
            crop_y = (new_h - H) // 2
            # Ensure dimensions are sufficient
            if new_w >= W and new_h >= H:
                tex = tex.crop((crop_x, crop_y, crop_x + W, crop_y + H))
            else:
                # Scale up to fill
                ratio = max(W / new_w, H / new_h)
                tex = tex.resize((int(new_w * ratio) + 1, int(new_h * ratio) + 1), Image.LANCZOS)
                new_w2, new_h2 = tex.size
                crop_x2 = (new_w2 - W) // 2
                crop_y2 = (new_h2 - H) // 2
                tex = tex.crop((crop_x2, crop_y2, crop_x2 + W, crop_y2 + H))

            # Convert to sepia tone
            tex = tex.convert("L")
            tex_arr = np.array(tex, dtype=np.float32)
            # Sepia toning
            r = np.clip(tex_arr * 0.393 + 50, 0, 255)
            g = np.clip(tex_arr * 0.349 + 40, 0, 255)
            b = np.clip(tex_arr * 0.272 + 30, 0, 255)
            sepia = np.stack([r, g, b], axis=-1).astype(np.uint8)
            tex_sepia = Image.fromarray(sepia)

            # Heavy dark overlay — only 15-20% visible
            img = Image.blend(img, tex_sepia, 0.18)

        # Fade in and out
        fade = 1.0
        if t < 0.15:
            fade = ease_out(t / 0.15)
        elif t > 0.85:
            fade = ease_out((1 - t) / 0.15)

        if fade < 1.0:
            black = Image.new("RGB", (W, H), BG)
            img = Image.blend(black, img, fade)

        img = add_vignette(img, 0.5)
        return img

    return gen_clip("004_scroll_texture", duration, frame_func)


def gen_005_offerings():
    """Three offerings appearing in sequence with gold dashes."""
    duration = 3.5

    font = load_font(FONT_MONO, 36)
    font_label = load_font(FONT_MONO_LIGHT, 16)

    offerings = [
        "L2 orderbooks.",
        "Basket indices.",
        "Hosted backtesting.",
    ]

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        label_alpha = ease_out(min(t / 0.2, 1.0))
        label_color = (
            int(GOLD[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(GOLD[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(GOLD[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        x_base = int(W * 0.12)
        draw.text((x_base, THIRD_Y1 - 80), "WHAT THE GRANT PROVIDES",
                   font=font_label, fill=label_color)

        for idx, text in enumerate(offerings):
            appear_t = 0.10 + idx * 0.20
            if t < appear_t:
                continue

            line_t = (t - appear_t) / max(1 - appear_t, 0.01)
            alpha = ease_out(min(line_t / 0.25, 1.0))

            text_color = (
                int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
                int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
                int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
            )
            gold_color = (
                int(GOLD[0] * alpha + BG[0] * (1 - alpha)),
                int(GOLD[1] * alpha + BG[1] * (1 - alpha)),
                int(GOLD[2] * alpha + BG[2] * (1 - alpha)),
            )

            y = THIRD_Y1 - 30 + idx * 70
            draw.text((x_base, y), "—", font=font, fill=gold_color)
            draw.text((x_base + 60, y), text, font=font, fill=text_color)

        img = add_vignette(img, 0.2)
        return img

    return gen_clip("005_offerings", duration, frame_func)


def gen_006_brownian():
    """Brownian motion paths in gold on deep black.
    Mathematical, organic, alive — using NumPy vectorized paths."""
    duration = 2.5

    np.random.seed(42)
    n_paths = 12
    n_steps = 300
    paths = []
    for _ in range(n_paths):
        start_x = np.random.uniform(W * 0.2, W * 0.8)
        start_y = np.random.uniform(H * 0.2, H * 0.8)
        x = np.cumsum(np.random.normal(0, 4.0, n_steps)) + start_x
        y = np.cumsum(np.random.normal(0, 2.5, n_steps)) + start_y
        paths.append((x, y))

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        for path_idx, (px, py) in enumerate(paths):
            path_delay = path_idx * 0.04
            path_reveal = int(n_steps * ease_in_out(
                min(max(t - path_delay, 0) / 0.75, 1.0)
            ))
            if path_reveal < 2:
                continue

            for j in range(1, path_reveal):
                seg_alpha = 0.4 + 0.6 * (j / path_reveal)
                c = (
                    int(GOLD[0] * seg_alpha),
                    int(GOLD[1] * seg_alpha),
                    int(GOLD[2] * seg_alpha),
                )
                x1, y1 = int(px[j-1]), int(py[j-1])
                x2, y2 = int(px[j]), int(py[j])
                draw.line([(x1, y1), (x2, y2)], fill=c, width=2)

            # Bright dot at tip
            if path_reveal > 0:
                tx, ty = int(px[path_reveal-1]), int(py[path_reveal-1])
                draw.ellipse([tx-3, ty-3, tx+3, ty+3], fill=WHITE)

        # SDE formula bottom-right
        font_formula = load_font(FONT_MONO_LIGHT, 18)
        formula_alpha = ease_out(min(t / 0.4, 1.0)) * 0.5
        fc = (
            int(WHITE[0] * formula_alpha + BG[0] * (1 - formula_alpha)),
            int(WHITE[1] * formula_alpha + BG[1] * (1 - formula_alpha)),
            int(WHITE[2] * formula_alpha + BG[2] * (1 - formula_alpha)),
        )
        draw.text((W - 400, H - 50), "dS = \u03bcS dt + \u03c3S dW", font=font_formula, fill=fc)

        img = add_vignette(img, 0.3)
        return img

    return gen_clip("006_brownian", duration, frame_func)


def gen_007_endpoints():
    """'23 endpoints.' — large, centered, authoritative."""
    duration = 3.0

    font_big = load_font(FONT_BASK, 120)
    font_sub = load_font(FONT_MONO_LIGHT, 24)

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        alpha = ease_out(min(t / 0.3, 1.0))

        num_color = (
            int(GOLD[0] * alpha + BG[0] * (1 - alpha)),
            int(GOLD[1] * alpha + BG[1] * (1 - alpha)),
            int(GOLD[2] * alpha + BG[2] * (1 - alpha)),
        )
        word_color = (
            int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
            int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
            int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
        )

        full_text = "23 endpoints."
        bbox = font_big.getbbox(full_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = (H - th) // 2 - 40

        bbox_num = font_big.getbbox("23 ")
        draw.text((x, y), "23 ", font=font_big, fill=num_color)
        draw.text((x + bbox_num[2] - bbox_num[0], y), "endpoints.",
                   font=font_big, fill=word_color)

        sub_t = max(0, (t - 0.4) / 0.6)
        if sub_t > 0:
            sub_alpha = ease_out(min(sub_t / 0.35, 1.0))
            sub_color = (
                int(WHITE[0] * sub_alpha * 0.7 + BG[0] * (1 - sub_alpha * 0.7)),
                int(WHITE[1] * sub_alpha * 0.7 + BG[1] * (1 - sub_alpha * 0.7)),
                int(WHITE[2] * sub_alpha * 0.7 + BG[2] * (1 - sub_alpha * 0.7)),
            )
            sub_text = "Same data plane as the institutional dashboard."
            sub_bbox = font_sub.getbbox(sub_text)
            sub_tw = sub_bbox[2] - sub_bbox[0]
            sub_x = (W - sub_tw) // 2
            draw.text((sub_x, y + th + 50), sub_text,
                       font=font_sub, fill=sub_color)

        img = add_vignette(img, 0.2)
        return img

    return gen_clip("007_endpoints", duration, frame_func)


def gen_008_audience():
    """Words appear one by one, centered, each replacing the previous."""
    duration = 3.0

    words = ["Researchers.", "Students.", "Quants.", "Builders."]
    font = load_font(FONT_BASK, 80)
    font_label = load_font(FONT_MONO_LIGHT, 14)

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Section label
        label_alpha = ease_out(min(t / 0.15, 1.0))
        label_color = (
            int(GOLD[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(GOLD[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(GOLD[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        draw.text((int(W * 0.12), THIRD_Y1 - 80), "WHO SHOULD APPLY",
                   font=font_label, fill=label_color)

        # Each word gets ~25% of the timeline
        word_duration = 1.0 / len(words)
        current_idx = min(int(t / word_duration), len(words) - 1)
        word_t = (t - current_idx * word_duration) / word_duration

        word = words[current_idx]

        # Fade in for first 30% of word's time, hold, fade slightly at transition
        if word_t < 0.25:
            alpha = ease_out(word_t / 0.25)
        elif word_t > 0.85 and current_idx < len(words) - 1:
            alpha = ease_out((1 - word_t) / 0.15)
        else:
            alpha = 1.0

        text_color = (
            int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
            int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
            int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
        )

        bbox = font.getbbox(word)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = (H - th) // 2

        draw.text((x, y), word, font=font, fill=text_color)

        img = add_vignette(img, 0.25)
        return img

    return gen_clip("008_audience", duration, frame_func)


def gen_009_research_areas():
    """Research areas of interest — scrolling list with quiet authority."""
    duration = 3.5
    scroll_tex = load_scroll_texture()

    font = load_font(FONT_MONO, 18)
    font_label = load_font(FONT_MONO_LIGHT, 14)

    areas = [
        "Cross-venue price discovery",
        "Basket construction methodologies",
        "Volatility estimation and risk factor models",
        "Market-neutral execution strategies",
        "Information aggregation efficiency",
    ]

    def frame_func(i, t, n):
        tex_opacity = 0.05 if scroll_tex else 0
        img = make_bg(tex_opacity, scroll_tex)
        draw = ImageDraw.Draw(img)

        # Section label
        label_alpha = ease_out(min(t / 0.2, 1.0))
        label_color = (
            int(GOLD[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(GOLD[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(GOLD[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        x_base = int(W * 0.12)
        draw.text((x_base, THIRD_Y1 - 80), "RESEARCH AREAS OF INTEREST",
                   font=font_label, fill=label_color)

        for idx, area in enumerate(areas):
            appear_t = 0.08 + idx * 0.12
            if t < appear_t:
                continue
            line_t = (t - appear_t) / max(1 - appear_t, 0.01)
            alpha = ease_out(min(line_t / 0.3, 1.0))

            text_color = (
                int(WHITE[0] * alpha * 0.85 + BG[0] * (1 - alpha * 0.85)),
                int(WHITE[1] * alpha * 0.85 + BG[1] * (1 - alpha * 0.85)),
                int(WHITE[2] * alpha * 0.85 + BG[2] * (1 - alpha * 0.85)),
            )
            gold_c = (
                int(GOLD[0] * alpha + BG[0] * (1 - alpha)),
                int(GOLD[1] * alpha + BG[1] * (1 - alpha)),
                int(GOLD[2] * alpha + BG[2] * (1 - alpha)),
            )

            y = THIRD_Y1 - 30 + idx * 48
            # Small gold dot
            draw.ellipse([x_base, y + 8, x_base + 5, y + 13], fill=gold_c)
            draw.text((x_base + 22, y), area, font=font, fill=text_color)

        img = add_vignette(img, 0.3)
        return img

    return gen_clip("009_research_areas", duration, frame_func)


def gen_010_ito_portrait():
    """Kiyoshi Itô portrait — B&W, slow Ken Burns, heavy vignette."""
    duration = 2.5
    portrait = load_ito_portrait()

    font = load_font(FONT_MONO_LIGHT, 14)

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)

        if portrait:
            # Ken Burns: slow zoom 1.0 -> 1.06, slight upward pan
            scale = 1.0 + 0.06 * t
            p = portrait.copy()

            # Convert to grayscale
            p = p.convert("L")

            pw, ph = p.size
            # Scale to fill frame width
            aspect = pw / ph
            if aspect > W / H:
                new_h = int(H * scale)
                new_w = int(new_h * aspect)
            else:
                new_w = int(W * scale)
                new_h = int(new_w / aspect)

            p = p.resize((new_w, new_h), Image.LANCZOS)

            # Center + slight pan
            pan_y = int(15 * t)
            crop_x = max(0, (new_w - W) // 2)
            crop_y = max(0, (new_h - H) // 2 - pan_y)
            p = p.crop((crop_x, crop_y, crop_x + W, crop_y + H))

            # Ensure correct size
            if p.size != (W, H):
                p = p.resize((W, H), Image.LANCZOS)

            # Sepia tone
            p_arr = np.array(p, dtype=np.float32)
            r = np.clip(p_arr * 0.35 + BG[0], 0, 255)
            g = np.clip(p_arr * 0.32 + BG[1], 0, 255)
            b = np.clip(p_arr * 0.27 + BG[2], 0, 255)
            sepia = np.stack([r, g, b], axis=-1).astype(np.uint8)
            p_sepia = Image.fromarray(sepia)

            # Blend — portrait visible but subdued
            img = Image.blend(img, p_sepia, 0.65)

        # Name label bottom left
        draw = ImageDraw.Draw(img)
        label_alpha = ease_out(min(max(t - 0.3, 0) / 0.3, 1.0)) * 0.7
        label_c = (
            int(WHITE[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(WHITE[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(WHITE[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        draw.text((int(W * 0.12), H - 80),
                   "Kiyoshi Itô, 1915–2008", font=font, fill=label_c)

        img = add_vignette(img, 0.40)

        # Fade in/out
        fade = 1.0
        if t < 0.12:
            fade = ease_out(t / 0.12)
        elif t > 0.88:
            fade = ease_out((1 - t) / 0.12)
        if fade < 1.0:
            black = Image.new("RGB", (W, H), BG)
            img = Image.blend(black, img, fade)

        return img

    return gen_clip("010_ito_portrait", duration, frame_func)


def gen_011_api_scopes():
    """API scopes in monospace — technical authority."""
    duration = 3.0

    font = load_font(FONT_MONO, 22)
    font_label = load_font(FONT_MONO_LIGHT, 14)

    scopes = [
        "baskets:read",
        "markets:read",
        "backtests:read",
        "backtests:write",
    ]

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Label
        label_alpha = ease_out(min(t / 0.2, 1.0))
        label_color = (
            int(GOLD[0] * label_alpha + BG[0] * (1 - label_alpha)),
            int(GOLD[1] * label_alpha + BG[1] * (1 - label_alpha)),
            int(GOLD[2] * label_alpha + BG[2] * (1 - label_alpha)),
        )
        x_base = int(W * 0.12)
        draw.text((x_base, THIRD_Y1 - 60), "API ACCESS",
                   font=font_label, fill=label_color)

        for idx, scope in enumerate(scopes):
            appear_t = 0.1 + idx * 0.15
            if t < appear_t:
                continue
            line_t = (t - appear_t) / max(1 - appear_t, 0.01)
            alpha = ease_out(min(line_t / 0.25, 1.0))

            # Scopes in gold monospace
            scope_color = (
                int(GOLD[0] * alpha + BG[0] * (1 - alpha)),
                int(GOLD[1] * alpha + BG[1] * (1 - alpha)),
                int(GOLD[2] * alpha + BG[2] * (1 - alpha)),
            )

            y = THIRD_Y1 + idx * 50
            draw.text((x_base, y), scope, font=font, fill=scope_color)

        # Rate limit text appears late
        if t > 0.6:
            sub_alpha = ease_out(min((t - 0.6) / 0.3, 1.0)) * 0.5
            sub_c = (
                int(WHITE[0] * sub_alpha + BG[0] * (1 - sub_alpha)),
                int(WHITE[1] * sub_alpha + BG[1] * (1 - sub_alpha)),
                int(WHITE[2] * sub_alpha + BG[2] * (1 - sub_alpha)),
            )
            font_tiny = load_font(FONT_MONO_LIGHT, 14)
            draw.text((x_base, THIRD_Y1 + 4 * 50 + 20),
                       "120 reads/min  ·  10 writes/min",
                       font=font_tiny, fill=sub_c)

        img = add_vignette(img, 0.3)
        return img

    return gen_clip("011_api_scopes", duration, frame_func)


def gen_012_url():
    """itomarkets.com/research-program — clean, definitive."""
    duration = 2.5

    font = load_font(FONT_MONO, 28)
    font_label = load_font(FONT_MONO_LIGHT, 14)

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        alpha = ease_out(min(t / 0.4, 1.0))

        # URL centered
        url = "itomarkets.com/research-program"
        bbox = font.getbbox(url)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = H // 2

        text_color = (
            int(WHITE[0] * alpha + BG[0] * (1 - alpha)),
            int(WHITE[1] * alpha + BG[1] * (1 - alpha)),
            int(WHITE[2] * alpha + BG[2] * (1 - alpha)),
        )

        draw.text((x, y), url, font=font, fill=text_color)

        # "Apply" label above
        label_color = (
            int(GOLD[0] * alpha + BG[0] * (1 - alpha)),
            int(GOLD[1] * alpha + BG[1] * (1 - alpha)),
            int(GOLD[2] * alpha + BG[2] * (1 - alpha)),
        )
        apply_text = "APPLY"
        abbox = font_label.getbbox(apply_text)
        atw = abbox[2] - abbox[0]
        draw.text(((W - atw) // 2, y - 40), apply_text,
                   font=font_label, fill=label_color)

        img = add_vignette(img, 0.25)
        return img

    return gen_clip("012_url", duration, frame_func)


def gen_013_endcard():
    """Itô MARKETS logo centered. Gold line completes. Fade to black."""
    duration = 3.5
    logo = load_logo()

    def frame_func(i, t, n):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Fade in
        fade_in = ease_out(min(t / 0.3, 1.0))

        # Logo
        if logo:
            l = logo.copy()
            lw, lh = l.size
            # Scale logo to reasonable size (max 400px wide)
            scale = min(400 / lw, 100 / lh)
            new_lw = int(lw * scale)
            new_lh = int(lh * scale)
            l = l.resize((new_lw, new_lh), Image.LANCZOS)

            # Apply fade by modifying alpha
            l_arr = np.array(l)
            l_arr[:, :, 3] = (l_arr[:, :, 3].astype(np.float32) * fade_in).astype(np.uint8)
            l = Image.fromarray(l_arr)

            # Center
            lx = (W - new_lw) // 2
            ly = (H - new_lh) // 2 - 20
            img.paste(l, (lx, ly), l)

        # Gold line below logo
        line_y = H // 2 + 50
        line_alpha = fade_in
        line_start = int(W * 0.35)
        line_end = int(W * 0.65)
        line_color = (
            int(GOLD[0] * line_alpha),
            int(GOLD[1] * line_alpha),
            int(GOLD[2] * line_alpha),
        )
        draw.line([(line_start, line_y), (line_end, line_y)],
                   fill=line_color, width=1)

        # Tagline below
        font_tag = load_font(FONT_MONO_LIGHT, 14)
        if t > 0.25:
            tag_alpha = ease_out(min((t - 0.25) / 0.3, 1.0)) * fade_in
            tag_c = (
                int(WHITE[0] * tag_alpha * 0.6 + BG[0] * (1 - tag_alpha * 0.6)),
                int(WHITE[1] * tag_alpha * 0.6 + BG[1] * (1 - tag_alpha * 0.6)),
                int(WHITE[2] * tag_alpha * 0.6 + BG[2] * (1 - tag_alpha * 0.6)),
            )
            tag = "Research infrastructure for prediction markets."
            tbbox = font_tag.getbbox(tag)
            ttw = tbbox[2] - tbbox[0]
            draw.text(((W - ttw) // 2, line_y + 25), tag,
                       font=font_tag, fill=tag_c)

        # Fade to black at end
        if t > 0.8:
            fade_out = ease_out((1 - t) / 0.2)
            black = Image.new("RGB", (W, H), BG)
            img = Image.blend(black, img, fade_out)

        img = add_vignette(img, 0.2)
        return img

    return gen_clip("013_endcard", duration, frame_func)


# ═══════════════════════════════════════════════════════════════════════
# AUDIO + ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════

def prepare_audio(total_duration):
    """Trim the music track to video duration and apply fade."""
    src = Path("/home/ubuntu/attachments/0d7dfa8c-ef5b-4866-9809-67704f5fb8c2/onlyHope_KLICKAUD.mp3")
    out = AUDIO_DIR / "music_stem.mp3"

    if not src.exists():
        print("  ⚠ Music file not found, skipping audio")
        return None

    # Take the first section of the track, apply fade in/out
    subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-i", str(src),
        "-t", f"{total_duration:.2f}",
        "-af", f"afade=t=in:d=1.5,afade=t=out:st={total_duration - 2:.2f}:d=2,"
               f"volume=0.7",
        "-ar", "44100", "-ac", "2", "-b:a", "192k",
        str(out)
    ], check=True)
    print(f"  ✓ music_stem.mp3 ({total_duration:.1f}s)")
    return out


def write_edl(clips_info, total_duration):
    """Write edit decision list for post-editing."""
    edl_clips = []
    for clip in clips_info:
        file_path = Path(clip["file"])
        if file_path.is_absolute():
            rel_path = file_path.relative_to(REPO)
        else:
            rel_path = file_path
        edl_clip = {
            "id": clip["id"],
            "file": str(rel_path),
            "duration": clip["duration"],
        }
        if "in_point" in clip:
            edl_clip["in_point"] = clip["in_point"]
            edl_clip["out_point"] = clip["out_point"]
        edl_clips.append(edl_clip)

    edl = {
        "project": "Itô Research Grant — Announcement",
        "resolution": {"width": W, "height": H},
        "fps": FPS,
        "total_duration": total_duration,
        "reference_assembly": "out/ito_research_grant.mp4",
        "color_palette": {
            "background": "#0A0E17",
            "white": "#E8E4DE",
            "gold": "#8D7A50",
            "ink": "#111827",
        },
        "fonts": {
            "serif": "Libre Baskerville",
            "mono": "IBM Plex Mono",
        },
        "audio": {
            "music": "timeline/audio/music_stem.mp3",
            "note": "onlyHope by KLICKAUD — trim/adjust in post as needed",
        },
        "clips": edl_clips,
    }

    edl_path = REPO / "timeline" / "edl.json"
    with open(edl_path, "w") as f:
        json.dump(edl, f, indent=2)
    print(f"  ✓ edl.json")
    return edl_path


def assemble_reference(clips_info, audio_path, total_duration):
    """Build reference assembly MP4 with crossfades."""
    # Simple concatenation with short crossfades for the reference cut
    clip_paths = [c["file"] for c in clips_info]

    # Build concat file
    concat_path = REPO / "timeline" / "concat.txt"
    with open(concat_path, "w") as f:
        for cp in clip_paths:
            f.write(f"file '{cp}'\n")

    # First concat without transitions for simplicity,
    # then add audio
    concat_out = OUT_DIR / "ito_research_grant_noaudio.mp4"
    subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_path),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(concat_out)
    ], check=True)

    # Now build with xfade transitions for a polished reference
    final_out = OUT_DIR / "ito_research_grant.mp4"

    if len(clip_paths) < 2:
        shutil.copy(concat_out, final_out)
        return final_out

    # Build xfade chain
    xfade_dur = 0.2
    durations = [c["duration"] for c in clips_info]

    # For xfade assembly, build filter chain
    filter_parts = []
    inputs = []
    for idx, cp in enumerate(clip_paths):
        inputs.extend(["-i", cp])

    # Build xfade chain iteratively
    n = len(clip_paths)
    cumulative_offset = 0

    if n == 2:
        offset = durations[0] - xfade_dur
        filter_str = f"[0:v][1:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.3f}[outv]"
    else:
        prev = "[0:v]"
        parts = []
        for idx in range(1, n):
            cumulative_offset += durations[idx - 1] - xfade_dur
            next_in = f"[{idx}:v]"
            if idx < n - 1:
                out_label = f"[v{idx}]"
            else:
                out_label = "[outv]"
            parts.append(
                f"{prev}{next_in}xfade=transition=fade:duration={xfade_dur}:offset={cumulative_offset:.3f}{out_label}"
            )
            prev = out_label if idx < n - 1 else ""
            # Reset cumulative for xfade chain (each xfade eats time)
        # Actually xfade offset is from the START of the assembled stream
        # Recalculate properly
        parts = []
        offset = durations[0] - xfade_dur
        prev = "[0:v]"
        for idx in range(1, n):
            next_in = f"[{idx}:v]"
            if idx < n - 1:
                out_label = f"[v{idx}]"
            else:
                out_label = "[outv]"
            parts.append(
                f"{prev}{next_in}xfade=transition=fade:duration={xfade_dur}:offset={offset:.3f}{out_label}"
            )
            prev = out_label
            if idx < n - 1:
                offset += durations[idx] - xfade_dur
        filter_str = ";".join(parts)

    # Add audio if available
    if audio_path and audio_path.exists():
        inputs.extend(["-i", str(audio_path)])
        audio_idx = n
        vid_dur = sum(durations) - xfade_dur * (n - 1)
        filter_str += f";[{audio_idx}:a]atrim=0:{vid_dur:.3f},asetpts=PTS-STARTPTS[outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]"]
    else:
        map_args = ["-map", "[outv]"]

    cmd = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "warning",
        *inputs,
        "-filter_complex", filter_str,
        *map_args,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(final_out)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ xfade assembly failed, falling back to concat: {result.stderr[:200]}")
        # Fallback: concat with audio
        if audio_path and audio_path.exists():
            subprocess.run([
                "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                "-i", str(concat_out),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(final_out)
            ], check=True)
        else:
            shutil.copy(concat_out, final_out)

    # Clean up
    if concat_out.exists():
        concat_out.unlink()
    if concat_path.exists():
        concat_path.unlink()

    return final_out


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    ensure_dirs()

    print("═" * 60)
    print("  Itô Research Grant — Video Generation")
    print("  Aesthetic: Quiet intensity · Deep negative space")
    print("═" * 60)

    # Generate ALL clips (available for timeline post-editing)
    all_generators = [
        ("001_void_gold_line",    gen_001_void_gold_line,    3.0),
        ("002_grant_title",       gen_002_grant_title,       2.5),
        ("003_problem",           gen_003_problem,           3.0),
        ("004_scroll_texture",    gen_004_scroll_texture,    2.5),
        ("005_offerings",         gen_005_offerings,         3.5),
        ("006_brownian",          gen_006_brownian,          2.5),
        ("007_endpoints",         gen_007_endpoints,         3.0),
        ("008_audience",          gen_008_audience,          3.0),
        ("009_research_areas",    gen_009_research_areas,    3.5),
        ("010_ito_portrait",      gen_010_ito_portrait,      2.5),
        ("011_api_scopes",        gen_011_api_scopes,        3.0),
        ("012_url",               gen_012_url,               2.5),
        ("013_endcard",           gen_013_endcard,           3.5),
    ]

    all_clips_info = []
    print("\n▸ Generating all timeline clips...")
    for name, gen_func, duration in all_generators:
        path = gen_func()
        all_clips_info.append({
            "id": name,
            "file": str(path),
            "duration": duration,
        })

    # Reference assembly: tighter 9-clip cut for ~25s
    assembly_ids = [
        "001_void_gold_line",    # 3.0s  — void + gold line
        "002_grant_title",       # 2.5s  — identity
        "003_problem",           # 3.0s  — problem statement
        "005_offerings",         # 3.5s  — what you get
        "006_brownian",          # 2.5s  — mathematical beauty
        "007_endpoints",         # 3.0s  — hero stat
        "008_audience",          # 3.0s  — who it's for
        "012_url",               # 2.5s  — CTA
        "013_endcard",           # 3.5s  — logo resolve
    ]
    assembly_clips = [c for c in all_clips_info if c["id"] in assembly_ids]
    # Preserve order
    assembly_clips.sort(key=lambda c: assembly_ids.index(c["id"]))

    # Calculate timing for assembly
    xfade_dur = 0.2
    cumulative_time = 0.0
    for c in assembly_clips:
        c["in_point"] = round(cumulative_time, 3)
        c["out_point"] = round(cumulative_time + c["duration"], 3)
        cumulative_time += c["duration"]

    n_assembly = len(assembly_clips)
    total_duration = cumulative_time - xfade_dur * (n_assembly - 1)
    print(f"\n  Assembly: {total_duration:.1f}s ({n_assembly} clips)")
    print(f"  Timeline: {len(all_clips_info)} total clips available")

    # Prepare audio
    print("\n▸ Preparing audio...")
    audio_path = prepare_audio(total_duration)

    # Write EDL (includes ALL clips for timeline)
    print("\n▸ Writing EDL...")
    write_edl(all_clips_info, total_duration)

    # Assemble reference cut (tighter selection)
    print("\n▸ Assembling reference cut...")
    final = assemble_reference(assembly_clips, audio_path, total_duration)
    print(f"\n  ✓ Reference assembly: {final}")

    # Print ffprobe info
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "default=noprint_wrappers=1",
        str(final)
    ], capture_output=True, text=True)
    print(f"  {result.stdout.strip()}")

    print("\n═" * 60)
    print("  Timeline files:")
    print(f"    All clips:    timeline/clips/ ({len(all_clips_info)} clips)")
    print(f"    Assembly:     {n_assembly} clips, {total_duration:.1f}s")
    print(f"    Audio:        timeline/audio/music_stem.mp3")
    print(f"    EDL:          timeline/edl.json")
    print(f"    Reference:    out/ito_research_grant.mp4")
    print("═" * 60)


if __name__ == "__main__":
    main()
