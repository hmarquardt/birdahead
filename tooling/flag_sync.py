"""Reconcile learner identification flags into the local curation workbench.

Flags are reports, not proof. Each new asset report appends one deferral event
for triage, preserves the learner/session/release context, and never consumes
the timed owner-review budget. Re-running is idempotent by flag id.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sqlite3

from tooling.acquire import CATALOG
from tooling.discover import PRIVATE, ROOT, now, save
from tooling.review_store import Store, WORK

ACCEPTED = {'automatically_accepted', 'human_approved', 'expert_verified'}


def read_flags(path):
    path = Path(path)
    if not path.exists():
        return []
    connection = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute('SELECT * FROM flags ORDER BY at')]
    finally:
        connection.close()


def sync(*, learner_db=PRIVATE / 'local-mvp/learning.sqlite', review_db=WORK / 'reviews.sqlite',
         catalog=CATALOG, apply=False, report_path=ROOT / 'experiments/flag-reconciliation.json'):
    flags = read_flags(learner_db)
    store = Store(review_db)
    try:
        if Path(catalog).exists():
            store.sync(json.loads(Path(catalog).read_text()))
        existing = {row['flag_id']: row for row in store.intake_flags()}
        background = store.used_seconds()
        accepted_events = {row['flag_id']: row for row in existing.values() if row.get('event_hash')}
        actions = []; affected_assets = set(); species = Counter()
        for flag in flags:
            flag_id, asset_id = flag['id'], flag['asset_id']
            detail = {'release_id': flag.get('release_id'), 'session_id': flag.get('session_id'),
                      'suggested_species': flag.get('suggested_species'), 'flag_at': flag.get('at')}
            if flag_id in existing:
                actions.append({'flag_id': flag_id, 'asset_id': asset_id, 'status': 'already_reconciled'});continue
            try:
                before = store.state(asset_id)
            except ValueError:
                actions.append({'flag_id': flag_id, 'asset_id': asset_id, 'status': 'unmapped_asset'})
                if apply: store.intake(flag_id, asset_id, flag.get('profile_id'), 'unmapped_asset', detail=detail)
                continue
            prior = next((row for row in accepted_events.values() if row['asset_id'] == asset_id), None)
            status = 'deferred_for_triage'; event_hash = prior.get('event_hash') if prior else None
            if prior:
                status = 'duplicate_report'
            elif apply:
                event_hash = store.record_report(asset_id, f"learner:{flag.get('profile_id')}", flag.get('reason', ''),
                                                 {'source': 'local learner flag', 'release_id': flag.get('release_id'),
                                                  'session_id': flag.get('session_id'), 'suggested_species': flag.get('suggested_species')})
            actions.append({'flag_id': flag_id, 'asset_id': asset_id, 'status': status,
                            'asset_was_accepted': before.get('status') in ACCEPTED})
            if apply:
                store.intake(flag_id, asset_id, flag.get('profile_id'), status, event_hash, detail)
                if not prior: accepted_events[flag_id] = {'flag_id': flag_id, 'asset_id': asset_id, 'event_hash': event_hash}
            affected_assets.add(asset_id)
            asset = next((a for a in store.assets() if a['id'] == asset_id), None)
            if asset: species[asset.get('species_code')] += 1
        after = store.used_seconds()
        actions_counts = Counter(action['status'] for action in actions)
        report = {
            'schema': 'birdahead-flag-reconciliation-v1', 'at': now(),
            'mode': 'apply' if apply else 'dry_run', 'learner_flags': len(flags),
            'already_reconciled': actions_counts.get('already_reconciled', 0),
            'new_deferred_for_triage': actions_counts.get('deferred_for_triage', 0),
            'duplicate_reports': actions_counts.get('duplicate_report', 0),
            'unmapped_assets': actions_counts.get('unmapped_asset', 0),
            'unique_assets_affected': len(affected_assets),
            'assets_previously_accepted': sum(1 for action in actions if action.get('asset_was_accepted')),
            'owner_review_seconds_before': round(background, 3), 'owner_review_seconds_after': round(after, 3),
            'owner_review_budget_consumed': round(max(0, after - background), 3),
            'affected_species_counts': dict(species),
            'audit_valid': store.verify(),
            'actions': actions,
            'note': 'A learner report is evidence for triage, not biological proof. Rights/biology acceptance history is retained.'}
        save(report_path, report)
        return report
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--learner-db', type=Path, default=PRIVATE / 'local-mvp/learning.sqlite')
    parser.add_argument('--review-db', type=Path, default=WORK / 'reviews.sqlite')
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--report', type=Path, default=ROOT / 'experiments/flag-reconciliation.json')
    parser.add_argument('--apply', action='store_true', help='Write deferral events; otherwise dry-run')
    args = parser.parse_args()
    report = sync(learner_db=args.learner_db, review_db=args.review_db, catalog=args.catalog,
                  apply=args.apply, report_path=args.report)
    print(json.dumps({key: report[key] for key in ['mode', 'learner_flags', 'new_deferred_for_triage',
        'duplicate_reports', 'unmapped_assets', 'unique_assets_affected', 'owner_review_seconds_after']}, indent=2))


if __name__ == '__main__':
    main()
