"""Resume the teaching universe in successive bounded batches with a disk check.

Run after setting an explicit incremental media budget. The existing checkpoint,
request/retry counters and catalog are reused; no owner action is needed between
batches. Stop when the universe is processed or a bounded resource limit is hit.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from tooling.discover import PRIVATE
from tooling.expansion import STATE, CATALOG, _load, run, universe_species


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-species', type=int, default=8)
    parser.add_argument('--batch-assets', type=int, default=100)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--requests', type=int, default=900)
    parser.add_argument('--new-media-bytes', type=int, default=5_000_000_000)
    parser.add_argument('--reserve-bytes', type=int, default=1_000_000_000)
    args = parser.parse_args()
    free = shutil.disk_usage(PRIVATE).free
    if free < args.new_media_bytes + args.reserve_bytes:
        raise SystemExit(f'Insufficient disk: {free} bytes free; need {args.new_media_bytes + args.reserve_bytes}')
    state = _load(STATE)
    if not state:
        raise SystemExit('No checkpoint; run tooling.expansion plan first')
    baseline = int(state.get('media_bytes_baseline', state['counters']['media_bytes']))
    state['media_bytes_baseline'] = baseline
    state['budgets'].update({'requests': args.requests, 'media_bytes': args.new_media_bytes, 'max_assets': 10**9})
    from tooling.expansion import save
    save(STATE, state)
    batches = 0
    while True:
        before = json.loads(STATE.read_text())['cursor']
        run(max_species=args.batch_species, max_assets=args.batch_assets, budgets=state['budgets'],
            download_workers=args.workers, media_baseline=baseline)
        batches += 1
        latest = json.loads(STATE.read_text())
        print(json.dumps({'batch': batches, 'cursor': latest['cursor'], 'complete': latest['complete'],
                          'assets': latest['counters']['assets_added'],
                          'incremental_media_bytes': latest['counters']['media_bytes'] - baseline}, indent=2), flush=True)
        if latest['complete'] or latest['cursor'] == before:
            break


if __name__ == '__main__':
    main()
