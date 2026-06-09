"""Тесты для core/manifest.py: load, save, dry_run."""

import json
import os
import tempfile
import unittest

from repo_ctx.core.manifest import MANIFEST_FILENAME, load_manifest, save_manifest
from repo_ctx.exceptions import ManifestError


class TestLoadManifest(unittest.TestCase):
    def test_returns_none_when_file_absent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_manifest(d))

    def test_loads_valid_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            data = {"source": "/some/path", "profile": "microservice"}
            with open(os.path.join(d, MANIFEST_FILENAME), "w") as f:
                json.dump(data, f)
            result = load_manifest(d)
        self.assertEqual(result, data)

    def test_raises_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, MANIFEST_FILENAME), "w") as f:
                f.write("{not valid json")
            with self.assertRaises(ManifestError):
                load_manifest(d)


class TestSaveManifest(unittest.TestCase):
    def test_saves_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            data = {"profile": "default", "managed_files": ["CLAUDE.md"]}
            save_manifest(d, data)
            result = load_manifest(d)
        self.assertEqual(result, data)

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            save_manifest(d, {"profile": "x"}, dry_run=True)
            self.assertFalse(os.path.exists(os.path.join(d, MANIFEST_FILENAME)))

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as d:
            save_manifest(d, {"profile": "old"})
            save_manifest(d, {"profile": "new"})
            result = load_manifest(d)
        self.assertEqual(result["profile"], "new")


if __name__ == "__main__":
    unittest.main()
