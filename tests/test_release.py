import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tooling.local_release as release
from tooling.seasonal import COUNTIES


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.private = self.root / 'private'
        self.private.mkdir()
        (self.root / 'experiments').mkdir()
        self.poc = [{'ebird_species_code': f'p{index}', 'common_name': f'Pilot {index}',
                     'scientific_name': f'Pilotus {index}'} for index in range(25)]
        (self.root / 'experiments/poc-species.json').write_text(json.dumps(self.poc))
        media = self.private / 'media/a.jpg'
        media.parent.mkdir(parents=True)
        media.write_bytes(b'release fixture media')
        self.sha = hashlib.sha256(media.read_bytes()).hexdigest()
        self.universe = {'taxonomy': {'authority': 'eBird/Clements', 'version': '2026'},
                         'source_scope': {'start_year': 2016, 'end_year': 2025, 'counties': COUNTIES}}
        self.profiles = {location: {'rows': [{'species_code': row['ebird_species_code']} for row in self.poc for _ in range(48)]}
                         for location in COUNTIES}
        self.asset = {'id': 'fixture-asset', 'kind': 'photo', 'species_code': 'p0',
                      'local_path': 'private/media/a.jpg', 'sha256': self.sha,
                      'automated_decision': {'status': 'automatically_accepted'}}
        self.payload = {'species': self.poc, 'profiles': self.profiles, 'assets': [self.asset]}
        self.patches = [patch.object(release, 'ROOT', self.root), patch.object(release, 'PRIVATE', self.private)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_valid_release_compiles_and_checks_media(self):
        self.assertTrue(release.validate(self.payload))
        coverage = release.coverage(self.poc, self.payload['assets'])
        self.assertEqual(coverage['p0']['photos'], 1)
        self.assertFalse(coverage['p0']['photo_practice_ready'])
        self.assertEqual(coverage['p1']['photos'], 0)

    def test_missing_pilot_or_incomplete_bins_is_rejected(self):
        self.payload['species'] = self.poc[1:]
        with self.assertRaises(ValueError):
            release.validate(self.payload)
        self.payload['species'] = self.poc
        self.profiles['US-IN-051']['rows'].pop()
        with self.assertRaises(ValueError):
            release.validate(self.payload)

    def test_nonaccepted_or_checksum_changed_media_is_rejected(self):
        self.asset['automated_decision'] = {'status': 'defer'}
        with self.assertRaises(ValueError):
            release.validate(self.payload)
        self.asset['automated_decision'] = {'status': 'automatically_accepted'}
        self.asset['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            release.validate(self.payload)

    def test_media_outside_private_storage_is_rejected(self):
        self.asset['local_path'] = '../../outside.jpg'
        with self.assertRaises(ValueError):
            release.validate(self.payload)

    def test_compatibility_key_survives_additive_content_but_not_scope_change(self):
        first = release.compatibility_key(self.universe, self.profiles)
        added = {'species': self.poc + [{'ebird_species_code': 'p99'}], 'profiles': self.profiles, 'assets': []}
        self.assertEqual(first, release.compatibility_key(self.universe, self.profiles))
        changed = {'taxonomy': {'authority': 'eBird/Clements', 'version': '2027'},
                   'source_scope': self.universe['source_scope']}
        self.assertNotEqual(first, release.compatibility_key(changed, self.profiles))


if __name__ == '__main__':
    unittest.main()
