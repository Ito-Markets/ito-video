"""Failing-first tests: offline fixture path + documented provenance."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FIXTURE = REPO_ROOT / "tasteforge" / "fixtures" / "flashethereal"
PROVENANCE_MD = REPO_ROOT / "PROVENANCE.md"


class OfflineFixtureTests(unittest.TestCase):
    def test_fixture_contains_recovered_metadata_only(self):
        names = {p.name for p in FIXTURE.iterdir()}
        self.assertIn("pack.json", names)
        self.assertIn("grade.json", names)
        self.assertIn("cadence.json", names)
        self.assertIn("spec.json", names)
        self.assertIn("grounding.txt", names)
        # Deliberately excluded heavy/binary recovered artifacts.
        self.assertNotIn("look.cube", names)
        self.assertFalse(any(n.endswith(".glb") for n in names))
        self.assertFalse(any(n.endswith(".png") for n in names))
        self.assertNotIn(".DS_Store", names)

    def test_cadence_statistics_are_self_consistent(self):
        cad = json.loads((FIXTURE / "cadence.json").read_text())
        durs = [s["duration"] for s in cad["shots"]]
        self.assertEqual(cad["n_shots"], len(durs))
        self.assertAlmostEqual(cad["mean_shot"], sum(durs) / len(durs), places=2)
        self.assertGreater(cad["cuts_per_min"], 50)

    def test_grade_has_zone_structure(self):
        grade = json.loads((FIXTURE / "grade.json").read_text())
        self.assertEqual(len(grade["zones"]), 5)
        self.assertEqual(len(grade["palette"][0]), 2)
        self.assertEqual(len(grade["l_cdf"]), 256)

    def test_pack_manifest_matches_recovered_values(self):
        manifest = json.loads((FIXTURE / "pack.json").read_text())
        self.assertEqual(manifest["name"], "flashethereal")
        self.assertEqual(len(manifest["refs"]), 3)
        self.assertEqual(manifest["mint"]["lut_size"], 33)
        self.assertTrue(manifest["distill"]["dry_run"])


class ProvenanceDocTests(unittest.TestCase):
    def test_provenance_md_documents_lineage_and_exclusions(self):
        text = PROVENANCE_MD.read_text()
        self.assertIn("ef06a606d3b528fbd939b05fadc25bf6674073a1e05a01e3aa6b9c9416fd6284", text)
        self.assertIn("/Users/affoon/Movies/Ito/tasteforge-flow-20260818", text)
        self.assertIn("cse_01Tmgz8ezNwk64Zx7MUgsiUy", text)
        self.assertIn("look.cube", text)  # documented exclusion
        self.assertIn("fixtures/flashethereal", text)

    def test_readme_documents_operator_workflow(self):
        readme = (REPO_ROOT / "tasteforge" / "README.md").read_text()
        for cmd in ("inspect", "validate", "interview", "distill", "apply", "export"):
            self.assertIn(cmd, readme)


if __name__ == "__main__":
    unittest.main()
