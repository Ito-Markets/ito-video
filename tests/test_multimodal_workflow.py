import json
import tempfile
import unittest
from pathlib import Path

from tasteforge.contract import validate_bundle
from tasteforge.workflow import parse_feature_output, run_workflow


class FeatureExtractionTests(unittest.TestCase):
    def test_ffmpeg_metadata_becomes_timestamped_style_and_scene_features(self):
        output = """
frame:0 pts:0 pts_time:0.75
lavfi.signalstats.YAVG=51
lavfi.signalstats.SATAVG=40
lavfi.signalstats.HUEAVG=15
lavfi.scene_score=0.42
frame:1 pts:1 pts_time:2.25
lavfi.signalstats.YAVG=204
lavfi.signalstats.SATAVG=70
lavfi.signalstats.HUEAVG=20
lavfi.scene_score=0.08
"""
        parsed = parse_feature_output(output)
        self.assertEqual(parsed["scene_changes"], [0.75])
        self.assertEqual([sample["time"] for sample in parsed["style_samples"]], [0.75, 2.25])
        self.assertAlmostEqual(parsed["style_samples"][0]["luma"], 0.2)
        self.assertAlmostEqual(parsed["style_samples"][1]["luma"], 0.8)
        self.assertEqual(parsed["style_samples"][0]["hue"], 15.0)


class MultimodalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.references = []
        for name, payload in (
            ("flash.mov", b"flash-ethereal-reference"),
            ("cyber.mov", b"3d-cyber-glitch-reference"),
            ("fluid.mov", b"fluid-sketch-reference"),
        ):
            path = self.root / name
            path.write_bytes(payload)
            self.references.append(path)
        self.editorial = self.root / "FINAL_canvas.edl"
        self.editorial.write_text("TITLE: FINAL_canvas\nFCM: NON-DROP FRAME\n", encoding="utf-8")

        self.config = {
            "schema_version": 1,
            "run_id": "fixture-run",
            "seed": 20260819,
            "evidence_files": [str(self.editorial)],
            "genres": [
                {
                    "number": 1,
                    "slug": "flash-ethereal",
                    "label": "Flash Ethereal",
                    "references": [str(self.references[0])],
                    "signature": {
                        "materials": ["glass bloom", "white phosphor"],
                        "motion": ["hard-cut flash", "slow orbital drift"],
                        "composition": ["high-key centered subject"],
                        "avoid": ["muddy shadows"],
                    },
                },
                {
                    "number": 2,
                    "slug": "3d-cyber-glitch",
                    "label": "3D Cyber Glitch",
                    "references": [str(self.references[1])],
                    "signature": {
                        "materials": ["wireframe chrome", "scanline emissive"],
                        "motion": ["depth orbit", "macroblock rupture"],
                        "composition": ["full-frame 3D interstitial"],
                        "avoid": ["decorative corner mesh"],
                    },
                },
                {
                    "number": 3,
                    "slug": "fluid-sketch",
                    "label": "Fluid Sketch",
                    "references": [str(self.references[2])],
                    "signature": {
                        "materials": ["ink wash", "graphite edge"],
                        "motion": ["nonlinear contour flow", "paper bleed"],
                        "composition": ["negative-space drawing field"],
                        "avoid": ["rigid neon grid"],
                    },
                },
            ],
        }
        self.config_path = self.root / "workflow.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def fake_probe(path: Path) -> dict:
        return {
            "duration": 6.0,
            "width": 1920,
            "height": 1080,
            "fps": 24.0,
            "codec": "fixture",
            "sample_times": [0.75, 2.25, 3.75, 5.25],
            "style_samples": [
                {"time": 0.75, "luma": 0.2, "saturation": 0.4},
                {"time": 2.25, "luma": 0.8, "saturation": 0.7},
            ],
            "scene_changes": [0.75, 2.25, 5.25],
        }

    def test_file_driven_run_emits_distinct_genres_and_all_modality_manifests(self):
        out = self.root / "out"
        receipt = run_workflow(self.config_path, out, probe=self.fake_probe)

        self.assertTrue(receipt["dry_run"])
        self.assertEqual(receipt["provider_calls"], 0)
        self.assertEqual(len(receipt["references"]), 3)
        self.assertEqual(len(receipt["evidence_files"]), 1)
        self.assertEqual(receipt["evidence_files"][0]["kind"], "editorial")
        self.assertEqual(len(receipt["evidence_files"][0]["sha256"]), 64)
        self.assertTrue(all(len(ref["sha256"]) == 64 for ref in receipt["references"]))
        emitted = {
            path.relative_to(out).as_posix()
            for path in out.rglob("*")
            if path.is_file() and path.name != "receipt.json"
        }
        bound = {artifact["path"] for artifact in receipt["evidence_artifacts"]}
        self.assertEqual(bound, emitted)
        self.assertTrue(receipt["evidence_artifacts"])
        for artifact in receipt["evidence_artifacts"]:
            self.assertGreater(artifact["bytes"], 0)
            self.assertEqual(len(artifact["sha256"]), 64)
            self.assertIn("genre_numbers", artifact)
            self.assertIn("modalities", artifact)
            self.assertFalse(artifact["provider_execution"])
            self.assertTrue(artifact["provenance"])
            for source in artifact["provenance"]:
                self.assertTrue(source["reference_path"])
                self.assertEqual(len(source["reference_sha256"]), 64)
                self.assertIn("reference_times", source)
                self.assertIn(source["time_basis"], {"media_seconds", "whole_file"})

        specs = [json.loads(path.read_text()) for path in sorted((out / "genres").glob("*.json"))]
        self.assertEqual([spec["number"] for spec in specs], [1, 2, 3])
        self.assertEqual(len({spec["style_fingerprint"] for spec in specs}), 3)
        self.assertEqual({spec["label"] for spec in specs}, {
            "Flash Ethereal", "3D Cyber Glitch", "Fluid Sketch"
        })
        for spec in specs:
            temporal = spec["measured_features"]["temporal"]
            style = spec["measured_features"]["style"]
            self.assertEqual(temporal["scene_change_count"], 3)
            self.assertGreater(temporal["scene_interval_variance"], 0)
            self.assertAlmostEqual(style["luma_mean"], 0.5)
            self.assertAlmostEqual(style["saturation_mean"], 0.55)

        for modality in ("image", "video", "3d_asset"):
            manifest = json.loads((out / "manifests" / f"{modality}.json").read_text())
            self.assertEqual(manifest["modality"], modality)
            self.assertEqual(len(manifest["requests"]), 3)
            self.assertTrue(all(request["prompt"] for request in manifest["requests"]))
            self.assertTrue(all(request["dry_run"] for request in manifest["requests"]))
            self.assertTrue(all(request["provider_call_mode"] == "disabled" for request in manifest["requests"]))
            self.assertFalse(manifest["provider_execution"])
            self.assertTrue(all(request["provider_execution"] is False for request in manifest["requests"]))
            self.assertTrue(all(request["endpoint_candidate"] for request in manifest["requests"]))
            self.assertTrue(all(request["request_body"]["prompt"] == request["prompt"]
                                for request in manifest["requests"]))

        validate_bundle(out)
        recipe = json.loads((out / "resolve" / "effect_recipe.json").read_text())
        self.assertEqual(recipe["seed"], self.config["seed"])
        self.assertFalse(recipe["periodic"])
        cv_events = [event for event in recipe["events"] if event["requires_subject_anchor"]]
        self.assertTrue(cv_events)
        self.assertTrue(all(event["subject_anchor"]["source_ref_sha256"] for event in cv_events))
        self.assertTrue(all(event["placement"]["max_coverage"] <= 0.35 for event in recipe["events"]))


if __name__ == "__main__":
    unittest.main()
