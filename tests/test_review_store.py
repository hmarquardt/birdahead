import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from tooling.review_store import Store


class ReviewStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=Store(self.root/'review.sqlite',budget=20)
        self.asset={'id':'fixture','sha256':hashlib.sha256(b'fixture-media').hexdigest(),'species_code':'fixture-species','creator':'Fixture creator',
                    'source_url':'https://example.org/source','license_url':'https://creativecommons.org/licenses/by/4.0/','license_version':'4.0',
                    'local_path':str(self.root/'media.jpg'),'automated_decision':{'rights':'pending','biology':'pending','status':'candidate'}}
        (self.root/'media.jpg').write_bytes(b'fixture-media');self.db.sync([self.asset])
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def finish(self,gate,action,evidence='fixture evidence',reason='fixture reason'):
        s=self.db.start('fixture','Automated fixture reviewer');return self.db.finish(s,gate,action,reason,evidence)
    def test_rights_and_biology_are_independent(self):
        self.finish('biology','approve');self.assertEqual(self.db.state('fixture')['rights'],'pending')
        with patch('tooling.review_store.PRIVATE',self.root):self.assertEqual(self.db.export(self.root/'out.json')['approved_assets'],0)
        self.finish('rights','approve')
        with patch('tooling.review_store.PRIVATE',self.root):
            first=self.db.export(self.root/'out.json');second=self.db.export(self.root/'out.json')
        self.assertEqual(first,second);self.assertEqual(first['approved_assets'],1);self.assertTrue(self.db.verify())
    def test_automatic_acceptance_needs_no_individual_human_review(self):
        self.asset['automated_decision']={'rights':'approved','biology':'approved','status':'automatically_accepted'};self.db.sync([self.asset])
        state=self.db.state('fixture');self.assertEqual(state['status'],'automatically_accepted');self.assertFalse(state['human_approved'])
    def test_rejection_requires_reason_and_never_exports(self):
        session=self.db.start('fixture','Fixture')
        with self.assertRaises(ValueError):self.db.finish(session,'biology','reject','')
        self.db.finish(session,'biology','quarantine','conflicting identification')
        self.finish('rights','approve')
        with patch('tooling.review_store.PRIVATE',self.root):self.assertEqual(self.db.export(self.root/'out.json')['approved_assets'],0)
    def test_approval_is_bound_to_media_and_rights_evidence(self):
        self.finish('biology','approve');self.finish('rights','approve');self.asset['license_url']='https://example.org/different-rights';self.db.sync([self.asset])
        self.assertEqual(self.db.state('fixture')['status'],'candidate');self.assertFalse(self.db.state('fixture')['human_approved'])
    def test_budget_blocks_approval_and_allows_defer(self):
        with patch('tooling.review_store.time.time',return_value=100):session=self.db.start('fixture','Fixture')
        with patch('tooling.review_store.time.time',return_value=121):
            with self.assertRaises(ValueError):self.db.finish(session,'biology','approve','reason','evidence')
            self.db.finish(session,'asset','defer','budget exhausted')
            with self.assertRaises(ValueError):self.db.start('fixture','Fixture')
    def test_audit_events_cannot_be_updated_or_deleted(self):
        self.finish('asset','defer')
        with self.assertRaises(sqlite3.IntegrityError):self.db.connection.execute("UPDATE events SET payload='tampered'")
        with self.assertRaises(sqlite3.IntegrityError):self.db.connection.execute('DELETE FROM events')
        self.assertTrue(self.db.verify())
    def test_only_one_active_session(self):
        self.db.start('fixture','Fixture')
        with self.assertRaises(ValueError):self.db.start('fixture','Other tab')


if __name__=='__main__':unittest.main()
