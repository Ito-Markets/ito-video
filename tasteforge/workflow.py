"""File-driven, multimodal TasteForge dry-run orchestration.

The workflow reads one JSON contract, hashes and probes every local reference,
keeps each numbered genre separate, and writes provider request manifests. It
never imports or calls a provider SDK.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import statistics
import subprocess
from pathlib import Path
from typing import Any, Callable

Probe = Callable[[Path], dict[str, Any]]
_MODALITIES = ("image", "video", "3d_asset")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_feature_output(output: str, *, scene_threshold: float = 0.30) -> dict[str, Any]:
    """Parse ffmpeg ``metadata=print`` output into timestamped measurements."""
    records: list[dict[str, float]] = []
    current: dict[str, float] | None = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        match = re.search(r"pts_time:([-+0-9.eE]+)", line)
        if line.startswith("frame:") and match:
            if current:
                records.append(current)
            current = {"time": float(match.group(1))}
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.rsplit("=", 1)
        mapped = {
            "lavfi.signalstats.YAVG": "luma_raw",
            "lavfi.signalstats.SATAVG": "saturation_raw",
            "lavfi.signalstats.HUEAVG": "hue",
            "lavfi.scene_score": "scene_score",
        }.get(key)
        if mapped:
            try:
                current[mapped] = float(value)
            except ValueError:
                pass
    if current:
        records.append(current)

    style_samples = []
    scene_changes = []
    for record in records:
        if "luma_raw" in record:
            style_samples.append({
                "time": round(record["time"], 6),
                "luma": round(record["luma_raw"] / 255.0, 6),
                "saturation": round(record.get("saturation_raw", 0.0) / 100.0, 6),
                "hue": record.get("hue"),
            })
        if record.get("scene_score", 0.0) >= scene_threshold:
            scene_changes.append(round(record["time"], 6))
    return {"style_samples": style_samples, "scene_changes": scene_changes}


def _run_ffmpeg_features(path: Path) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for temporal/style feature extraction")
    filters = (
        "scale=320:-2,"
        "select='not(mod(n\\,12))+gt(scene\\,0.30)',"
        "signalstats,metadata=print:file=-"
    )
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-vf", filters,
         "-an", "-vsync", "0", "-f", "null", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_feature_output(result.stderr + "\n" + result.stdout)


def probe_media(path: Path) -> dict[str, Any]:
    """Probe local media and extract timestamped style/temporal features."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for reference probing")
    command = [
        ffprobe, "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    video: dict[str, Any] = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"),
        {},
    )
    duration = float(video.get("duration") or payload.get("format", {}).get("duration") or 0)
    rate = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    num, _, den = rate.partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    feature_data = _run_ffmpeg_features(path)
    measured_times = sorted({
        float(sample["time"]) for sample in feature_data["style_samples"]
    } | set(feature_data["scene_changes"]))
    sample_times = measured_times or [
        round(duration * fraction, 6) for fraction in (0.125, 0.375, 0.625, 0.875)
    ]
    return {
        "duration": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "codec": str(video.get("codec_name") or "unknown"),
        "pixel_format": str(video.get("pix_fmt") or "unknown"),
        "color_space": str(video.get("color_space") or "unknown"),
        "sample_times": sample_times,
        "style_samples": feature_data["style_samples"],
        "scene_changes": feature_data["scene_changes"],
    }


def _prompt(modality: str, genre: dict[str, Any], features: dict[str, Any]) -> str:
    signature = genre["signature"]
    base = (
        f"Genre {genre['number']}: {genre['label']}. "
        f"Materials: {', '.join(signature['materials'])}. "
        f"Motion: {', '.join(signature['motion'])}. "
        f"Composition: {', '.join(signature['composition'])}. "
        f"Avoid: {', '.join(signature['avoid'])}. "
        f"Reference evidence: {features['reference_count']} file(s), "
        f"{features['total_duration']:.3f}s total."
    )
    suffix = {
        "image": " Create one still image with explicit subject placement and no temporal language.",
        "video": " Create a moving shot with camera motion and non-looping temporal progression.",
        "3d_asset": " Create a watertight textured 3D asset with front, side, and material consistency.",
    }[modality]
    return base + suffix


def _build_effect_recipe(
    config: dict[str, Any], specs: list[dict[str, Any]], references: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build a deterministic, seeded, non-periodic Resolve placement plan."""
    seed = int(config["seed"])
    rng = random.Random(seed)
    by_genre = {
        spec["number"]: [ref for ref in references if ref["genre_number"] == spec["number"]]
        for spec in specs
    }
    duration = float(config.get("resolve_duration") or sum(
        spec["measured_features"]["total_duration"] for spec in specs
    ))
    duration = max(duration, 6.0)
    effect_names = {
        "flash-ethereal": "bloom_flash",
        "3d-cyber-glitch": "cv_wireframe_lock",
        "fluid-sketch": "fluid_contour_bleed",
    }
    events: list[dict[str, Any]] = []
    clock = round(rng.uniform(0.35, 0.75), 6)
    index = 0
    while clock < duration - 0.25 and len(events) < 18:
        spec = specs[index % len(specs)]
        ref = by_genre[spec["number"]][index % len(by_genre[spec["number"]])]
        sample_times = ref["probe"].get("sample_times", [])
        evidence_time = float(sample_times[index % len(sample_times)]) if sample_times else 0.0
        requires_anchor = spec["slug"] == "3d-cyber-glitch"
        event: dict[str, Any] = {
            "event_id": f"fx-{index:03d}",
            "time": clock,
            "duration": round(rng.uniform(0.08, 0.42), 6),
            "genre_number": spec["number"],
            "effect": effect_names.get(spec["slug"], "reference_accent"),
            "requires_subject_anchor": requires_anchor,
            "placement": {
                "safe_area": 0.08,
                "max_coverage": 0.30 if requires_anchor else 0.35,
                "occlusion_policy": "preserve_subject_face_and_readable_type",
                "track_space": "source_normalized",
            },
            "evidence": {
                "reference_sha256": ref["sha256"],
                "time": evidence_time,
                "style_fingerprint": spec["style_fingerprint"],
            },
        }
        if requires_anchor:
            event["subject_anchor"] = {
                "mode": "segmentation_track",
                "target": "primary_subject",
                "source_ref_sha256": ref["sha256"],
                "evidence_time": evidence_time,
                "lost_policy": "disable_effect_until_track_recovers",
            }
        events.append(event)
        # Independent continuous draws create an aperiodic schedule. The seed,
        # algorithm, rounded values, and exact events are all serialized.
        clock = round(clock + rng.uniform(0.61, 2.17), 6)
        index += 1

    # Tiny inputs still need enough events for a schedule to be auditable.
    while len(events) < 4:
        clock = round(clock + rng.uniform(0.61, 2.17), 6)
        spec = specs[len(events) % len(specs)]
        ref = by_genre[spec["number"]][0]
        requires_anchor = spec["slug"] == "3d-cyber-glitch"
        event = {
            "event_id": f"fx-{len(events):03d}",
            "time": clock,
            "duration": round(rng.uniform(0.08, 0.42), 6),
            "genre_number": spec["number"],
            "effect": effect_names.get(spec["slug"], "reference_accent"),
            "requires_subject_anchor": requires_anchor,
            "placement": {
                "safe_area": 0.08,
                "max_coverage": 0.30 if requires_anchor else 0.35,
                "occlusion_policy": "preserve_subject_face_and_readable_type",
                "track_space": "source_normalized",
            },
            "evidence": {
                "reference_sha256": ref["sha256"],
                "time": 0.0,
                "style_fingerprint": spec["style_fingerprint"],
            },
        }
        if requires_anchor:
            event["subject_anchor"] = {
                "mode": "segmentation_track",
                "target": "primary_subject",
                "source_ref_sha256": ref["sha256"],
                "evidence_time": 0.0,
                "lost_policy": "disable_effect_until_track_recovers",
            }
        events.append(event)

    return {
        "schema_version": 1,
        "dry_run": True,
        "provider_calls": 0,
        "seed": seed,
        "rng_algorithm": "python.random.Random/v1",
        "periodic": False,
        "timeline_duration": duration,
        "events": events,
        "placement_constraints": {
            "subject_anchored_cv_only": True,
            "full_frame_3d_not_corner_overlay": True,
            "preserve_titles_and_faces": True,
            "disable_on_track_loss": True,
        },
    }


def run_workflow(config_path: str | Path, out_dir: str | Path, *, probe: Probe | None = None) -> dict[str, Any]:
    """Execute the deterministic offline contract and return its receipt."""
    config_path = Path(config_path)
    out_dir = Path(out_dir)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    probe = probe or probe_media

    def resolve_input(raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        return candidate.resolve()

    if config.get("schema_version") != 1:
        raise ValueError("workflow schema_version must be 1")
    genres = sorted(config.get("genres", []), key=lambda item: item["number"])
    if not genres:
        raise ValueError("workflow needs at least one numbered genre")

    references: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    manifests: dict[str, dict[str, Any]] = {
        modality: {
            "schema_version": 1,
            "modality": modality,
            "dry_run": True,
            "provider_calls": 0,
            "provider_execution": False,
            "requests": [],
        }
        for modality in _MODALITIES
    }
    provenance_rules: list[dict[str, Any]] = []
    evidence_files: list[dict[str, Any]] = []
    for raw_path in config.get("evidence_files", []):
        path = resolve_input(raw_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        suffix = path.suffix.lower()
        evidence_files.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "kind": (
                "editorial" if suffix in {".edl", ".fcpxml"}
                else "archive" if suffix == ".zip"
                else "workflow_record"
            ),
        })

    for genre in genres:
        genre_refs: list[dict[str, Any]] = []
        for raw_path in genre.get("references", []):
            path = resolve_input(raw_path)
            if not path.is_file():
                raise FileNotFoundError(path)
            measured = probe(path)
            ref = {
                "genre_number": genre["number"],
                "genre_slug": genre["slug"],
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "probe": measured,
            }
            references.append(ref)
            genre_refs.append(ref)

        if not genre_refs:
            raise ValueError(f"genre {genre['slug']} has no references")
        total_duration = round(sum(float(ref["probe"].get("duration") or 0) for ref in genre_refs), 6)
        scene_changes = [
            float(time)
            for ref in genre_refs
            for time in ref["probe"].get("scene_changes", [])
        ]
        scene_intervals = [
            later - earlier for earlier, later in zip(scene_changes, scene_changes[1:])
        ]
        style_samples = [
            sample
            for ref in genre_refs
            for sample in ref["probe"].get("style_samples", [])
        ]
        luma = [float(sample["luma"]) for sample in style_samples if "luma" in sample]
        saturation = [
            float(sample["saturation"])
            for sample in style_samples
            if "saturation" in sample
        ]
        features = {
            "reference_count": len(genre_refs),
            "total_duration": total_duration,
            "sample_times": [
                {"sha256": ref["sha256"], "times": ref["probe"].get("sample_times", [])}
                for ref in genre_refs
            ],
            "temporal": {
                "scene_change_count": len(scene_changes),
                "scene_changes": scene_changes,
                "scene_interval_mean": (
                    round(statistics.fmean(scene_intervals), 6) if scene_intervals else 0.0
                ),
                "scene_interval_variance": (
                    round(statistics.pvariance(scene_intervals), 6)
                    if len(scene_intervals) > 1 else 0.0
                ),
            },
            "style": {
                "sample_count": len(style_samples),
                "luma_mean": round(statistics.fmean(luma), 6) if luma else None,
                "saturation_mean": (
                    round(statistics.fmean(saturation), 6) if saturation else None
                ),
            },
        }
        fingerprint_payload = {"signature": genre["signature"], "features": features}
        fingerprint = hashlib.sha256(_canonical_bytes(fingerprint_payload)).hexdigest()
        spec = {
            "schema_version": 1,
            "number": genre["number"],
            "slug": genre["slug"],
            "label": genre["label"],
            "signature": genre["signature"],
            "measured_features": features,
            "style_fingerprint": fingerprint,
            "dry_run": True,
        }
        specs.append(spec)
        _write_json(out_dir / "genres" / f"{genre['number']:02d}-{genre['slug']}.json", spec)

        evidence = [
            {
                "reference_sha256": ref["sha256"],
                "times": ref["probe"].get("sample_times", []),
                "feature_keys": ["duration", "fps", "style_samples", "scene_changes"],
            }
            for ref in genre_refs
        ]
        for axis, values in genre["signature"].items():
            provenance_rules.append({
                "rule_id": f"genre-{genre['number']}-{axis}",
                "genre_number": genre["number"],
                "axis": axis,
                "rule": values,
                "evidence": evidence,
            })

        for modality in _MODALITIES:
            prompt = _prompt(modality, genre, features)
            modality_index = _MODALITIES.index(modality)
            request_seed = int(config["seed"]) + genre["number"] * 100 + modality_index
            endpoint = {
                "image": "fal-ai/flux/dev",
                "video": "fal-ai/kling-video/v2.1/master/text-to-video",
                "3d_asset": "fal-ai/hunyuan3d/v2",
            }[modality]
            body: dict[str, Any] = {"prompt": prompt, "seed": request_seed}
            if modality == "image":
                body.update({"image_size": "landscape_16_9", "num_images": 1})
            elif modality == "video":
                body.update({"aspect_ratio": "16:9", "duration": "5", "generate_audio": False})
            else:
                body.update({
                    "output_format": "glb",
                    "generate_texture": True,
                    "input_image_artifact": (
                        f"manifest://image/{config['run_id']}-{genre['number']}-image"
                    ),
                })
            manifests[modality]["requests"].append({
                "request_id": f"{config['run_id']}-{genre['number']}-{modality}",
                "genre_number": genre["number"],
                "genre_slug": genre["slug"],
                "style_fingerprint": fingerprint,
                "prompt": prompt,
                "provider": "fal",
                "endpoint_candidate": endpoint,
                "endpoint_status": "historical_candidate_unverified_no_network_lookup",
                "provider_call_mode": "disabled",
                "provider_execution": False,
                "request_body": body,
                "submit": False,
                "dry_run": True,
                "reference_sha256": [ref["sha256"] for ref in genre_refs],
            })

    for modality, manifest in manifests.items():
        _write_json(out_dir / "manifests" / f"{modality}.json", manifest)
    _write_json(out_dir / "references.json", references)
    _write_json(out_dir / "evidence_files.json", evidence_files)
    _write_json(out_dir / "provenance.json", {
        "schema_version": 1,
        "run_id": config["run_id"],
        "rules": provenance_rules,
    })
    effect_recipe = _build_effect_recipe(config, specs, references)
    _write_json(out_dir / "resolve" / "effect_recipe.json", effect_recipe)

    def reference_provenance(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{
            "reference_path": ref["path"],
            "reference_sha256": ref["sha256"],
            "reference_times": sorted({
                float(time) for time in ref["probe"].get("sample_times", [])
            }),
            "time_basis": "media_seconds",
        } for ref in selected]

    whole_file_provenance = [{
        "reference_path": item["path"],
        "reference_sha256": item["sha256"],
        "reference_times": [],
        "time_basis": "whole_file",
    } for item in evidence_files]

    evidence_artifacts: list[dict[str, Any]] = []
    all_genres = [spec["number"] for spec in specs]
    all_modalities = list(_MODALITIES)
    for artifact_path in sorted(path for path in out_dir.rglob("*") if path.is_file()):
        relative = artifact_path.relative_to(out_dir).as_posix()
        genre_numbers = list(all_genres)
        modalities = list(all_modalities)
        sources = reference_provenance(references)
        if relative.startswith("genres/"):
            genre_number = int(artifact_path.name.split("-", 1)[0])
            genre_numbers = [genre_number]
            sources = reference_provenance([
                ref for ref in references if ref["genre_number"] == genre_number
            ])
        elif relative.startswith("manifests/"):
            modality = artifact_path.stem
            modalities = [modality]
        elif relative == "evidence_files.json" and whole_file_provenance:
            genre_numbers = []
            modalities = []
            sources = whole_file_provenance
        elif relative == "resolve/effect_recipe.json":
            modalities = ["video"]
            source_by_digest = {ref["sha256"]: ref for ref in references}
            exact: dict[str, set[float]] = {}
            for event in effect_recipe["events"]:
                evidence = event["evidence"]
                exact.setdefault(evidence["reference_sha256"], set()).add(float(evidence["time"]))
            sources = [{
                "reference_path": source_by_digest[digest]["path"],
                "reference_sha256": digest,
                "reference_times": sorted(times),
                "time_basis": "media_seconds",
            } for digest, times in sorted(exact.items())]
        evidence_artifacts.append({
            "path": relative,
            "bytes": artifact_path.stat().st_size,
            "sha256": _sha256(artifact_path),
            "genre_numbers": genre_numbers,
            "modalities": modalities,
            "provider_execution": False,
            "provenance": sources,
        })

    receipt = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "seed": int(config["seed"]),
        "dry_run": True,
        "provider_calls": 0,
        "provider_execution": False,
        "references": references,
        "evidence_files": evidence_files,
        "evidence_artifacts": evidence_artifacts,
        "genre_fingerprints": [spec["style_fingerprint"] for spec in specs],
        "artifacts": {
            "genres": len(specs),
            "manifests": list(_MODALITIES),
            "provenance_rules": len(provenance_rules),
            "evidence_artifacts": len(evidence_artifacts),
        },
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
    _write_json(out_dir / "receipt.json", receipt)
    return receipt
