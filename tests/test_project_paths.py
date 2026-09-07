"""Portable project footage resolution and public manifest boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from project_paths import footage_root, resolve_source, portable_source, manifest_output, protect_output


class ProjectPathsTests(unittest.TestCase):
    def test_annotations_are_deferred_for_python39(self):
        # Python 3.9 cannot evaluate ``str | None`` during module import.
        self.assertIsInstance(footage_root.__annotations__['configured'], str)

    def test_default_and_environment_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            raw = project / 'assets/raw'
            raw.mkdir(parents=True)
            with patch.dict('os.environ', {}, clear=True):
                self.assertEqual(footage_root(project), raw)
            with patch.dict('os.environ', {'ITO_FOOTAGE_ROOT': tmp}):
                self.assertEqual(footage_root(project), project)

    def test_cli_overrides_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict('os.environ', {'ITO_FOOTAGE_ROOT': 'missing'}):
                self.assertEqual(footage_root(Path(tmp), tmp), Path(tmp).resolve())

    def test_missing_configuration_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict('os.environ', {}, clear=True):
                with self.assertRaisesRegex(FileNotFoundError, 'ITO_FOOTAGE_ROOT'):
                    footage_root(Path(tmp))

    def test_external_footage_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            clip = root / 'talking/clip.mov'
            clip.parent.mkdir()
            clip.touch()
            reference = portable_source(clip, root)
            self.assertEqual(reference, 'footage://talking/clip.mov')
            self.assertEqual(resolve_source(reference, root, root), clip)
            with self.assertRaises(ValueError):
                resolve_source('footage://../outside.mov', root, root)

    def test_project_relative_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            clip = root / 'clip.mp4'
            clip.touch()
            self.assertEqual(resolve_source('clip.mp4', root, root), clip)
            with self.assertRaises(FileNotFoundError):
                resolve_source('missing.mp4', root, root)

    def test_existing_outputs_and_media_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'existing.json'
            path.write_text('{}')
            with self.assertRaises(FileExistsError):
                manifest_output(path, False)
            self.assertEqual(path.read_text(), '{}')
            manifest_output(path, True)
            with self.assertRaises(ValueError):
                manifest_output(path.with_suffix('.mp4'), True)
            link = Path(tmp) / 'dangling.json'
            link.symlink_to(Path(tmp) / 'missing.json')
            for overwrite in (False, True):
                with self.assertRaises(ValueError):
                    protect_output(link, overwrite)

    def test_public_manifest_paths_are_portable(self):
        root = Path(__file__).resolve().parents[1]
        for entry in json.loads((root / 'edl.json').read_text())['pool']:
            self.assertFalse(Path(entry['src']).is_absolute())
        for line in (root / 'concat.txt').read_text().splitlines():
            self.assertTrue(line.startswith("file 'trims/"))
        for name in ('scan_sources.py', 'build_edl.py', 'build_ito.py', 'edl.json', 'concat.txt'):
            self.assertNotIn('/' + 'Users/', (root / name).read_text())


if __name__ == '__main__':
    unittest.main()
