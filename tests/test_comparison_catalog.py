import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app/public/comparisons.json"
RELEASE = ROOT / "experiments/private/local-mvp/release.json"

class ComparisonCatalogTests(unittest.TestCase):
    def test_catalog_has_sources_and_explicit_gaps(self):
        catalog = json.loads(CATALOG.read_text())
        self.assertEqual(catalog["schema"], "birdahead-comparison-catalog-v1")
        self.assertEqual(catalog["review_status"], "provisional_curated")
        source_ids = set(catalog["sources"])
        self.assertGreaterEqual(len(source_ids), 8)
        self.assertGreaterEqual(len(catalog["pairs"]), 4)
        for pair in catalog["pairs"]:
            self.assertTrue(pair["gaps"], pair["id"])
            for trait in pair["traits"]:
                self.assertTrue(trait["source_ids"], (pair["id"], trait["dimension"]))
                self.assertTrue(set(trait["source_ids"]) <= source_ids)

    @unittest.skipUnless(RELEASE.exists(), "private accepted release is not present in this checkout")
    def test_catalog_covers_reviewed_confusion_pairs(self):
        catalog = json.loads(CATALOG.read_text())
        release = json.loads(RELEASE.read_text())
        expected = {tuple(sorted((row["left"], row["right"]))) for row in release["confusion_pairs"]}
        actual = {tuple(sorted((row["left"]["name"], row["right"]["name"]))) for row in catalog["pairs"]}
        self.assertEqual(actual, expected)

if __name__ == "__main__":
    unittest.main()

