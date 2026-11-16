import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "app/public/discovery.json"
RELEASE = ROOT / "experiments/private/local-mvp/release.json"

class DiscoveryCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(DISCOVERY.read_text())

    def test_catalog_preserves_bins_missingness_and_separates_teaching(self):
        self.assertEqual(self.catalog["schema"], "birdahead-discovery-v1")
        self.assertEqual(len(self.catalog["species"]), 333)
        self.assertEqual(sum(row["teaching"] for row in self.catalog["species"]), 100)
        self.assertEqual(len(self.catalog["bins"]), 48)
        self.assertEqual(self.catalog["bins"][0]["start"], "2001-01-01")
        self.assertEqual(self.catalog["bins"][-1]["end"], "2002-01-01")
        self.assertEqual(self.catalog["counties"]["US-IN-051"]["name"], "Gibson")
        self.assertEqual(len(self.catalog["counties"]["US-IN-051"]["sample_sizes"]), 48)
        self.assertTrue(any(value is None for row in self.catalog["species"] for county in row["counties"].values() for value in county))
        self.assertTrue(any(not row["teaching"] for row in self.catalog["species"]))
        self.assertTrue(any(row["practice_ready"] for row in self.catalog["species"]))
        self.assertTrue(any(not row["practice_ready"] for row in self.catalog["species"]))

    def test_regional_frequency_is_sample_weighted_not_county_average(self):
        row = next(row for row in self.catalog["species"] if row["code"] == "mallar3")
        sizes = self.catalog["counties"]
        index = 0
        values = [(row["counties"][code][index], sizes[code]["sample_sizes"][index]) for code in sizes]
        values = [(value, weight) for value, weight in values if value is not None and weight]
        expected = sum(value * weight for value, weight in values) / sum(weight for _, weight in values)
        self.assertAlmostEqual(row["regional"]["frequency"][index], round(expected, 7), places=7)
        self.assertEqual(row["regional"]["support"][index], sum(weight for _, weight in values))
        self.assertEqual(row["regional"]["counties_used"][index], len(values))

    @unittest.skipUnless(RELEASE.exists(), "private accepted release is not present in this checkout")
    def test_teaching_profiles_match_imported_release_exactly(self):
        release = json.loads(RELEASE.read_text())
        selected = {row["ebird_species_code"]: row for row in release["species"]}
        for row in self.catalog["species"]:
            if not row["teaching"]:
                continue
            self.assertIn(row["code"], selected)
            for county, values in row["counties"].items():
                expected = [item["frequency"] for item in release["profiles"][county]["rows"] if item["species_code"] == row["code"]]
                self.assertEqual(values, expected)

if __name__ == "__main__":
    unittest.main()
