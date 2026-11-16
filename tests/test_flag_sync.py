import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import tooling.flag_sync as flag_sync
import tooling.review_store as review_store
from tooling.review_store import Store


class FlagSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.private = self.root / 'private'
        self.private.mkdir()
        media = self.private / 'media/a.jpg'
        media.parent.mkdir(parents=True)
        media.write_bytes(b'flag fixture media')
        self.asset = {'id': 'fixture-asset', 'kind': 'photo', 'species_code': 'fixture-bird',
                      'creator': 'Fixture creator', 'source_url': 'https://example.org/record',
                      'license_url': 'https://creativecommons.org/licenses/by/4.0/', 'license_version': '4.0',
                      'local_path': str(media.relative_to(self.root)), 'sha256': hashlib.sha256(media.read_bytes()).hexdigest(),
                      'automated_decision': {'rights': 'approved', 'biology': 'approved', 'status': 'automatically_accepted'}}
        self.review_db = self.root / 'reviews.sqlite'
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps([self.asset]))
        self.learner_db = self.root / 'learning.sqlite'
        self.report_path = self.root / 'flag-report.json'
        self.patches = [patch.object(review_store, 'PRIVATE', self.private),
                        patch.object(flag_sync, 'PRIVATE', self.private)]
        for item in self.patches:
            item.start()
        store = Store(self.review_db)
        store.sync([self.asset])
        store.close()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def flags(self, rows):
        connection = sqlite3.connect(self.learner_db)
        connection.execute('CREATE TABLE IF NOT EXISTS flags(id TEXT PRIMARY KEY,profile_id TEXT,asset_id TEXT,release_id TEXT,session_id TEXT,reason TEXT,suggested_species TEXT,at TEXT)')
        connection.executemany('INSERT OR REPLACE INTO flags VALUES(?,?,?,?,?,?,?,?)', rows)
        connection.commit(); connection.close()

    def sync(self, apply=True):
        return flag_sync.sync(learner_db=self.learner_db, review_db=self.review_db, catalog=self.catalog,
                              apply=apply, report_path=self.report_path)

    def test_flag_creates_one_deferral_and_no_owner_review_time(self):
        self.flags([('flag-1', 'birder-1', 'fixture-asset', 'release-1', 'session-1', 'Looks wrong', None, '2026-11-15T00:00:00Z')])
        report = self.sync()
        self.assertEqual(report['new_deferred_for_triage'], 1)
        self.assertEqual(report['owner_review_seconds_after'], 0)
        self.assertTrue(report['audit_valid'])
        store = Store(self.review_db)
        try:
            self.assertEqual(store.state('fixture-asset')['status'], 'defer')
            self.assertEqual(store.connection.execute('SELECT count(*) FROM events').fetchone()[0], 1)
            self.assertEqual(len(store.intake_flags()), 1)
            self.assertEqual(store.export(self.root / 'approved.json')['approved_assets'], 0)
        finally:
            store.close()

    def test_rerun_is_idempotent_and_duplicate_reports_do_not_append_events(self):
        self.flags([('flag-1', 'birder-1', 'fixture-asset', 'release-1', 'session-1', 'Looks wrong', None, '2026-11-15T00:00:00Z')])
        self.sync(); report = self.sync()
        self.assertEqual(report['already_reconciled'], 1)
        store = Store(self.review_db)
        try:
            self.assertEqual(store.connection.execute('SELECT count(*) FROM events').fetchone()[0], 1)
        finally:
            store.close()
        self.flags([('flag-2', 'birder-2', 'fixture-asset', 'release-1', None, 'Also odd', None, '2026-11-15T00:01:00Z')])
        report = self.sync()
        self.assertEqual(report['duplicate_reports'], 1)
        store = Store(self.review_db)
        try:
            self.assertEqual(store.connection.execute('SELECT count(*) FROM events').fetchone()[0], 1)
            self.assertEqual(len(store.intake_flags()), 2)
        finally:
            store.close()

    def test_unmapped_flag_and_dry_run_are_reported_without_events(self):
        self.flags([('flag-x', 'birder-1', 'missing-asset', 'release-1', None, 'Unknown', None, '2026-11-15T00:00:00Z')])
        dry = self.sync(apply=False)
        self.assertEqual(dry['unmapped_assets'], 1)
        store = Store(self.review_db)
        try:
            self.assertEqual(store.connection.execute('SELECT count(*) FROM events').fetchone()[0], 0)
            self.assertEqual(len(store.intake_flags()), 0)
        finally:
            store.close()
        applied = self.sync()
        self.assertEqual(applied['unmapped_assets'], 1)
        store = Store(self.review_db)
        try:
            self.assertEqual(len(store.intake_flags()), 1)
            self.assertEqual(store.intake_flags()[0]['status'], 'unmapped_asset')
        finally:
            store.close()


if __name__ == '__main__':
    unittest.main()
