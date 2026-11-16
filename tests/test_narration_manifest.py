import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NARRATION = ROOT / "app/public/narration"

class NarrationManifestTests(unittest.TestCase):
    def test_kokoro_manifest_hashes_and_has_no_apple_m4a_assets(self):
        manifest = json.loads((NARRATION / "manifest.json").read_text())
        self.assertEqual(manifest["narration_version"], "kokoro-82m-af_heart-v1")
        self.assertEqual(manifest["model"], "hexgrad/Kokoro-82M")
        self.assertEqual(manifest["model_license"], "Apache-2.0")
        self.assertEqual(manifest["schema"], "birdahead-narration-v2")
        self.assertGreaterEqual(len(manifest["files"]), 100)
        self.assertFalse(list(NARRATION.rglob("*.m4a")))
        for relative, metadata in manifest["files"].items():
            path = NARRATION / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(path.stat().st_size, metadata["bytes"], relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), metadata["sha256"], relative)

if __name__ == "__main__":
    unittest.main()
