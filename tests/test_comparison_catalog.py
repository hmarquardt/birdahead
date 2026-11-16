import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ComparisonCatalogTests(unittest.TestCase):
    def test_catalog_covers_reviewed_confusion_pairs_with_sources_and_gaps(self):
        catalog = json.loads((ROOT / "app/public/comparisons.json").read_text())
        release = json.loads((ROOT / "experiments/private/local-mvp/release.json").read_text())
        expected = {tuple(sorted((row["left"], row["right"]))) for row in release["confusion_pairs"]}
        actual = {tuple(sorted((row["left"]["name"], row["right"]["name"]))) for row in catalog["pairs"]}
        self.assertEqual(actual, expected)
        self.assertEqual(catalog["review_status"], "provisional_curated")
        source_ids = set(catalog["sources"])
        for pair in catalog["pairs"]:
            self.assertTrue(pair["gaps"], pair["id"])
            for trait in pair["traits"]:
                self.assertTrue(trait["source_ids"], (pair["id"], trait["dimension"]))
                self.assertTrue(set(trait["source_ids"]) <= source_ids)

if __name__ == "__main__":
    unittest.main()
