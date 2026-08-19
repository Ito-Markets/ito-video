"""Failing-first tests for the tasteforge CLI (python3 -m tasteforge)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tasteforge import cli

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tasteforge" / "fixtures" / "flashethereal"

ANSWERS = {
    "palette": "near-black void, bone white, violet bloom",
    "grain": "fine 35mm grain",
    "lighting": "single hard key",
    "focal_length": "35mm",
    "camera_motion": "locked off",
    "subject_framing": "centered, headroom",
    "grade_description": "crushed blacks",
    "mood_adjectives": "holy, crystalline",
    "avoid": "plastic highlights",
    "brief": "courier in night traffic",
}

MEDIA = {
    "clips": [
        {"path": "/tmp/media/a.mov", "duration": 5.0, "name": "a"},
        {"path": "/tmp/media/b.mov", "duration": 4.0, "name": "b"},
    ]
}


def run_cli(*args, expect=0):
    proc = subprocess.run(
        [sys.executable, "-m", "tasteforge", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return proc


class CliTests(unittest.TestCase):
    def test_multimodal_command_routes_file_contract_and_validates_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "workflow.json"
            config.write_text("{}", encoding="utf-8")
            out = Path(td) / "out"
            expected = {"provider_calls": 0, "provider_execution": False}
            with mock.patch(
                "tasteforge.cli.workflow_mod.run_workflow", return_value=expected
            ) as run, mock.patch("tasteforge.cli.contract_mod.validate_bundle") as validate:
                status = cli.main([
                    "multimodal", "--config", str(config), "--out-dir", str(out)
                ])
            self.assertEqual(status, 0)
            run.assert_called_once_with(config, out)
            validate.assert_called_once_with(out)
    def test_provenance_subcommand(self):
        proc = run_cli("provenance", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("generations", data)

    def test_inspect_subcommand(self):
        proc = run_cli("inspect", str(FIXTURE), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["name"], "flashethereal")

    def test_validate_subcommand_ok_and_fail(self):
        proc = run_cli("validate", str(FIXTURE))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "badpack"
            bad.mkdir()
            (bad / "pack.json").write_text("{}")
            proc = run_cli("validate", str(bad))
            self.assertNotEqual(proc.returncode, 0)

    def test_interview_distill_apply_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            answers_p = Path(td) / "answers.json"
            profile_p = Path(td) / "profile.json"
            spec_p = Path(td) / "spec.json"
            report_p = Path(td) / "report.json"
            media_p = Path(td) / "media.json"
            events_p = Path(td) / "events.json"
            answers_p.write_text(json.dumps(ANSWERS))
            media_p.write_text(json.dumps(MEDIA))

            proc = run_cli("interview", "--answers", str(answers_p),
                           "--genre", "flashethereal", "--out", str(profile_p))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(profile_p.exists())

            proc = run_cli("distill", "--profile", str(profile_p),
                           "--pack", str(FIXTURE), "--out", str(spec_p))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            spec = json.loads(spec_p.read_text())
            self.assertTrue(spec["source"]["dry_run"])

            proc = run_cli("apply", "--pack", str(FIXTURE), "--media", str(media_p),
                           "--duration", "10", "--out", str(report_p))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(report_p.read_text())
            self.assertEqual(report["provider"], "none")
            events_p.write_text(json.dumps({"clips": report["timeline_events"]}))

            proc = run_cli("export", "--events", str(events_p),
                           "--out-dir", td, "--title", "cli-test")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(td) / "cli-test.edl").exists())
            self.assertTrue((Path(td) / "cli-test.fcpxml").exists())

    def test_live_provider_flags_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            profile_p = Path(td) / "profile.json"
            run_cli("interview", "--answers", self._write(td, ANSWERS),
                    "--genre", "g", "--out", str(profile_p))
            proc = run_cli("distill", "--profile", str(profile_p), "--live")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("separately authorized", proc.stderr + proc.stdout)
            media_p = Path(td) / "media.json"
            media_p.write_text(json.dumps(MEDIA))
            proc = run_cli("apply", "--pack", str(FIXTURE),
                           "--media", str(media_p), "--live")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("separately authorized", proc.stderr + proc.stdout)

    @staticmethod
    def _write(td, obj):
        p = Path(td) / "answers.json"
        p.write_text(json.dumps(obj))
        return str(p)


if __name__ == "__main__":
    unittest.main()
