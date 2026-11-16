import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tooling.delivery_manifest as delivery


class DeliveryManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.private = self.root / 'private'
        (self.private / 'media').mkdir(parents=True)
        rows = []
        for asset_id, license_code in [('a', 'cc-by'), ('b', 'cc-by-nc-sa')]:
            path = self.private / 'media' / f'{asset_id}.jpg'
            path.write_bytes(('media-' + asset_id).encode())
            rows.append({'id': asset_id, 'kind': 'photo', 'species_code': 'fixture', 'local_path': str(path.relative_to(self.root)),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'creator': 'Fixture creator',
                         'license_code': license_code, 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                         'attribution': 'Fixture attribution', 'source': 'inaturalist', 'source_url': 'https://example.org/record',
                         'permitted_delivery': True, 'share_alike': license_code.endswith('sa'),
                         'commercial_compatible': license_code == 'cc-by', 'derivative_of': None,
                         'presentation_modification_notice': None})
        self.release_path = self.root / 'release.json'
        self.release_path.write_text(json.dumps({'schema': 'birdahead-local-release-v2', 'id': 'fixture-release',
                                                 'compatibility_key': 'fixture-family', 'assets': rows}))
        self.output = self.root / 'delivery.json'
        self.patches = [patch.object(delivery, 'ROOT', self.root), patch.object(delivery, 'PRIVATE', self.private)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_manifest_has_no_private_paths_and_reports_restrictions(self):
        report = delivery.build(self.release_path, self.output)
        self.assertEqual(report['object_count'], 2)
        self.assertEqual(report['total_bytes'], len(b'media-a') + len(b'media-b'))
        self.assertEqual(report['projected_r2']['projected_usd_per_month'], 0.0)
        self.assertIn('license:cc-by|source:inaturalist|derivative:false', report['restrictions'])
        self.assertIn('license:cc-by-nc-sa|source:inaturalist|derivative:false', report['restrictions'])
        self.assertTrue(all('local_path' not in obj for obj in report['objects']))
        self.assertEqual({obj['key'] for obj in report['objects']}, {'media/a.jpg', 'media/b.jpg'})

    def test_checksum_change_is_rejected(self):
        (self.private / 'media/a.jpg').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            delivery.build(self.release_path, self.output)


if __name__ == '__main__':
    unittest.main()
