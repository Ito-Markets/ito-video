import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tasteforge.contract import (
    ContractError,
    validate_artifact_receipt,
    validate_effect_recipe,
    validate_genre_specs,
    validate_manifests,
    validate_provenance,
)


class GenreContractTests(unittest.TestCase):
    def test_collapsing_references_into_one_generic_style_is_rejected(self):
        generic = {
            "signature": {
                "materials": ["cinematic"],
                "motion": ["dynamic"],
                "composition": ["beautiful"],
                "avoid": [],
            },
            "style_fingerprint": "same",
        }
        specs = [
            {**generic, "number": 1, "slug": "flash-ethereal"},
            {**generic, "number": 2, "slug": "3d-cyber-glitch"},
            {**generic, "number": 3, "slug": "fluid-sketch"},
        ]
        with self.assertRaisesRegex(ContractError, "collapsed|distinct"):
            validate_genre_specs(specs)


class ResolveRecipeContractTests(unittest.TestCase):
    def test_repeating_interval_cycle_is_rejected_as_periodic(self):
        recipe = {
            "seed": 41,
            "rng_algorithm": "python.random.Random/v1",
            "periodic": False,
            "events": [
                {"time": 1.0, "effect": "bloom"},
                {"time": 2.0, "effect": "bloom"},
                {"time": 4.0, "effect": "bloom"},
                {"time": 5.0, "effect": "bloom"},
                {"time": 7.0, "effect": "bloom"},
            ],
        }
        with self.assertRaisesRegex(ContractError, "periodic"):
            validate_effect_recipe(recipe)

    def test_seed_without_declared_rng_algorithm_is_rejected(self):
        recipe = {
            "seed": 41,
            "periodic": False,
            "events": [
                {"time": 1.0, "effect": "bloom"},
                {"time": 2.2, "effect": "bloom"},
                {"time": 4.9, "effect": "bloom"},
                {"time": 8.3, "effect": "bloom"},
            ],
        }
        with self.assertRaisesRegex(ContractError, "seed|algorithm"):
            validate_effect_recipe(recipe)

    def test_unseeded_schedule_is_rejected(self):
        recipe = {
            "periodic": False,
            "rng_algorithm": "python.random.Random/v1",
            "events": [
                {"time": 1.0, "effect": "bloom"},
                {"time": 2.2, "effect": "bloom"},
                {"time": 4.9, "effect": "bloom"},
            ],
        }
        with self.assertRaisesRegex(ContractError, "seed"):
            validate_effect_recipe(recipe)

    def test_cv_effect_with_placeholder_anchor_is_rejected(self):
        recipe = {
            "seed": 41,
            "rng_algorithm": "python.random.Random/v1",
            "periodic": False,
            "events": [
                {"time": 1.0, "effect": "bloom"},
                {
                    "time": 2.2,
                    "effect": "cv_boxes",
                    "requires_subject_anchor": True,
                    "subject_anchor": {"mode": "frame_center"},
                },
                {"time": 4.9, "effect": "bloom"},
                {"time": 8.3, "effect": "bloom"},
            ],
        }
        with self.assertRaisesRegex(ContractError, "subject anchor"):
            validate_effect_recipe(recipe)

    def test_cv_effect_cannot_bypass_anchor_by_clearing_requirement_flag(self):
        recipe = {
            "seed": 41,
            "rng_algorithm": "python.random.Random/v1",
            "periodic": False,
            "events": [
                {"time": 1.0, "effect": "bloom", "placement": self._placement()},
                {"time": 2.2, "effect": "cv_wireframe_lock",
                 "requires_subject_anchor": False, "placement": self._placement()},
                {"time": 4.9, "effect": "bloom", "placement": self._placement()},
                {"time": 8.3, "effect": "bloom", "placement": self._placement()},
            ],
        }
        with self.assertRaisesRegex(ContractError, "subject anchor"):
            validate_effect_recipe(recipe)

    @staticmethod
    def _placement():
        return {
            "safe_area": 0.08,
            "max_coverage": 0.35,
            "occlusion_policy": "preserve_subject_face_and_readable_type",
        }


class ProvenanceContractTests(unittest.TestCase):
    def test_rule_without_reference_time_evidence_is_rejected(self):
        payload = {
            "rules": [{
                "rule_id": "genre-1-materials",
                "rule": ["glass bloom"],
                "evidence": [{"reference_sha256": "a" * 64, "times": []}],
            }],
        }
        with self.assertRaisesRegex(ContractError, "time evidence"):
            validate_provenance(payload)


class ManifestContractTests(unittest.TestCase):
    def test_missing_3d_asset_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for modality in ("image", "video"):
                (root / f"{modality}.json").write_text(json.dumps({
                    "modality": modality,
                    "dry_run": True,
                    "provider_calls": 0,
                    "requests": [{"prompt": modality}],
                }), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "3d_asset"):
                validate_manifests(root)

    def test_manifest_with_provider_execution_enabled_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for modality in ("image", "video", "3d_asset"):
                (root / f"{modality}.json").write_text(json.dumps({
                    "modality": modality,
                    "dry_run": True,
                    "provider_calls": 0,
                    "provider_execution": modality == "video",
                    "requests": [{
                        "genre_number": 1,
                        "style_fingerprint": "a" * 64,
                        "prompt": modality,
                        "submit": False,
                        "provider_call_mode": "disabled",
                        "provider_execution": False,
                    }],
                }), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "dry-run boundary"):
                validate_manifests(root)


class ArtifactReceiptContractTests(unittest.TestCase):
    def test_unbound_emitted_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unbound.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "unbound emitted artifact"):
                validate_artifact_receipt(root, {"evidence_artifacts": []})

    def test_provider_execution_or_missing_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            entry = {
                "path": "artifact.json",
                "bytes": artifact.stat().st_size,
                "sha256": "a" * 64,
                "genre_numbers": [],
                "modalities": [],
                "provider_execution": True,
                "provenance": [],
            }
            with self.assertRaisesRegex(ContractError, "provider execution"):
                validate_artifact_receipt(root, {"evidence_artifacts": [entry]})

    def test_artifact_byte_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            entry = {
                "path": "artifact.json",
                "bytes": artifact.stat().st_size,
                "sha256": "0" * 64,
                "genre_numbers": [1],
                "modalities": ["image"],
                "provider_execution": False,
                "provenance": [{
                    "reference_path": "/reference.mov",
                    "reference_sha256": "b" * 64,
                    "reference_times": [0.5],
                    "time_basis": "media_seconds",
                }],
            }
            with self.assertRaisesRegex(ContractError, "SHA-256"):
                validate_artifact_receipt(root, {"evidence_artifacts": [entry]})

    def test_unknown_provenance_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            receipt = {
                "references": [],
                "evidence_files": [],
                "evidence_artifacts": [{
                    "path": "artifact.json",
                    "bytes": artifact.stat().st_size,
                    "sha256": digest,
                    "genre_numbers": [1],
                    "modalities": ["image"],
                    "provider_execution": False,
                    "provenance": [{
                        "reference_path": "/unknown.mov",
                        "reference_sha256": "b" * 64,
                        "reference_times": [0.5],
                        "time_basis": "media_seconds",
                    }],
                }],
            }
            with self.assertRaisesRegex(ContractError, "unknown provenance source"):
                validate_artifact_receipt(root, receipt)

    def test_receipt_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = {"evidence_artifacts": [], "receipt_sha256": "0" * 64}
            with self.assertRaisesRegex(ContractError, "receipt SHA-256"):
                validate_artifact_receipt(tmp, receipt)


if __name__ == "__main__":
    unittest.main()
