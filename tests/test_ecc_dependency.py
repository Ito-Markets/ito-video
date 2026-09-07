"""The Ito example consumes the installed ECC engine wheel."""
import importlib.metadata
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import tasteforge

REPO_ROOT = Path(__file__).resolve().parents[1]


class EccDependencyTests(unittest.TestCase):
    def test_runtime_is_installed_outside_example_checkout(self):
        self.assertFalse((REPO_ROOT / "tasteforge").exists())
        self.assertFalse(Path(tasteforge.__file__).resolve().is_relative_to(REPO_ROOT))
        dist = importlib.metadata.distribution("ecc-tasteforge")
        self.assertTrue(any(str(p).endswith(".dist-info/WHEEL") for p in dist.files))
        self.assertTrue(any(e.name == "tasteforge" for e in dist.entry_points))
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run(
                [sys.executable, "-c", "import tasteforge,json; from pathlib import Path; "
                 "print(json.dumps({'path': tasteforge.__file__, 'fixture': "
                 "(Path(tasteforge.__file__).parent/'fixtures/flashethereal/pack.json').exists()}))"],
                cwd=cwd, capture_output=True, text=True, check=True,
            )
        self.assertTrue(json.loads(result.stdout)["fixture"])


if __name__ == "__main__":
    unittest.main()
