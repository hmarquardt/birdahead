"""Compile a deterministic private learner release from accepted media and profiles."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from tooling.discover import PRIVATE, ROOT, save
from tooling.histograms import UNIVERSE
from tooling.review_store import Store, canonical
from tooling.seasonal import COUNTIES

ACCEPTED = {'automatically_accepted', 'human_approved', 'expert_verified'}
TARGETS = {'photos': 5, 'audio': 3}


def compatibility_key(universe, profiles):
    scope = {'family': 'birdahead-local-release-v2',
             'taxonomy': universe['taxonomy'],
             'source_scope': {key: universe['source_scope'][key] for key in ['start_year', 'end_year', 'counties']}}
    return hashlib.sha256(canonical(scope).encode()).hexdigest()


def coverage(species, assets):
    rows = {row['ebird_species_code']: {'photos': 0, 'audio': 0} for row in species}
    for asset in assets:
        if asset['species_code'] not in rows:
            raise ValueError('Accepted asset references a species outside the release universe')
        if asset['kind'] in {'photo', 'audio'}:
            rows[asset['species_code']][{'photo': 'photos', 'audio': 'audio'}[asset['kind']]] += 1
    output = {}
    for code, counts in rows.items():
        output[code] = {'photos': counts['photos'], 'audio': counts['audio'],
                        'photo_practice_ready': counts['photos'] >= 2, 'audio_practice_ready': counts['audio'] >= 2,
                        'photo_target_met': counts['photos'] >= TARGETS['photos'],
                        'audio_target_met': counts['audio'] >= TARGETS['audio']}
    return output


def validate(payload):
    species = payload['species']
    codes = [row['ebird_species_code'] for row in species]
    if len(codes) != len(set(codes)):
        raise ValueError('Duplicate species code in release')
    if len(species) < 25 or not all(any(row['ebird_species_code'] == pilot['ebird_species_code'] for row in species)
                                    for pilot in json.loads((ROOT / 'experiments/poc-species.json').read_text())):
        raise ValueError('Release must retain the versioned pilot species')
    profiles = payload['profiles']
    if set(profiles) != set(COUNTIES):
        raise ValueError('Release profiles must cover exactly the seven counties')
    for location, profile in profiles.items():
        counts = {code: 0 for code in codes}
        for row in profile['rows']:
            if row['species_code'] not in counts:
                raise ValueError('Profile row outside release species')
            counts[row['species_code']] += 1
        if any(count != 48 for count in counts.values()):
            raise ValueError(f'Incomplete 48-bin coverage in {location}')
    ids = set()
    for asset in payload['assets']:
        if asset['id'] in ids:
            raise ValueError('Duplicate media asset id')
        ids.add(asset['id'])
        if asset['species_code'] not in codes:
            raise ValueError('Media asset outside release species')
        if asset.get('automated_decision', {}).get('status') not in ACCEPTED:
            raise ValueError('Release contains a non-accepted media asset')
        local = (ROOT / asset['local_path']).resolve()
        if not local.is_relative_to(PRIVATE.resolve()) or not local.is_file():
            raise ValueError('Release media path is outside private storage or missing')
        if hashlib.sha256(local.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Release media checksum changed')
    return True


def build():
    destination = PRIVATE / 'local-mvp'; destination.mkdir(parents=True, exist_ok=True)
    store = Store()
    try:
        store.export(destination / 'approved-media.json')
    finally:
        store.close()
    approved = json.loads((destination / 'approved-media.json').read_text())
    universe = json.loads(UNIVERSE.read_text())
    if universe.get('schema') != 'birdahead-teaching-universe-v1':
        raise ValueError('Unsupported teaching universe')
    species = universe['species']
    profiles = {code: json.loads((PRIVATE / 'occurrence/profiles' / f'{code}.json').read_text()) for code in COUNTIES}
    scopes = {(p['metadata']['start_year'], p['metadata']['end_year'], p['metadata']['taxonomy_version'], p['metadata']['units'])
              for p in profiles.values()}
    if len(scopes) != 1:
        raise ValueError('Inconsistent profile scope in release')
    keys = ['id', 'species_code', 'kind', 'local_path', 'sha256', 'creator', 'source_url', 'license_url',
            'license_code', 'license_version', 'attribution', 'source', 'source_record_id', 'source_url',
            'vocalization', 'sex', 'age', 'plumage', 'target_bbox_xyxy', 'original_dimensions',
            'automated_decision', 'review_state', 'permitted_modification', 'permitted_delivery', 'permitted_storage',
            'permitted_offline', 'permitted_scope', 'share_alike', 'presentation_modification_notice',
            'derivative_of', 'derivative_recipe', 'media_format', 'technical_metrics', 'commercial_compatible',
            'acquisition_pass', 'source_verified', 'machine_screened', 'human_approved', 'expert_verified',
            'biological_attribute_status']
    assets = [{key: asset.get(key) for key in keys if key in asset} for asset in approved['assets']]
    coverage_rows = coverage(species, assets)
    compact_species = [{key: row.get(key) for key in ['priority_rank', 'ebird_species_code', 'common_name', 'scientific_name',
                        'pilot', 'confusion_pair', 'coverage_target', 'selection_rationale', 'selection_score']}
                       for row in species]
    profile_meta = next(iter(profiles.values()))['metadata']
    payload = {
        'schema': 'birdahead-local-release-v2', 'scope': 'personal recreational noncommercial; local-only',
        'species': compact_species, 'counties': COUNTIES, 'profiles': profiles, 'assets': assets,
        'coverage': coverage_rows,
        'coverage_summary': {
            'species': len(species), 'assets': len(assets),
            'accepted_by_kind': {kind: sum(a['kind'] == kind for a in assets) for kind in ['photo', 'audio']},
            'species_photo_practice_ready': sum(row['photo_practice_ready'] for row in coverage_rows.values()),
            'species_audio_practice_ready': sum(row['audio_practice_ready'] for row in coverage_rows.values()),
            'species_photo_target_met': sum(row['photo_target_met'] for row in coverage_rows.values()),
            'species_audio_target_met': sum(row['audio_target_met'] for row in coverage_rows.values()),
            'gaps': sorted(code for code, row in coverage_rows.items() if not row['photo_practice_ready'] and not row['audio_practice_ready'])},
        'data_vintage': {'start_year': profile_meta['start_year'], 'end_year': profile_meta['end_year'],
                         'source_taxonomy_version': None, 'taxonomy_version': profile_meta['taxonomy_version'],
                         'bin_definition': profile_meta['bin_definition'], 'units': profile_meta['units'],
                         'source_note': 'Owner-supplied 2016-2025 county exports; source taxonomy release unknown.',
                         'imported_at': universe['generated_at'], 'reference_date': universe['reference_date'],
                         'missing_semantics': profile_meta['missing_semantics']},
        'universe': {key: universe[key] for key in ['schema', 'generated_at', 'reference_date', 'reference_county',
                    'selection_limit', 'taxonomy', 'source_scope', 'weights', 'seasonal_anchors', 'coverage_objective',
                    'confusion_pairs', 'candidate_counts', 'limitations']},
        'confusion_pairs': universe['confusion_pairs'],
        'state_support': {'sample_sizes_retained': True, 'frequency_meaning': 'historical complete-checklist reporting fraction',
                          'not_encounter_probability': True, 'unknown_stays_unknown': True},
        'limitations': ['Automated acceptance is preliminary source/model corroboration, not biological certification.',
                        'Historical reporting frequency is not encounter probability or abundance.',
                        'Missing media coverage is explicit; no weak examples are promoted to fill a species.',
                        'Source taxonomy release is unknown; unresolved/split-lump names remain excluded.'],
        'approved_manifest_sha256': hashlib.sha256((destination / 'approved-media.json').read_bytes()).hexdigest(),
    }
    payload['compatibility_key'] = compatibility_key(universe, profiles)
    payload['id'] = hashlib.sha256(canonical(payload).encode()).hexdigest()
    validate(payload)
    save(destination / 'release.json', payload)
    print(json.dumps({'release': payload['id'], 'compatibility_key': payload['compatibility_key'],
                      'species': len(species), 'assets': len(assets),
                      'coverage_summary': payload['coverage_summary'],
                      'private_output': 'experiments/private/local-mvp/release.json'}, indent=2))
    return payload


if __name__ == '__main__':
    build()
