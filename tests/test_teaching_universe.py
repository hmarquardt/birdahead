import json
from pathlib import Path
import unittest
from tooling.teaching_universe import build_universe, _supported


def source(location, taxa, unresolved=()):
    data = {row['common']: row['values'] for row in taxa}
    data.update({name: [0.2] * 48 for name in unresolved})
    matches = {row['common']: {'comName': row['common'], 'sciName': row['scientific'],
                               'speciesCode': row['code'], 'taxonID': row['taxon']} for row in taxa}
    return {'location': location, 'sizes': [100] * 48, 'data': data, 'matches': matches,
            'mapped': {row['code']: row['common'] for row in taxa}, 'raw': ('fixture-' + location).encode()}


class TeachingUniverseTests(unittest.TestCase):
    def setUp(self):
        values = lambda v: [v] * 48
        taxa = [
            {'common': 'Fixture pilot', 'scientific': 'Pilotus fixture', 'code': 'pilot', 'taxon': 1, 'values': values(.01)},
            {'common': 'Fixture common', 'scientific': 'Communis fixture', 'code': 'common', 'taxon': 2, 'values': values(.8)},
            {'common': 'Fixture marker', 'scientific': 'Markerus fixture', 'code': 'marker', 'taxon': 3, 'values': values(.0015)},
        ]
        self.sources = [source(code, taxa, ['Mystery Sparrow'] if code == 'US-IN-051' else ()) for code in
                        ['US-IN-051', 'US-IN-055', 'US-IN-083', 'US-IN-125', 'US-IN-129', 'US-IN-163', 'US-IN-173']]
        self.poc = [{'ebird_species_code': 'pilot', 'common_name': 'Fixture pilot', 'scientific_name': 'Pilotus fixture'}]
        self.media = {'assets': [{'species_code': 'common', 'kind': 'photo'}]}

    def test_selection_retains_pilot_and_is_deterministic(self):
        first = build_universe(self.sources, 'fixture-2026', self.poc, self.media, limit=2)
        second = build_universe(self.sources, 'fixture-2026', self.poc, self.media, limit=2)
        universe = first[0]
        self.assertEqual(universe['species'], second[0]['species'])
        self.assertEqual(len(universe['species']), 2)
        self.assertEqual({row['ebird_species_code'] for row in universe['species']}, {'pilot', 'common'})
        self.assertEqual(universe['candidate_counts']['source_reconciled_species'], 3)
        self.assertEqual(universe['unresolved_scope']['US-IN-051'], 1)
        self.assertTrue(next(row for row in universe['species'] if row['pilot'])['pilot'])

    def test_suspicious_marker_and_zero_support_are_not_ranked(self):
        integrated = _supported([.0015] + [0] * 47, [100] * 48)
        self.assertIsNone(integrated[0]); self.assertEqual(integrated[1], 0)
        self.assertIsNone(_supported([0], [0])[0])
        supported = _supported([.25] * 48, [100] * 48)
        self.assertEqual(supported[0], .25)
        universe = build_universe(self.sources, 'fixture-2026', self.poc, self.media, limit=3)[0]
        marker = next(row for row in universe['species'] if row['ebird_species_code'] == 'marker')
        self.assertIsNone(marker['metrics']['annual_mean_frequency'])

    def test_limit_cannot_drop_the_versioned_pilot(self):
        with self.assertRaises(ValueError):
            build_universe(self.sources, 'fixture-2026', self.poc, self.media, limit=0)

    def test_wrong_source_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            build_universe(self.sources[:6], 'fixture-2026', self.poc, self.media)


if __name__ == '__main__':
    unittest.main()
