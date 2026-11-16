"""Public aggregate Phase Two coverage, acceptance and seasonal deck evidence."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path

from tooling.acquire import CATALOG, WORK
from tooling.discover import PRIVATE, ROOT, save
from tooling.histograms import UNIVERSE
from tooling.seasonal import COUNTIES, rank

ANCHORS = {'winter': '2026-01-15', 'spring_migration': '2026-05-05', 'summer': '2026-07-15',
           'fall_migration': '2026-09-10', 'now': '2026-11-15'}
ACCEPTED = {'automatically_accepted', 'human_approved', 'expert_verified'}


def _load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def _accepted(asset):
    return asset.get('automated_decision', {}).get('status') in ACCEPTED


def _counts(assets):
    rows = defaultdict(lambda: {'photos': 0, 'audio': 0, 'photos_accepted': 0, 'audio_accepted': 0})
    for asset in assets:
        bucket = 'photos' if asset.get('kind') == 'photo' else 'audio' if asset.get('kind') == 'audio' else None
        if not bucket:
            continue
        rows[asset['species_code']][bucket] += 1
        if _accepted(asset):
            rows[asset['species_code']][bucket + '_accepted'] += 1
    return rows


def _deck(ranking, counts, limit=25):
    selected = [row for row in ranking if (row.get('current_reporting_frequency') or 0) > 0][:limit]
    photo_ready = [row['species_code'] for row in selected if counts[row['species_code']]['photos_accepted'] >= 2]
    audio_ready = [row['species_code'] for row in selected if counts[row['species_code']]['audio_accepted'] >= 2]
    target = [row['species_code'] for row in selected if counts[row['species_code']]['photos_accepted'] >= 5
              and counts[row['species_code']]['audio_accepted'] >= 3]
    gaps = [row['species_code'] for row in selected if row['species_code'] not in photo_ready]
    return {'deck_size': len(selected), 'photo_practice_ready': len(photo_ready),
            'audio_practice_ready': len(audio_ready), 'photo_and_audio_target': len(target),
            'photo_gaps': gaps[:10], 'photo_ready_codes': photo_ready, 'audio_ready_codes': audio_ready}


def main():
    catalog = _load(CATALOG, [])
    universe = _load(UNIVERSE, {'species': []})['species']
    baseline = _load(ROOT / 'experiments/phase-one-media-baseline.json', {})
    results = _load(ROOT / 'experiments/phase05-results.json', {})
    expansion = _load(ROOT / 'experiments/phase-two-acquisition.json', {})
    state = _load(WORK / 'expansion/state.json', {})
    counts = _counts(catalog)
    names = {row['ebird_species_code']: row['common_name'] for row in universe}
    per_species = []
    for row in universe:
        code = row['ebird_species_code']
        current = counts[code]
        per_species.append({'priority_rank': row['priority_rank'], 'code': code, 'name': row['common_name'], 'pilot': row['pilot'],
            'photo_candidates': current['photos'], 'photo_accepted': current['photos_accepted'],
            'audio_candidates': current['audio'], 'audio_accepted': current['audio_accepted'],
            'photo_target_met': current['photos_accepted'] >= 5, 'audio_target_met': current['audio_accepted'] >= 3,
            'photo_practice_ready': current['photos_accepted'] >= 2, 'audio_practice_ready': current['audio_accepted'] >= 2,
            'gap': current['photos_accepted'] < 2 and current['audio_accepted'] < 2})
    tiers = Counter('target' if row['photo_target_met'] and row['audio_target_met'] else
                    'photo_only_target' if row['photo_target_met'] else
                    'practice_partial' if row['photo_practice_ready'] or row['audio_practice_ready'] else 'gap'
                    for row in per_species)
    reasons = Counter()
    for asset in catalog:
        for reason in asset.get('automated_decision', {}).get('reasons', []):
            reasons[reason] += 1
    photos = [a for a in catalog if a.get('kind') == 'photo']
    audio = [a for a in catalog if a.get('kind') == 'audio']
    accepted_photos = [a for a in photos if _accepted(a)]
    accepted_audio = [a for a in audio if _accepted(a)]
    accepted = accepted_photos + accepted_audio
    profile = _load(PRIVATE / 'occurrence/profiles/US-IN-051.json', {})
    decks = {label: _deck(rank(profile, date.fromisoformat(day)), counts) for label, day in ANCHORS.items()}
    arrivals = sorted(rank(profile, date.fromisoformat(ANCHORS['now'])),
                      key=lambda row: -(row.get('approaching_window_rise') or 0))
    arrival_deck = _deck([row for row in arrivals if (row.get('approaching_window_rise') or 0) > 0], counts)
    photos_by_contributor = Counter(a.get('contributor_id') for a in accepted_photos)
    audio_by_contributor = Counter(a.get('contributor_id') for a in accepted_audio)
    derivatives = [a for a in accepted_audio if isinstance(a.get('derivative_of'), dict)]
    before_accepted = baseline.get('automatically_accepted', 0)
    after_accepted = len(accepted)
    summary = {
        'schema': 'birdahead-phase-two-media-report-v1',
        'scope': 'Recreational noncommercial local collection; automatically accepted evidence is preliminary source/model corroboration, not biological certification.',
        'before': {'automatically_accepted': before_accepted, 'accepted_by_modality': baseline.get('accepted_by_modality', {}),
                   'photo_practice_species': baseline.get('accepted_species_photo_practice_ready', 0),
                   'audio_practice_species': baseline.get('accepted_species_audio_practice_ready', 0),
                   'photo_target_species': baseline.get('accepted_species_photo_target', 0),
                   'audio_target_species': baseline.get('accepted_species_audio_target', 0)},
        'after': {'automatically_accepted': after_accepted, 'accepted_by_modality': {'photo': len(accepted_photos), 'audio': len(accepted_audio)},
                  'photo_practice_species': sum(row['photo_practice_ready'] for row in per_species),
                  'audio_practice_species': sum(row['audio_practice_ready'] for row in per_species),
                  'photo_target_species': sum(row['photo_target_met'] for row in per_species),
                  'audio_target_species': sum(row['audio_target_met'] for row in per_species),
                  'species_with_any_accepted_photo': sum(row['photo_accepted'] > 0 for row in per_species),
                  'species_with_any_accepted_audio': sum(row['audio_accepted'] > 0 for row in per_species)},
        'acceptance': {'photo_candidates': len(photos), 'photo_accepted': len(accepted_photos),
                       'photo_rate': round(len(accepted_photos) / len(photos), 4) if photos else None,
                       'audio_candidates': len(audio), 'audio_accepted': len(accepted_audio),
                       'audio_rate': round(len(accepted_audio) / len(audio), 4) if audio else None,
                       'audio_derivative_candidates': sum(isinstance(a.get('derivative_of'), dict) for a in audio),
                       'accepted_derivative_clips': len(derivatives),
                       'rejection_reasons': dict(reasons.most_common())},
        'coverage_tiers': dict(tiers), 'per_species': per_species,
        'contributors': {'accepted_photos': len(photos_by_contributor), 'accepted_audio': len(audio_by_contributor),
                         'max_photos_one_contributor': max(photos_by_contributor.values(), default=0),
                         'max_audio_one_contributor': max(audio_by_contributor.values(), default=0),
                         'photo_contributor_buckets': dict(Counter('1' if n == 1 else '2' if n == 2 else '3+' for n in photos_by_contributor.values())),
                         'audio_contributor_buckets': dict(Counter('1' if n == 1 else '2' if n == 2 else '3+' for n in audio_by_contributor.values()))},
        'seasonal_decks': {'reference_county': 'US-IN-051', 'county_name': COUNTIES['US-IN-051'],
                           'anchors': ANCHORS, 'decks': decks, 'arriving_soon_now': arrival_deck},
        'data_vintage': {**{key: profile.get('metadata', {}).get(key) for key in
                            ['start_year', 'end_year', 'source_taxonomy_version', 'bin_definition', 'units']},
                         'source_note': 'Owner-supplied 2016-2025 county exports; source taxonomy release unknown.'},
        'acquisition': {'new_assets': expansion.get('counters', {}).get('assets_added', 0),
                        'requests': expansion.get('counters', {}).get('requests', 0),
                        'downloads': expansion.get('counters', {}).get('downloads', 0),
                        'new_media_bytes': expansion.get('counters', {}).get('media_bytes', 0),
                        'elapsed_seconds': expansion.get('counters', {}).get('elapsed_seconds', 0),
                        'retries': expansion.get('counters', {}).get('retries', 0),
                        'checkpoint_complete': state.get('complete'),
                        'total_catalog_bytes': sum(a.get('bytes', 0) for a in catalog),
                        'photo_catalog_bytes': sum(a.get('bytes', 0) for a in photos),
                        'audio_catalog_bytes': sum(a.get('bytes', 0) for a in audio),
                        'budgets': state.get('budgets', {})},
        'review': {'owner_review_seconds_recorded': results.get('owner_review_seconds_recorded', 0),
                   'owner_total_review_limit_seconds': 7200, 'human_approved': 0, 'expert_verified': 0,
                   'sampled_audit_queue': results.get('sampled_audit_queue', 0),
                   'note': 'No owner/expert review is fabricated; automatic acceptance remains distinct.'},
        'limitations': [
            'Acceptance is preliminary automated source/model corroboration, not independently calibrated accuracy.',
            'The 100-species objective is not a guarantee: species with insufficient support stay gaps.',
            'Reporting frequency is historical checklist frequency, not encounter probability or abundance.',
            'Source taxonomy release is unknown; unresolved and split/lump-ambiguous names stay excluded.',
            'Contributor counts and media availability are measured at report time.'],
    }
    save(ROOT / 'experiments/phase-two-media.json', summary)
    print(json.dumps({key: summary[key] for key in ['before', 'after', 'coverage_tiers', 'acceptance', 'acquisition', 'contributors']}, indent=2))
    return summary


if __name__ == '__main__':
    main()
