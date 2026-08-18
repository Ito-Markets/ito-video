"""Apply a style pack to local media - deterministically, offline.

The recovered pipeline's provider stage generated each shot against a hosted
model. In this lane, application is *local and deterministic*: the pack's
measured cadence plans the shot rhythm, local media clips fill the slots, and
the result is a schema-valid application report plus a timeline ready for
EDL/FCPXML export. Provider generation fails closed (see :func:`apply_generate).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from . import pack as pack_mod
from . import schema, timeline

__all__ = ["ProviderDisabledError", "apply_local", "apply_generate", "plan_shots"]

_DEFAULT_FPS = 24.0
_MIN_SHOT = 0.05  # matches the recovered cadence floor


class ProviderDisabledError(RuntimeError):
    """Provider generation was requested but is not authorized."""


_FAIL_CLOSED = (
    "provider generation requires explicit separately authorized execution; "
    "this package ships no provider adapters and performs no network calls. "
    "Use apply_local() (deterministic, offline) instead."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_shots(cadence: dict[str, Any], target_duration: float) -> list[float]:
    """Propose shot durations filling ``target_duration`` at this cadence.

    Samples from the reference's own shot-length distribution (seeded, like
    the recovered ``Cadence.plan_shots``) so the plan inherits rhythm
    variance instead of flattening into evenly spaced clips.
    """
    durations = [
        s["duration"]
        for s in cadence.get("shots", [])
        if isinstance(s, dict) and s.get("duration", 0) > _MIN_SHOT
    ]
    if not durations:
        durations = [max(float(cadence.get("mean_shot") or 0.0), 1.0)]

    rng = random.Random(7)  # deterministic, mirrors numpy default_rng(7)
    out: list[float] = []
    acc = 0.0
    while acc < target_duration:
        d = rng.choice(durations)
        remaining = target_duration - acc
        if remaining < d * 0.5:
            break
        d = min(d, remaining)
        out.append(round(d, 3))
        acc += d
    if not out:
        out = [round(target_duration, 3)]
    return out


def apply_local(
    sp: pack_mod.StylePack,
    media: list[dict[str, Any]],
    duration: float | None = None,
    fps: float | None = None,
) -> dict[str, Any]:
    """Plan a cut from the pack's cadence over local media clips.

    Returns an application report validated against
    ``schema.APPLICATION_REPORT_SCHEMA``. The report structurally cannot
    claim a provider run: ``provider`` is enum-locked to ``"none"`` and
    ``dry_run`` to ``true``.
    """
    if not media:
        raise ValueError("apply_local needs at least one media clip")

    cadence = sp.read_json(sp.cadence_path)
    seq_fps = float(cadence.get("fps") or fps or _DEFAULT_FPS)

    target = float(duration) if duration else sum(
        float(c.get("duration") or 0.0) for c in media
    )
    if target <= 0:
        raise ValueError("target duration must be positive (media durations or --duration)")

    planned = plan_shots(cadence, target)

    shots: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    clock = 0.0
    for i, d in enumerate(planned):
        clip = media[i % len(media)]
        frames = max(1, timeline.seconds_to_frames(d, seq_fps))
        events.append(
            {
                "path": str(clip["path"]),
                "name": str(clip.get("name") or clip["path"]),
                "duration": round(d, 3),
                "frames": frames,
                "offset_frames": sum(e["frames"] for e in events),
                "fps": seq_fps,
            }
        )
        shots.append(
            {
                "index": i,
                "start": round(clock, 3),
                "end": round(clock + d, 3),
                "duration": round(d, 3),
            }
        )
        clock += d

    report = {
        "schema_version": 1,
        "pack": sp.name,
        "generated": _utc_now(),
        "mode": "local-deterministic",
        "dry_run": True,
        "provider": "none",
        "target_duration": round(target, 3),
        "media": [
            {"path": str(c.get("path")), "duration": float(c.get("duration") or 0)}
            for c in media
        ],
        "planned_shots": shots,
        "timeline_events": events,
        "cadence": {
            "mean_shot": cadence.get("mean_shot", 0.0),
            "rhythm_variance": cadence.get("rhythm_variance", 0.0),
            "cuts_per_min": cadence.get("cuts_per_min", 0.0),
        },
        "notes": [
            "shot durations drawn from the pack's measured cadence (seeded, "
            "deterministic); no provider generation was requested or run",
        ],
    }
    problems = schema.validate(report, schema.APPLICATION_REPORT_SCHEMA)
    if problems:
        raise ValueError(f"apply_local produced an invalid report: {problems}")
    return report


def apply_generate(
    sp: pack_mod.StylePack, brief: str, **_: Any
) -> dict[str, Any]:
    """Refuse provider generation. Fails closed, always."""
    raise ProviderDisabledError(_FAIL_CLOSED)
