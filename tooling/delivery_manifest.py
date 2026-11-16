"""Compact rights-compliant delivery manifest for an eventual private R2 bucket.

The manifest contains object metadata only; media bytes remain in ignored private
storage. Every object retains its source license, attribution and derivative
notice. It is not a public redistribution grant.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import mimetypes
from pathlib import Path

from tooling.discover import PRIVATE, ROOT, save

RELEASE = PRIVATE / 'local-mvp/release.json'
OUTPUT = ROOT / 'experiments/phase-two-delivery-manifest.json'
R2_RATE_PER_GB_MONTH = 0.015
FREE_GB = 10.0


def _suffix(asset):
    path = Path(asset.get('local_path', ''))
    suffix = path.suffix.lower()
    return suffix or {'photo': '.jpg', 'audio': '.mp3'}[asset['kind']]


def build(release_path=RELEASE, output=OUTPUT):
    release = json.loads(Path(release_path).read_text())
    if release.get('schema') not in {'birdahead-local-release-v2'}:
        raise ValueError('Unsupported release for delivery manifest')
    objects = []
    total = 0
    restrictions = Counter()
    for asset in release['assets']:
        if not asset.get('permitted_delivery') or not asset.get('license_url') or not asset.get('creator'):
            raise ValueError('Delivery asset lacks delivery permission, license or creator')
        local = (ROOT / asset['local_path']).resolve()
        if not local.is_relative_to(PRIVATE.resolve()) or not local.is_file():
            raise ValueError('Delivery asset path invalid')
        raw = local.read_bytes()
        if hashlib.sha256(raw).hexdigest() != asset['sha256']:
            raise ValueError('Delivery media checksum changed')
        suffix = _suffix(asset)
        key = f"media/{asset['id']}{suffix}"
        content_type = mimetypes.guess_type(key)[0] or ('image/jpeg' if asset['kind'] == 'photo' else 'audio/mpeg')
        derivative = isinstance(asset.get('derivative_of'), dict)
        restrictions[(asset.get('license_code') or 'unknown', asset.get('source') or 'unknown', derivative)] += 1
        objects.append({
            'asset_id': asset['id'], 'key': key, 'content_type': content_type, 'bytes': len(raw), 'sha256': asset['sha256'],
            'kind': asset['kind'], 'species_code': asset['species_code'], 'creator': asset['creator'],
            'license_code': asset.get('license_code'), 'license_url': asset.get('license_url'),
            'attribution': asset.get('attribution'), 'source': asset.get('source'),
            'source_url': asset.get('source_url'), 'permitted_delivery': True,
            'share_alike': bool(asset.get('share_alike')), 'commercial_compatible': bool(asset.get('commercial_compatible')),
            'derivative': derivative, 'derivative_recipe': asset.get('derivative_recipe'),
            'presentation_modification_notice': asset.get('presentation_modification_notice')})
        total += len(raw)
    objects.sort(key=lambda row: row['key'])
    gib = total / (1024 ** 3)
    projected = max(0.0, gib - FREE_GB) * R2_RATE_PER_GB_MONTH
    source_notes = {
        'inaturalist': 'Photo license is separate from the observation license; retain creator, exact license and attribution. Exact coordinates are excluded from delivery metadata.',
        'xeno_canto': 'Recording license is per recording; retain recordist, recording ID, license and attribution. No Cornell-restricted media is included.',
        'cc-by': 'Attribution required; derivative and commercial use permitted by the source license.',
        'cc-by-sa': 'Attribution required; adaptations must carry the same share-alike license.',
        'cc-by-nc': 'Private household noncommercial use only; attribution required. Do not present as commercial or redistribute outside the household.',
        'cc-by-nc-sa': 'Private household noncommercial use only; attribution and share-alike required for adaptations.',
    }
    report = {
        'schema': 'birdahead-delivery-media-manifest-v1', 'scope': 'Private household, noncommercial, authenticated delivery only; not a public redistribution grant.',
        'release_id': release['id'], 'compatibility_key': release.get('compatibility_key'), 'object_count': len(objects),
        'total_bytes': total, 'total_gb': round(gib, 6), 'objects': objects,
        'projected_r2': {'total_gb': round(gib, 6), 'free_tier_gb': FREE_GB,
                         'billable_gb': round(max(0.0, gib - FREE_GB), 6), 'rate_usd_per_gb_month': R2_RATE_PER_GB_MONTH,
                         'projected_usd_per_month': round(projected, 6),
                         'note': 'Object storage only; class A/B operations and egress depend on actual use. Free-tier assumptions are account-wide.'},
        'restrictions': {f'license:{license}|source:{source}|derivative:{str(derivative).lower()}': count
                         for (license, source, derivative), count in sorted(restrictions.items())},
        'source_notes': source_notes,
        'limitations': ['Do not publish this bucket publicly unless every object license permits the intended use.',
                        'NC/SA assets constrain commercial use and derivative licensing; attribution must accompany delivery.',
                        'This manifest does not imply rights to source data, model weights or exact locations.']}
    save(output, report)
    print(json.dumps({key: report[key] for key in ['object_count', 'total_bytes', 'total_gb', 'projected_r2', 'restrictions']}, indent=2))
    return report


if __name__ == '__main__':
    build()
