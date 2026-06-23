#!/usr/bin/env python3
"""Generate polished Manim math animations for Ito brand film v3.

Produces:
  assets/gen/manim_ito_lemma.mp4      - Ito's lemma typeset + animate
  assets/gen/manim_stochastic_paths.mp4 - Brownian motion paths
  assets/gen/manim_sde.mp4            - SDE formula reveal
"""
import os
import subprocess
import shutil

OUTDIR = os.path.join(os.path.dirname(__file__), "assets", "gen")
os.makedirs(OUTDIR, exist_ok=True)

# Brand colors
BG_COLOR = "#0A0E17"
GOLD = "#8D7A50"
WHITE = "#E8E4DE"
ACCENT_BLUE = "#365F92"

MANIM_SCRIPT = r'''
from manim import *
import numpy as np

BG = "{bg}"
GOLD = "{gold}"
WHITE = "{white}"
BLUE = "{blue}"

config.background_color = BG
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 30


class ItoLemma(Scene):
    """Ito's lemma formula reveal with elegant animation."""
    def construct(self):
        # Title label
        label = Text("ITO'S LEMMA", font_size=18, color=GOLD,
                      font="monospace").to_edge(UP, buff=0.5)
        label.set_opacity(0.7)

        # The formula
        formula = MathTex(
            r"df(X_t, t)",
            r"=",
            r"\frac{{\partial f}}{{\partial t}} \, dt",
            r"+",
            r"\frac{{\partial f}}{{\partial x}} \, dX_t",
            r"+",
            r"\frac{{1}}{{2}} \frac{{\partial^2 f}}{{\partial x^2}} \, (dX_t)^2",
            font_size=48,
            color=WHITE,
        )
        formula.move_to(ORIGIN)

        # Animate each piece
        self.play(Write(label), run_time=0.4)
        self.play(Write(formula[0]), Write(formula[1]), run_time=0.5)
        self.play(Write(formula[2]), run_time=0.4)
        self.play(Write(formula[3]), Write(formula[4]), run_time=0.4)
        self.play(Write(formula[5]), Write(formula[6]), run_time=0.5)

        # Gold highlight on the stochastic term
        box = SurroundingRectangle(formula[6], color=GOLD, buff=0.1)
        note = Text("stochastic correction", font_size=14, color=GOLD,
                     font="monospace").next_to(box, DOWN, buff=0.2)
        self.play(Create(box), FadeIn(note), run_time=0.4)
        self.wait(0.3)


class StochasticPaths(Scene):
    """Multiple Brownian motion sample paths with glow."""
    def construct(self):
        label = Text("BROWNIAN MOTION", font_size=18, color=GOLD,
                      font="monospace").to_edge(UP, buff=0.5)
        label.set_opacity(0.7)

        np.random.seed(42)
        n_paths = 8
        n_steps = 200
        dt = 0.02

        axes = Axes(
            x_range=[0, 4, 1], y_range=[-2, 2, 1],
            x_length=10, y_length=5,
            axis_config={{"color": GOLD, "stroke_width": 1}},
        ).move_to(ORIGIN + DOWN * 0.3)

        colors = [WHITE, GOLD, BLUE, "#6B8DA0", "#A08D6B",
                  "#8DA06B", "#6BA08D", "#A06B8D"]

        paths = []
        for i in range(n_paths):
            x_vals = np.linspace(0, 4, n_steps)
            increments = np.random.normal(0, np.sqrt(dt), n_steps)
            y_vals = np.cumsum(increments)
            y_vals = y_vals - y_vals[0]  # start at 0

            line = axes.plot_line_graph(
                x_values=x_vals, y_values=y_vals,
                add_vertex_dots=False,
                line_color=colors[i % len(colors)],
                stroke_width=1.5 if i > 0 else 2.5,
            )
            if i > 0:
                line.set_opacity(0.5)
            paths.append(line)

        self.play(Write(label), Create(axes), run_time=0.5)
        # Animate paths appearing rapidly
        anims = [Create(p, run_time=0.8) for p in paths[:3]]
        self.play(*anims)
        anims2 = [Create(p, run_time=0.5) for p in paths[3:]]
        self.play(*anims2)
        self.wait(0.3)


class SDEReveal(Scene):
    """SDE formula with drift and diffusion terms highlighted."""
    def construct(self):
        label = Text("STOCHASTIC DIFFERENTIAL EQUATION", font_size=18,
                      color=GOLD, font="monospace").to_edge(UP, buff=0.5)
        label.set_opacity(0.7)

        sde = MathTex(
            r"dX_t", r"=", r"\mu(X_t, t)", r"\, dt",
            r"+", r"\sigma(X_t, t)", r"\, dW_t",
            font_size=56, color=WHITE,
        )
        sde.move_to(ORIGIN + UP * 0.5)

        drift_label = Text("drift", font_size=16, color=BLUE,
                           font="monospace")
        diffusion_label = Text("diffusion", font_size=16, color=GOLD,
                               font="monospace")

        # Color the terms
        sde[2].set_color(BLUE)
        sde[3].set_color(BLUE)
        sde[5].set_color(GOLD)
        sde[6].set_color(GOLD)

        self.play(Write(label), run_time=0.3)
        self.play(Write(sde), run_time=0.8)

        # Brace under drift
        drift_brace = Brace(VGroup(sde[2], sde[3]), DOWN, color=BLUE)
        drift_label.next_to(drift_brace, DOWN, buff=0.1)
        diff_brace = Brace(VGroup(sde[5], sde[6]), DOWN, color=GOLD)
        diffusion_label.next_to(diff_brace, DOWN, buff=0.1)

        self.play(
            GrowFromCenter(drift_brace), FadeIn(drift_label),
            GrowFromCenter(diff_brace), FadeIn(diffusion_label),
            run_time=0.5,
        )
        self.wait(0.4)
'''.format(bg=BG_COLOR, gold=GOLD, white=WHITE, blue=ACCENT_BLUE)


def render_scene(scene_name: str, output_name: str):
    script_path = os.path.join(OUTDIR, "_manim_scenes.py")
    with open(script_path, "w") as f:
        f.write(MANIM_SCRIPT)

    cmd = [
        "manim", "render",
        "-ql",  # low quality for speed, will upscale
        "--fps", "30",
        "--disable_caching",
        "-o", f"{output_name}.mp4",
        script_path,
        scene_name,
    ]
    print(f"Rendering {scene_name}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"WARN: manim failed for {scene_name}: {result.stderr[-500:]}")
        return None

    # Find the output file
    for root, dirs, files in os.walk("/tmp"):
        for fn in files:
            if fn == f"{output_name}.mp4":
                src = os.path.join(root, fn)
                dst = os.path.join(OUTDIR, f"manim_{output_name}.mp4")
                shutil.copy2(src, dst)
                print(f"  -> {dst}")
                return dst

    # Search in media directory
    media_dir = os.path.join(os.path.dirname(script_path), "media")
    for root, dirs, files in os.walk(media_dir if os.path.exists(media_dir) else "."):
        for fn in files:
            if fn == f"{output_name}.mp4":
                src = os.path.join(root, fn)
                dst = os.path.join(OUTDIR, f"manim_{output_name}.mp4")
                shutil.copy2(src, dst)
                print(f"  -> {dst}")
                return dst

    print(f"  Could not find output for {scene_name}")
    return None


def main():
    scenes = [
        ("ItoLemma", "ito_lemma"),
        ("StochasticPaths", "stochastic_paths"),
        ("SDEReveal", "sde_reveal"),
    ]
    for scene_name, output_name in scenes:
        render_scene(scene_name, output_name)
    print("Done generating Manim animations.")


if __name__ == "__main__":
    main()
