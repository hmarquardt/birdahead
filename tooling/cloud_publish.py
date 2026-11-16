"""Publish the private accepted collection to the authenticated BirdAhead Worker.

Media travels only to the Worker's private R2 binding; no R2 credentials or public
URLs are used. A local ledger makes interrupted publishes resumable. Activation is
a separate D1 pointer update in the Worker, so rollback never rewrites media.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from tooling.discover import PRIVATE, ROOT, save

RELEASE = PRIVATE / 'local-mvp/release.json'
DELIVERY = ROOT / 'experiments/phase-two-delivery-manifest.json'
LEDGER = PRIVATE / 'production/publish-ledger.json'
PUBLIC_REPORT = ROOT / 'experiments/phase-three-publish.json'


def _read_env(path):
    values = {}
    path = Path(path)
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:]
        if '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def publish_token(local=False):
    if local:
        values = _read_env(ROOT / '.dev.vars')
        if values.get('PUBLISH_TOKEN'):
            return values['PUBLISH_TOKEN']
    for key in ['BIRDAHEAD_PUBLISH_TOKEN', 'PUBLISH_TOKEN']:
        if os.environ.get(key):
            return os.environ[key]
    values = _read_env(Path.home() / '.config/secrets/birdahead.env')
    return values.get('BIRDAHEAD_PUBLISH_TOKEN') or values.get('PUBLISH_TOKEN')


def cloud_catalog(release, delivery):
    by_asset = {row['asset_id']: row for row in delivery['objects']}
    assets = []
    for asset in release['assets']:
        row = by_asset.get(asset['id'])
        if not row:
            raise ValueError(f"Accepted asset missing from delivery manifest: {asset['id']}")
        clean = {key: value for key, value in asset.items() if key != 'local_path'}
        clean['r2_key'] = row['key']
        clean['content_type'] = row['content_type']
        clean['bytes'] = row['bytes']
        for key in ('public_delivery', 'public_use_basis', 'public_noncommercial_only', 'public_share_alike', 'public_license_notice'):
            clean[key] = row.get(key)
        assets.append(clean)
    return {
        'schema': 'birdahead-cloud-catalog-v1', 'release_id': release['id'],
        'compatibility_key': release.get('compatibility_key'), 'species': release['species'],
        'counties': release['counties'], 'profiles': release['profiles'], 'assets': assets,
        'coverage': release.get('coverage'), 'coverage_summary': release.get('coverage_summary'),
        'data_vintage': release.get('data_vintage'), 'universe': release.get('universe'),
        'confusion_pairs': release.get('confusion_pairs', []), 'limitations': release.get('limitations', []),
        'state_support': release.get('state_support'),
        'delivery_scope': 'public noncommercial educational delivery plus authenticated household delivery; raw source data remains private',
        'public_data_terms': {
            'ebird_attribution': 'eBird. 2016-2025. eBird observation data; derived seasonal summaries. Cornell Lab of Ornithology, Ithaca, New York. https://ebird.org.',
            'ebird_terms_url': 'https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/',
            'ebird_notice': 'Derived seasonal summaries only; original histogram exports are not publicly redistributed. Noncommercial educational use; eBird Data Access Terms apply.',
            'policy': 'Public delivery is noncommercial only, with per-asset creator, source and license attribution.',
        },
    }


def request(origin, token, method, path, body=None, headers=None, timeout=90):
    url = origin.rstrip('/') + path
    merged = {'X-Publish-Token': token, 'X-BirdAhead-Publish': '1', 'User-Agent': 'BirdAhead-Publisher/1.0', **(headers or {})}
    req = urllib.request.Request(url, data=body, method=method, headers=merged)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_000_001)
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read(10000)
        raise RuntimeError(f'Publish endpoint HTTP {exc.code}: {raw.decode("utf-8", "replace")[:300]}') from None


def upload_object(origin, token, key, path, sha, content_type):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('Local media checksum changed')
    status, result = request(origin, token, 'PUT', '/api/admin/object?key=' + urllib.parse.quote(key, safe=''),
                             raw, {'Content-Type': content_type, 'X-Content-SHA256': sha, 'Content-Length': str(len(raw))})
    if status != 200 or result.get('sha256') != sha:
        raise RuntimeError('Upload verification failed')
    return result


def load_ledger(path=None):
    path = Path(path or LEDGER)
    return json.loads(path.read_text()) if path.exists() else {'objects': {}, 'catalogs': {}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', default='https://birdahead.com')
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--catalog-only', action='store_true')
    parser.add_argument('--verify', action='store_true', help='Verify all ledger objects against remote metadata')
    parser.add_argument('--rollback-id', default=None)
    parser.add_argument('--no-activate', action='store_true')
    parser.add_argument('--concurrency', type=int, default=2)
    parser.add_argument('--resolve-ip', default=None, help='Local DNS workaround for the apex host')
    parser.add_argument('--geography-package', type=Path, help='Reviewed eligible compact geographic package; uploaded through private Worker binding')
    args = parser.parse_args()
    origin = 'http://127.0.0.1:8788' if args.local else args.origin
    if args.resolve_ip:
        import socket
        host = urllib.parse.urlsplit(origin).hostname
        original = socket.getaddrinfo
        def resolved(name, port, *rest, **kwargs):
            return original(args.resolve_ip if name == host else name, port, *rest, **kwargs)
        socket.getaddrinfo = resolved
    token = publish_token(args.local)
    if not token:
        raise SystemExit('No publish token available in the private credential file')
    if args.rollback_id:
        if args.dry_run:
            print(json.dumps({'rollback': args.rollback_id, 'origin': origin, 'dry_run': True}, indent=2)); return
        print(json.dumps(request(origin, token, 'POST', '/api/admin/rollback', json.dumps({'id': args.rollback_id}).encode(), {'Content-Type':'application/json'}), indent=2)); return
    release = json.loads(Path(RELEASE).read_text())
    delivery = json.loads(Path(DELIVERY).read_text())
    catalog = cloud_catalog(release, delivery)
    geography = None
    if args.geography_package:
        from tooling.geographic_release import load_package
        geography = load_package(args.geography_package)
        catalog['geography'] = geography
        # Preserve learner compatibility, but never rewrite a previous release catalog.
        release = {**release, 'id': hashlib.sha256(json.dumps({'base': release['id'], 'geography': geography}, sort_keys=True).encode()).hexdigest()}
        catalog['release_id'] = release['id']
    catalog_raw = json.dumps(catalog, sort_keys=True, separators=(',', ':')).encode()
    catalog_key = f"releases/{release['id']}/catalog.json"
    catalog_sha = hashlib.sha256(catalog_raw).hexdigest()
    ledger_path = (PRIVATE / 'production/publish-ledger-local.json') if args.local else LEDGER
    ledger = load_ledger(ledger_path)
    print(json.dumps({'release_id': release['id'], 'objects': len(delivery['objects']), 'bytes': delivery['total_bytes'],
                      'catalog_key': catalog_key, 'origin': origin, 'dry_run': args.dry_run}, indent=2))
    if args.dry_run:
        return
    if not args.catalog_only:
        pending = []
        for row in delivery['objects']:
            prior = ledger['objects'].get(row['key'])
            if prior and prior.get('sha256') == row['sha256'] and prior.get('bytes') == row['bytes']:
                continue
            pending.append(row)
        if args.verify:
            for row in delivery['objects']:
                _, result = request(origin, token, 'GET', '/api/admin/object?key=' + urllib.parse.quote(row['key'], safe=''))
                if result.get('exists') and result.get('sha256') == row['sha256']:
                    ledger['objects'][row['key']] = {'sha256': row['sha256'], 'bytes': row['bytes'], 'verified_at': datetime.now(timezone.utc).isoformat()}
                else:
                    ledger['objects'].pop(row['key'], None)
            pending = [row for row in delivery['objects'] if row['key'] not in ledger['objects']]
        completed = 0
        if pending:
            local_by_key = {row['key']: (ROOT / next(asset for asset in release['assets'] if asset['id'] == row['asset_id'])['local_path'])
                            for row in delivery['objects']}
            with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
                futures = {pool.submit(upload_object, origin, token, row['key'], local_by_key[row['key']], row['sha256'], row['content_type']): row for row in pending}
                for future in as_completed(futures):
                    row = futures[future]
                    try:
                        future.result()
                    except Exception as exc:
                        raise SystemExit(f"Upload failed for {row['key']}: {exc}") from None
                    ledger['objects'][row['key']] = {'sha256': row['sha256'], 'bytes': row['bytes'], 'verified_at': datetime.now(timezone.utc).isoformat()}
                    completed += 1
                    save(ledger_path, ledger)
                    if completed % 25 == 0:
                        print(json.dumps({'uploaded': completed, 'pending': len(pending)}), flush=True)
        print(json.dumps({'uploaded_or_skipped': len(delivery['objects']), 'changed_uploaded': completed}, indent=2))
    # Upload the versioned catalog and activate only after every object is verified.
    if geography:
        for row in geography['regions']:
            upload_object(origin, token, row['key'], args.geography_package / (row['id'] + '.json'), row['sha256'], 'application/json')
    status, result = request(origin, token, 'PUT', '/api/admin/object?key=' + urllib.parse.quote(catalog_key, safe=''),
                             catalog_raw, {'Content-Type': 'application/json', 'X-Content-SHA256': catalog_sha, 'Content-Length': str(len(catalog_raw))})
    ledger['catalogs'][catalog_key] = {'sha256': catalog_sha, 'bytes': len(catalog_raw), 'verified_at': datetime.now(timezone.utc).isoformat()}
    save(ledger_path, ledger)
    activation = None
    if not args.no_activate:
        _, activation = request(origin, token, 'POST', '/api/admin/release', json.dumps({'id': release['id'], 'object_key': catalog_key, 'compatibility_key': release.get('compatibility_key') or release['id'], 'activate': True}).encode(), {'Content-Type': 'application/json'})
    summary = {'schema': 'birdahead-publish-report-v1', 'at': datetime.now(timezone.utc).isoformat(), 'origin': origin,
               'release_id': release['id'], 'catalog_key': catalog_key, 'objects': len(delivery['objects']),
               'bytes': delivery['total_bytes'], 'activated': bool(activation and activation.get('active')),
               'scope': 'Public noncommercial educational delivery; authenticated household progress and private administration'}
    save((PRIVATE / 'production/publish-report-local.json') if args.local else PUBLIC_REPORT, summary)
    print(json.dumps({'catalog': result, 'activation': activation, 'report': summary}, indent=2))


if __name__ == '__main__':
    main()
