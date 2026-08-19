"""Failing-first tests for applying a pack to local media (deterministic only)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tasteforge import apply as apply_mod, pack as pack_mod, schema  # noqa: E402

FIXTURE = REPO_ROOT / "tasteforge" / "fixtures" / "flashethereal"

MEDIA = {
    "clips": [
        {"path": "/tmp/media/shot_a.mov", "duration": 6.2, "name": "shot_a"},
        {"path": "/tmp/media/shot_b.mov", "duration": 4.8, "name": "shot_b"},
        {"path": "/tmp/media/shot_c.mov", "duration": 8.1, "name": "shot_c"},
    ]
}


class ApplyLocalTests(unittest.TestCase):
    def test_apply_local_report_is_schema_valid(self):
        sp = pack_mod.load(FIXTURE)
        report = apply_mod.apply_local(sp, MEDIA["clips"])
        problems = schema.validate(report, schema.APPLICATION_REPORT_SCHEMA)
        self.assertEqual(problems, [])

    def test_report_claims_no_provider(self):
        report = apply_mod.apply_local(pack_mod.load(FIXTURE), MEDIA["clips"])
        self.assertEqual(report["provider"], "none")
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["mode"], "local-deterministic")

    def test_planned_shots_follow_cadence_and_fill_duration(self):
        sp = pack_mod.load(FIXTURE)
        report = apply_mod.apply_local(sp, MEDIA["clips"], duration=20.0)
        durations = [s["duration"] for s in report["planned_shots"]]
        self.assertGreater(len(durations), 3, "77-cut cadence must not plan 3 shots")
        self.assertLessEqual(sum(durations), 20.0 + max(durations))
        self.assertEqual(len(report["timeline_events"]), len(durations))

    def test_apply_local_deterministic(self):
        sp = pack_mod.load(FIXTURE)
        a = apply_mod.apply_local(sp, MEDIA["clips"], duration=12.0)
        b = apply_mod.apply_local(sp, MEDIA["clips"], duration=12.0)
        a.pop("generated"), b.pop("generated")
        self.assertEqual(a, b)

    def test_events_reference_local_paths(self):
        report = apply_mod.apply_local(pack_mod.load(FIXTURE), MEDIA["clips"], duration=8.0)
        for event in report["timeline_events"]:
            self.assertTrue(event["path"].startswith("/tmp/media/"))
            self.assertGreater(event["frames"], 0)

    def test_provider_generation_fails_closed(self):
        with self.assertRaises(apply_mod.ProviderDisabledError):
            apply_mod.apply_generate(pack_mod.load(FIXTURE), brief="x")


if __name__ == "__main__":
    unittest.main()
