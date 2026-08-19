"""Fail-closed validation for multimodal TasteForge artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_REQUIRED_MODALITIES = {"image", "video", "3d_asset"}
_SIGNATURE_AXES = {"materials", "motion", "composition", "avoid"}


class ContractError(ValueError):
    """The dry-run bundle is incomplete or has lost taste specificity."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_signature(spec: dict[str, Any]) -> str:
    signature = spec.get("signature", {})
    return json.dumps(signature, sort_keys=True, separators=(",", ":"))


def validate_genre_specs(specs: list[dict[str, Any]]) -> None:
    """Require complete, semantically distinct numbered genre specs."""
    if not specs:
        raise ContractError("at least one genre spec is required")
    numbers = [spec.get("number") for spec in specs]
    if len(numbers) != len(set(numbers)):
        raise ContractError("genre numbers must be distinct")

    fingerprints = [spec.get("style_fingerprint") for spec in specs]
    signatures = [_semantic_signature(spec) for spec in specs]
    if len(fingerprints) != len(set(fingerprints)) or len(signatures) != len(set(signatures)):
        raise ContractError("genre references collapsed into a generic style; distinct specs required")

    for spec in specs:
        signature = spec.get("signature")
        if not isinstance(signature, dict) or not _SIGNATURE_AXES.issubset(signature):
            raise ContractError(f"genre {spec.get('number')} has an incomplete signature")
        if not all(isinstance(signature[axis], list) for axis in _SIGNATURE_AXES):
            raise ContractError(f"genre {spec.get('number')} signature axes must be lists")
        if not all(signature[axis] for axis in _SIGNATURE_AXES - {"avoid"}):
            raise ContractError(f"genre {spec.get('number')} uses generic empty style axes")


def validate_effect_recipe(recipe: dict[str, Any]) -> None:
    """Require a seeded aperiodic schedule and anchors on subject-aware effects."""
    if not isinstance(recipe.get("seed"), int) or isinstance(recipe.get("seed"), bool):
        raise ContractError("effect recipe must have an integer seed")
    if recipe.get("rng_algorithm") != "python.random.Random/v1":
        raise ContractError("effect recipe must declare its seeded RNG algorithm")
    events = recipe.get("events")
    if not isinstance(events, list) or len(events) < 3:
        raise ContractError("effect recipe needs at least three scheduled events")
    times = [float(event["time"]) for event in events]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("effect event times must be unique and increasing")
    intervals = [round(b - a, 6) for a, b in zip(times, times[1:])]
    if len(set(intervals)) <= 1:
        raise ContractError("stochastic schedule is periodic; intervals must vary")
    for period in range(1, len(intervals) // 2 + 1):
        if all(intervals[index] == intervals[index % period] for index in range(len(intervals))):
            raise ContractError("stochastic schedule is periodic; repeating interval cycle")
    if recipe.get("periodic") is not False:
        raise ContractError("effect recipe must explicitly declare periodic=false")
    for event in events:
        cv_effect = str(event.get("effect", "")).startswith("cv_")
        if cv_effect and event.get("requires_subject_anchor") is not True:
            raise ContractError(f"CV effect {event.get('effect')} must require a subject anchor")
        if event.get("requires_subject_anchor"):
            anchor = event.get("subject_anchor")
            required = {"mode", "target", "source_ref_sha256", "evidence_time", "lost_policy"}
            if not isinstance(anchor, dict) or not required.issubset(anchor):
                raise ContractError(f"CV effect {event.get('effect')} lacks a valid subject anchor")
            if anchor.get("mode") not in {"object_track", "point_track", "segmentation_track"}:
                raise ContractError(f"CV effect {event.get('effect')} has an invalid subject anchor")
    for event in events:
        placement = event.get("placement")
        if not isinstance(placement, dict) or not {"safe_area", "max_coverage", "occlusion_policy"}.issubset(placement):
            raise ContractError(f"effect {event.get('effect')} lacks placement constraints")


def validate_provenance(payload: dict[str, Any]) -> None:
    """Require every declared rule to cite immutable, timestamped evidence."""
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ContractError("provenance must contain derived rules")
    for rule in rules:
        evidence = rule.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ContractError(f"rule {rule.get('rule_id')} lacks reference evidence")
        for item in evidence:
            digest = item.get("reference_sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise ContractError(f"rule {rule.get('rule_id')} lacks immutable reference evidence")
            times = item.get("times")
            if not isinstance(times, list) or not times:
                raise ContractError(f"rule {rule.get('rule_id')} lacks time evidence")
            if not all(isinstance(time, (int, float)) and time >= 0 for time in times):
                raise ContractError(f"rule {rule.get('rule_id')} has invalid time evidence")


def validate_manifests(manifests_dir: str | Path) -> None:
    """Require image, video, and 3D-asset dry-run request manifests."""
    manifests_dir = Path(manifests_dir)
    found = {path.stem for path in manifests_dir.glob("*.json")} if manifests_dir.is_dir() else set()
    missing = _REQUIRED_MODALITIES - found
    if missing:
        raise ContractError(f"missing modality manifests: {sorted(missing)}")
    for modality in _REQUIRED_MODALITIES:
        payload = json.loads((manifests_dir / f"{modality}.json").read_text(encoding="utf-8"))
        if payload.get("modality") != modality or not payload.get("requests"):
            raise ContractError(f"invalid or empty {modality} manifest")
        if (payload.get("dry_run") is not True or payload.get("provider_calls") != 0
                or payload.get("provider_execution") is not False):
            raise ContractError(f"{modality} manifest crosses the dry-run boundary")
        for request in payload["requests"]:
            if (request.get("provider_execution") is not False
                    or request.get("submit") is not False
                    or request.get("provider_call_mode") != "disabled"):
                raise ContractError(f"{modality} request crosses the dry-run boundary")


def validate_artifact_receipt(out_dir: str | Path, receipt: dict[str, Any]) -> None:
    """Verify that the receipt binds every emitted artifact and its provenance."""
    out_dir = Path(out_dir).resolve()
    entries = receipt.get("evidence_artifacts")
    if not isinstance(entries, list):
        raise ContractError("receipt evidence_artifacts must be a list")
    if not all(isinstance(entry, dict) for entry in entries):
        raise ContractError("receipt evidence_artifacts entries must be objects")
    known_sources = {
        (source.get("path"), source.get("sha256"))
        for key in ("references", "evidence_files")
        for source in receipt.get(key, [])
        if isinstance(source, dict)
    }

    emitted = {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file() and path.name != "receipt.json"
    }
    bound_paths: list[str] = []
    for entry in entries:
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            raise ContractError("artifact path must be a non-empty relative path")
        bound_paths.append(relative)
    if len(bound_paths) != len(set(bound_paths)):
        raise ContractError("receipt contains duplicate artifact paths")
    missing = emitted - set(bound_paths)
    extra = set(bound_paths) - emitted
    if missing:
        raise ContractError(f"unbound emitted artifact: {sorted(missing)}")
    if extra:
        raise ContractError(f"receipt binds missing artifact: {sorted(extra)}")

    for entry in entries:
        relative = entry.get("path")
        assert isinstance(relative, str)
        path = (out_dir / relative).resolve()
        try:
            path.relative_to(out_dir)
        except ValueError as error:
            raise ContractError(f"artifact path escapes output directory: {relative}") from error
        if entry.get("provider_execution") is not False:
            raise ContractError(f"artifact {relative} permits provider execution")
        if not isinstance(entry.get("genre_numbers"), list):
            raise ContractError(f"artifact {relative} lacks genre binding")
        modalities = entry.get("modalities")
        if (not isinstance(modalities, list)
                or any(modality not in _REQUIRED_MODALITIES for modality in modalities)):
            raise ContractError(f"artifact {relative} has invalid modality binding")
        if entry.get("bytes") != path.stat().st_size:
            raise ContractError(f"artifact {relative} byte size does not match receipt")
        if entry.get("sha256") != _sha256(path):
            raise ContractError(f"artifact {relative} SHA-256 does not match receipt")
        provenance = entry.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            raise ContractError(f"artifact {relative} lacks exact reference/time provenance")
        for source in provenance:
            if not isinstance(source.get("reference_path"), str) or not source["reference_path"]:
                raise ContractError(f"artifact {relative} has invalid reference path")
            digest = source.get("reference_sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise ContractError(f"artifact {relative} has invalid reference SHA-256")
            if (source["reference_path"], digest) not in known_sources:
                raise ContractError(f"artifact {relative} cites an unknown provenance source")
            times = source.get("reference_times")
            basis = source.get("time_basis")
            if not isinstance(times, list) or basis not in {"media_seconds", "whole_file"}:
                raise ContractError(f"artifact {relative} has invalid reference/time provenance")
            if basis == "media_seconds" and not times:
                raise ContractError(f"artifact {relative} lacks media reference times")
            if basis == "whole_file" and times:
                raise ContractError(f"artifact {relative} whole-file provenance must not invent times")
            if not all(isinstance(time, (int, float)) and time >= 0 for time in times):
                raise ContractError(f"artifact {relative} has invalid media reference times")

    digest_payload = dict(receipt)
    claimed_digest = digest_payload.pop("receipt_sha256", None)
    actual_digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if claimed_digest != actual_digest:
        raise ContractError("receipt SHA-256 does not match its canonical content")


def validate_bundle(out_dir: str | Path) -> None:
    """Validate required multimodal files and cross-artifact invariants."""
    out_dir = Path(out_dir)
    specs = [json.loads(path.read_text(encoding="utf-8"))
             for path in sorted((out_dir / "genres").glob("*.json"))]
    validate_genre_specs(specs)

    validate_manifests(out_dir / "manifests")
    provenance_path = out_dir / "provenance.json"
    if not provenance_path.is_file():
        raise ContractError("missing provenance")
    validate_provenance(json.loads(provenance_path.read_text(encoding="utf-8")))

    recipe_path = out_dir / "resolve" / "effect_recipe.json"
    if not recipe_path.is_file():
        raise ContractError("missing Resolve effect recipe")
    validate_effect_recipe(json.loads(recipe_path.read_text(encoding="utf-8")))

    receipt_path = out_dir / "receipt.json"
    if not receipt_path.is_file():
        raise ContractError("missing receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("provider_execution") is not False or receipt.get("provider_calls") != 0:
        raise ContractError("receipt crosses the dry-run boundary")
    validate_artifact_receipt(out_dir, receipt)
