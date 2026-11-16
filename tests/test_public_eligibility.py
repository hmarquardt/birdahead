import unittest
from tooling.public_eligibility import evaluate

BASE = {
    'permitted_delivery': True, 'license_code': 'cc-by', 'source': 'inaturalist',
    'license_url': 'https://creativecommons.org/licenses/by/4.0/', 'creator': 'A',
    'source_url': 'https://example.org/1', 'attribution': 'A, CC BY 4.0',
}

class PublicEligibilityTests(unittest.TestCase):
    def test_all_supported_source_licenses_are_public_noncommercial(self):
        for code in ['cc0', 'cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa']:
            result = evaluate({**BASE, 'license_code': code})
            self.assertTrue(result['public_delivery'], code)
            self.assertTrue(result['public_use_basis'])
        self.assertFalse(evaluate({**BASE, 'license_code': 'cc-by-nd'})['public_delivery'])

    def test_missing_attribution_or_delivery_permission_blocks_public_use(self):
        self.assertFalse(evaluate({**BASE, 'attribution': None})['public_delivery'])
        self.assertFalse(evaluate({**BASE, 'permitted_delivery': False})['public_delivery'])
        self.assertFalse(evaluate({**BASE, 'source': 'unknown'})['public_delivery'])

    def test_share_alike_and_noncommercial_flags_are_preserved(self):
        self.assertTrue(evaluate({**BASE, 'license_code': 'cc-by-nc-sa'})['public_share_alike'])
        self.assertTrue(evaluate({**BASE, 'license_code': 'cc-by-nc-sa'})['public_noncommercial_only'])
        self.assertFalse(evaluate({**BASE, 'license_code': 'cc-by-sa'})['public_noncommercial_only'])
