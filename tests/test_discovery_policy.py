"""Offline checks for the consequential discovery boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tooling.discover import Client, credential, photo_candidate


class CredentialTests(unittest.TestCase):
    def test_environment_override_does_not_read_shared_file(self):
        with patch.dict('os.environ', {'EBIRD_API_KEY': 'fixture-environment-value'}, clear=True):
            with patch('pathlib.Path.read_text', side_effect=AssertionError('file read')):
                self.assertEqual(credential('EBIRD_API_KEY'), 'fixture-environment-value')

    def test_shared_file_is_parsed_as_data_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            file = home / '.config/secrets/shared.env'
            file.parent.mkdir(parents=True)
            file.write_text('export EBIRD_API_KEY="fixture-$(never-execute)" # comment\n')
            with patch.dict('os.environ', {}, clear=True), patch('pathlib.Path.home', return_value=home):
                self.assertEqual(credential('EBIRD_API_KEY'), 'fixture-$(never-execute)')
                self.assertIsNone(credential('MISSING_KEY'))

    def test_credential_query_is_rejected_before_network(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network call')):
            with self.assertRaises(ValueError):
                Client().get('https://example.org/api', {'key': 'fixture-only'})


class CandidatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.target = {'taxon_id': 123, 'ebird_species_code': 'fixture'}
        self.obs = {'id': 10, 'uri': 'https://example.org/10', 'quality_grade': 'research',
                    'taxon': {'id': 123, 'name': 'Fixture species'}, 'community_taxon_id': 123,
                    'license_code': 'cc0', 'user': {'login': 'fixture-observer'},
                    'location': 'precise location must not escape', 'geojson': {'coordinates': [1, 2]},
                    'observed_on': '2026-01-01'}
        self.photo = {'id': 20, 'license_code': 'cc-by', 'url': 'https://example.org/square.jpg',
                      'attribution': 'fixture credit'}

    def test_observation_license_cannot_license_photo(self):
        for code in [None, '', 'all-rights-reserved', 'cc-by-nc', 'cc-by-nd']:
            with self.subTest(code=code):
                photo = {**self.photo, 'license_code': code}
                result = photo_candidate(self.obs, photo, self.target)
                self.assertEqual(result['review_state'], 'quarantined')
                self.assertIsNone(result['permitted_delivery'])

    def test_identity_mismatch_dispute_or_hidden_asset_is_held(self):
        cases = []
        changed = copy.deepcopy(self.obs)
        changed['community_taxon_id'] = 456
        cases.append((changed, self.photo))
        cases.append(({**self.obs, 'flags': [{'flag': 'identification concern'}]}, self.photo))
        cases.append((self.obs, {**self.photo, 'hidden': True}))
        for obs, photo in cases:
            self.assertEqual(photo_candidate(obs, photo, self.target)['review_state'], 'quarantined')

    def test_candidate_never_means_approved_or_invented_metadata(self):
        result = photo_candidate(self.obs, self.photo, self.target)
        self.assertEqual(result['review_state'], 'candidate')
        self.assertFalse(result['identification_verified'])
        for field in ['sex', 'age', 'plumage', 'pose', 'sha256', 'license_version', 'license_url']:
            self.assertIsNone(result[field])
        self.assertNotIn('precise location', json.dumps(result))
        self.assertNotIn('geojson', result)
        self.assertNotIn('location', result)
        self.assertIsNone(result['geography'])


if __name__ == '__main__':
    unittest.main()
