import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tooling.expansion as expansion


def observation(identifier, user='owner-1'):
    return {'id': identifier, 'user': {'id': user, 'name': 'Fixture contributor'},
            'quality_grade': 'research', 'community_taxon_id': 42, 'flags': [], 'captive': False,
            'taxon': {'id': 42, 'name': 'Fixture bird', 'rank': 'species', 'ancestor_ids': []},
            'photos': [{'id': 900 + identifier, 'license_code': 'cc-by', 'hidden': False, 'flags': [],
                        'url': f'https://inaturalist-open-data.s3.amazonaws.com/photos/{identifier}/square.jpg',
                        'original_dimensions': {'width': 1200, 'height': 800},
                        'attribution': '(c) Fixture, CC BY'}],
            'identifications': [{'current': True, 'user': {'id': 'identifier-' + str(identifier)},
                                 'taxon': {'id': 42, 'ancestor_ids': []}}],
            'observed_on': '2026-05-0' + str(identifier % 9 + 1), 'created_at': '2026-05-10',
            'num_identification_agreements': 2, 'num_identification_disagreements': 0,
            'annotations': [], 'owners_identification_from_vision': False}


class FakeClient:
    serial = 0

    def __init__(self, budget=100):
        self.calls = 0
        self.events = []
        self.budget = budget
        self.seed = FakeClient.serial
        FakeClient.serial += 1

    def json(self, endpoint, params, xc=False):
        if self.calls >= self.budget:
            raise RuntimeError('Bounded API request budget exhausted')
        self.calls += 1
        self.events.append({'endpoint': endpoint, 'query': params})
        if endpoint.endswith('/taxa'):
            name = params.get('q', 'Fixture bird')
            return {'results': [{'id': 42, 'name': name, 'rank': 'species'}]}
        if endpoint.endswith('/observations'):
            values = []
            for offset in range(3):
                number = 100 + self.seed * 10 + self.calls * 3 + offset
                values.append(observation(number, 'owner-' + str(offset + 1)))
            return {'results': values}
        if endpoint.endswith('/recordings'):
            return {'recordings': []}
        raise AssertionError('Unexpected endpoint')


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.catalog = self.root / 'catalog.json'
        self.state = self.root / 'expansion/state.json'
        self.report = self.root / 'phase-two-acquisition.json'
        self.media = self.root / 'media'
        self.universe = self.root / 'teaching-universe.json'
        self.species = [
            {'ebird_species_code': 'fixture-a', 'common_name': 'Fixture A', 'scientific_name': 'Fixture a',
             'priority_rank': 1, 'pilot': True},
            {'ebird_species_code': 'fixture-b', 'common_name': 'Fixture B', 'scientific_name': 'Fixture b',
             'priority_rank': 2, 'pilot': False}]
        self.universe.write_text(json.dumps({'schema': 'birdahead-teaching-universe-v1', 'species': self.species}))
        self.patches = [
            patch.object(expansion, 'STATE', self.state),
            patch.object(expansion, 'CATALOG', self.catalog),
            patch.object(expansion, 'REPORT', self.report),
            patch.object(expansion, 'WORK', self.root),
            patch.object(expansion, 'UNIVERSE', self.universe),
            patch.object(expansion, 'universe_species', lambda path=None: self.species),
        ]
        for item in self.patches:
            item.start()
        self.catalog.write_text('[]')

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def downloader(self, url, dest, limit, state, retries):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        raw = ('media:' + url).encode()
        Path(dest).write_bytes(raw)
        expansion._note_bytes(state, len(raw))
        return raw, None

    def metrics(self, path):
        return {'width': 1200, 'height': 800, 'edge_variance_256': 100, 'mean_luminance': 120,
                'dhash': '0123456789abcdef'}

    def test_deficit_plan_and_duplicate_free_resume(self):
        expansion.run(reset=True, max_species=1, max_assets=1, client=FakeClient(),
                      downloader=self.downloader, metrics_fn=self.metrics)
        checkpoint = json.loads(self.state.read_text())
        self.assertEqual(checkpoint['cursor'], 1)
        self.assertEqual(checkpoint['counters']['assets_added'], 1)
        self.assertEqual(len(json.loads(self.catalog.read_text())), 1)
        expansion.run(max_species=1, max_assets=1, client=FakeClient(),
                      downloader=self.downloader, metrics_fn=self.metrics)
        catalog = json.loads(self.catalog.read_text())
        checkpoint = json.loads(self.state.read_text())
        self.assertEqual(checkpoint['cursor'], 2)
        self.assertEqual(len(catalog), 2)
        self.assertEqual(len({asset['id'] for asset in catalog}), 2)
        self.assertTrue(checkpoint['complete'])

    def test_interrupted_batch_persists_and_continues_without_duplicates(self):
        calls = {'count': 0}
        def interrupting_metrics(path):
            calls['count'] += 1
            if calls['count'] == 2:
                raise KeyboardInterrupt
            return self.metrics(path)
        with self.assertRaises(KeyboardInterrupt):
            expansion.run(reset=True, max_species=1, max_assets=5, client=FakeClient(),
                          downloader=self.downloader, metrics_fn=interrupting_metrics)
        catalog = json.loads(self.catalog.read_text())
        checkpoint = json.loads(self.state.read_text())
        self.assertEqual(len(catalog), 1)
        self.assertEqual(checkpoint['cursor'], 0)
        self.assertEqual(checkpoint['counters']['assets_added'], 1)
        expansion.run(max_species=1, max_assets=2, client=FakeClient(),
                      downloader=self.downloader, metrics_fn=self.metrics)
        catalog = json.loads(self.catalog.read_text())
        self.assertEqual(len(catalog), 3)
        self.assertEqual(len({asset['id'] for asset in catalog}), 3)
        self.assertGreaterEqual(json.loads(self.state.read_text())['cursor'], 1)

    def test_request_budget_stops_without_retrying_forever(self):
        expansion.run(reset=True, max_species=2, budgets={'requests': 1}, client=FakeClient(budget=1),
                      downloader=self.downloader, metrics_fn=self.metrics)
        checkpoint = json.loads(self.state.read_text())
        self.assertTrue(any('request budget' in reason for reason in checkpoint['failures']))
        self.assertEqual(checkpoint['budgets']['requests'], 1)

    def test_prefilter_rejects_low_resolution_duplicate_contributor_and_missing_support(self):
        state = expansion.plan([], self.species)
        valid = observation(200)
        low = observation(201); low['photos'][0]['original_dimensions'] = {'width': 300, 'height': 200}
        unsupported = observation(202); unsupported['identifications'] = []
        options = expansion._photo_options({'results': [valid, low, unsupported]}, self.species[0], 42,
                                           {'owner-1': 2}, set(), True)
        self.assertEqual(options, [])
        options = expansion._photo_options({'results': [valid]}, self.species[0], 42,
                                           {'owner-1': 0}, set(), False)
        self.assertEqual(len(options), 1)


if __name__ == '__main__':
    unittest.main()
