"""Prepare a concise sampled owner-audit queue from automated acceptances."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from tooling.acquire import CATALOG, WORK
from tooling.discover import ROOT, save
from tooling.teaching_universe import PAIR_NAMES

ACCEPTED = {'automatically_accepted', 'human_approved', 'expert_verified'}
HIGH_RISK = {name for pair in PAIR_NAMES for name in pair}
OUTPUT = ROOT / 'experiments/phase-two-audit-queue.json'
PRIVATE_OUTPUT = WORK / 'audit-queue-private.json'


def build(catalog_path=CATALOG, output=OUTPUT, private_output=PRIVATE_OUTPUT):
    assets = json.loads(Path(catalog_path).read_text())
    queue = [asset for asset in assets if asset.get('audit_selected') and
             asset.get('automated_decision', {}).get('status') in ACCEPTED]
    public = []
    for asset in sorted(queue, key=lambda row: (row['kind'], row['species_code'], row['id'])):
        public.append({'asset_id': asset['id'], 'kind': asset['kind'], 'species_code': asset['species_code'],
                       'common_name': asset.get('common_name'), 'license_code': asset.get('license_code'),
                       'source': asset.get('source'), 'high_risk_pair': asset.get('common_name') in HIGH_RISK,
                       'derivative_clip': isinstance(asset.get('derivative_of'), dict),
                       'audit_reason': 'stratified 20% automated-acceptance sample'})
    counts = Counter((row['kind'], row['high_risk_pair']) for row in public)
    report = {'schema': 'birdahead-audit-queue-v1', 'queue_size': len(public),
              'by_kind_and_risk': {f'{kind}|high_risk={str(risk).lower()}': count for (kind, risk), count in sorted(counts.items())},
              'owner_review_limit_seconds': 7200, 'estimated_minutes_at_20s_photo_45s_audio':
              round(sum(20 if row['kind'] == 'photo' else 45 for row in public) / 60, 1),
              'queue': public,
              'note': 'Sampled audit, not per-asset approval. A report is not proof of a biological error; the workbench records timed decisions.'}
    save(output, report)
    private = [{**asset, 'audit_reason': 'stratified 20% automated-acceptance sample'} for asset in queue]
    save(private_output, private)
    print(json.dumps({key: report[key] for key in ['queue_size', 'by_kind_and_risk', 'estimated_minutes_at_20s_photo_45s_audio']}, indent=2))
    return report


if __name__ == '__main__':
    build()
