"""Derive a prioritized regional teaching universe from the seven annual references.

The 100-species limit is a coverage objective, never authority to weaken media
rights or biological gates. Selection uses only derived aggregate frequencies;
original exports and unresolved source names stay in ignored private storage.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
import statistics
from pathlib import Path

from tooling.discover import Client, PRIVATE, ROOT, save
from tooling.histograms import BIN_DEFINITION, UNIVERSE, native_bin, parse_source
from tooling.seasonal import COUNTIES

SCHEMA = 'birdahead-teaching-universe-v1'
REFERENCE_COUNTY = 'US-IN-051'
DEFAULT_DATE = '2026-11-15'
TARGETS = {'photos': 5, 'audio': 3}
WEIGHTS = {'year_round': .35, 'current_season': .25, 'approaching_window': .20,
           'recreational_value': .12, 'media_availability': .08}
SEASON_ANCHORS = {'winter': '2026-01-15', 'spring_migration': '2026-05-05',
                  'summer': '2026-07-15', 'fall_migration': '2026-09-10'}
PAIR_NAMES = [("Cooper's Hawk", 'Sharp-shinned Hawk'), ('Downy Woodpecker', 'Hairy Woodpecker'),
              ('Turkey Vulture', 'Black Vulture'), ('Greater Yellowlegs', 'Lesser Yellowlegs')]


def _template(when):
    day = min(when.day, calendar.monthrange(2001, when.month)[1])
    return date(2001, when.month, day)


def _bins():
    return [(date.fromisoformat(native_bin(i // 4 + 1, i % 4 + 1)['start']),
             date.fromisoformat(native_bin(i // 4 + 1, i % 4 + 1)['end'])) for i in range(48)]


BINS = _bins()


def _at(values, when):
    if values is None:
        return None
    day = _template(when)
    for (start, end), value in zip(BINS, values):
        if start <= day < end:
            return value
    return None


def _sample_at(sizes, when):
    day = _template(when)
    for (start, end), value in zip(BINS, sizes):
        if start <= day < end:
            return value
    return None


def _mean(values):
    values = [value for value in values if value is not None]
    return statistics.fmean(values) if values else None


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _supported(values, sizes):
    """Drop zero-support and suspicious non-integral cells before ranking."""
    output = []
    for value, sample in zip(values, sizes):
        if value is None or not sample:
            output.append(None)
            continue
        numerator = value * sample
        tolerance = max(1e-6, 5e-7 * sample)
        output.append(value if abs(numerator - round(numerator)) <= tolerance else None)
    return output


def _normalize(values):
    supported = [value for value in values.values() if value is not None]
    if not supported:
        return {}
    low, high = min(supported), max(supported)
    if high == low:
        return {key: (0.0 if value is None else 0.5) for key, value in values.items()}
    return {key: (0.0 if value is None else (value - low) / (high - low)) for key, value in values.items()}


def media_counts(manifest):
    """Count currently exported accepted assets by species and modality."""
    counts = defaultdict(lambda: {'photos': 0, 'audio': 0})
    for asset in (manifest or {}).get('assets', []):
        kind = asset.get('kind')
        if kind not in {'photo', 'audio'}:
            continue
        counts[asset.get('species_code')][{'photo': 'photos', 'audio': 'audio'}[kind]] += 1
    return counts


def build_universe(sources, taxonomy_version, poc, media=None, *, reference_date=DEFAULT_DATE,
                   limit=100, reference_county=REFERENCE_COUNTY):
    """Pure selection over validated source exports. Deterministic for fixed inputs."""
    if len(sources) != len(COUNTIES):
        raise ValueError('Exactly seven validated county sources are required')
    locations = {source['location'] for source in sources}
    if locations != set(COUNTIES):
        raise ValueError('Teaching-universe source scope must match the seven counties')
    when = date.fromisoformat(reference_date)
    poc = {row['ebird_species_code']: row for row in poc}
    pair_codes = {}
    for left, right in PAIR_NAMES:
        if left in {row['common_name'] for row in poc.values()} and right in {row['common_name'] for row in poc.values()}:
            left_code = next(code for code, row in poc.items() if row['common_name'] == left)
            right_code = next(code for code, row in poc.items() if row['common_name'] == right)
            pair_codes[left_code] = right_code
            pair_codes[right_code] = left_code

    candidates = {}
    unresolved = {}
    for source in sources:
        location = source['location']
        unresolved[location] = sorted(set(source['data']) - set(source['matches']))
        for code, name in source['mapped'].items():
            taxon = source['matches'][name]
            row = candidates.setdefault(code, {
                'ebird_species_code': code,
                'common_name': taxon['comName'],
                'scientific_name': taxon['sciName'],
                'taxon_id': taxon.get('taxonID'),
                'county_values': {}, 'county_sizes': {}})
            if (row['common_name'], row['scientific_name']) != (taxon['comName'], taxon['sciName']):
                raise ValueError('Conflicting target-taxonomy concepts for one species code')
            row['county_values'][location] = _supported(source['data'][name], source['sizes'])
            row['county_sizes'][location] = source['sizes']

    media = media_counts(media)
    raw = {}
    for code, row in candidates.items():
        values = [value for county in row['county_values'].values() for value in county if value is not None]
        annual_mean = _mean(values)
        supported = len(values)
        year_round_share = (sum(value >= .05 for value in values) / supported) if supported else None
        county_current = {location: _at(county, when) for location, county in row['county_values'].items()}
        reference_values = row['county_values'].get(reference_county)
        current = _at(reference_values, when) if reference_values else None
        if current is None:
            current = _mean(list(county_current.values()))
        future = [_at(reference_values, when + timedelta(days=offset)) for offset in (14, 21, 28)] if reference_values else []
        future = [value for value in future if value is not None]
        peak = max(future) if future else None
        rise = max(0.0, peak - current) if peak is not None and current is not None else None
        sizes = row['county_sizes'].get(reference_county) or []
        sample = _sample_at(sizes, when) if sizes else None
        row['metrics'] = {
            'counties_present': len(row['county_values']),
            'annual_mean_frequency': annual_mean,
            'year_round_frequency_share': year_round_share,
            'current_reporting_frequency': current,
            'current_reference_county': reference_county,
            'current_by_county': county_current,
            'current_regional_mean': _mean(list(county_current.values())),
            'future_14_28_day_max': peak,
            'approaching_window_rise': rise,
            'current_sample_size': sample,
            'annual_checklist_samples_reference': sum(sizes) if sizes else None,
            'seasonal_anchors': {label: (_at(reference_values, date.fromisoformat(day)) if reference_values else None)
                                 for label, day in SEASON_ANCHORS.items()},
            'meaning': 'Relative curriculum priority; reporting frequency is not encounter probability.'}
        row['pilot'] = code in poc
        row['confusion_pair_code'] = pair_codes.get(code)
        counts = media.get(code, {'photos': 0, 'audio': 0})
        row['media_at_selection'] = {'photos': counts['photos'], 'audio': counts['audio']}
        raw[code] = {
            'year_round': None if annual_mean is None or year_round_share is None else .5 * annual_mean + .5 * year_round_share,
            'current_season': current if current is not None else 0.0,
            'approaching_window': rise if rise is not None else 0.0,
            'recreational_value': 1.0 if code in pair_codes else (.65 if code in poc else .15),
            'media_availability': min(1.0, (counts['photos'] / TARGETS['photos'] + counts['audio'] / TARGETS['audio']) / 2),
        }

    if not candidates:
        raise ValueError('No reconciled species candidates')
    normalized = {component: _normalize({code: raw[code][component] for code in candidates})
                  for component in WEIGHTS}
    for code, row in candidates.items():
        components = {component: normalized[component].get(code, 0.0) for component in WEIGHTS}
        row['selection_components'] = {component: round(value, 6) for component, value in components.items()}
        row['selection_score'] = round(sum(WEIGHTS[name] * components[name] for name in WEIGHTS), 6)

    ranked = sorted(candidates.values(), key=lambda row: (
        -row['selection_score'], -(row['metrics']['annual_mean_frequency'] or 0),
        -(row['metrics']['current_reporting_frequency'] or 0), row['ebird_species_code']))
    if limit < len(poc):
        raise ValueError('Selection limit cannot exclude the versioned pilot')
    selected = ranked[:limit]
    selected_codes = {row['ebird_species_code'] for row in selected}
    missing_pilot = [row for row in ranked if row['pilot'] and row['ebird_species_code'] not in selected_codes]
    if missing_pilot:
        non_pilot = [row for row in selected if not row['pilot']]
        for forced in missing_pilot:
            if not non_pilot:
                break
            displaced = non_pilot.pop()
            selected[selected.index(displaced)] = forced
        selected = sorted(selected, key=lambda row: ranked.index(row))

    rows = []
    for rank, row in enumerate(selected, 1):
        pair_code = row['confusion_pair_code']
        partner = candidates.get(pair_code)
        rationale = []
        if row['pilot']:
            rationale.append('versioned pilot retained for comparison coverage')
        if pair_code:
            rationale.append('directed confusion pair')
        if (row['metrics']['year_round_frequency_share'] or 0) >= .5:
            rationale.append('year-round regional frequency')
        if (row['metrics']['approaching_window_rise'] or 0) >= .05:
            rationale.append('approaching migration window')
        if (row['media_at_selection']['photos'] >= 2 or row['media_at_selection']['audio'] >= 1):
            rationale.append('existing accepted media')
        rows.append({
            'priority_rank': rank,
            'ebird_species_code': row['ebird_species_code'],
            'common_name': row['common_name'],
            'scientific_name': row['scientific_name'],
            'taxon_id': row['taxon_id'],
            'pilot': row['pilot'],
            'confusion_pair': None if not partner else {
                'common_name': partner['common_name'],
                'ebird_species_code': partner['ebird_species_code']},
            'selection_score': row['selection_score'],
            'selection_components': row['selection_components'],
            'metrics': row['metrics'],
            'media_at_selection': row['media_at_selection'],
            'coverage_target': dict(TARGETS),
            'selection_rationale': rationale or ['regional occurrence signal']})

    return {
        'schema': SCHEMA,
        'generated_at': '2026-11-15',
        'reference_date': reference_date,
        'reference_county': reference_county,
        'selection_limit': limit,
        'taxonomy': {'authority': 'eBird/Clements', 'version': taxonomy_version,
                     'source_taxonomy_version': None,
                     'source_taxonomy_note': 'Annual export bodies do not embed a release; scope is owner-supplied filename/context.'},
        'source_scope': {'start_year': 2016, 'end_year': 2025, 'bin_definition': BIN_DEFINITION,
                         'counties': dict(COUNTIES),
                         'source_sha256': {source['location']: hashlib.sha256(source['raw']).hexdigest() for source in sources}},
        'weights': WEIGHTS,
        'seasonal_anchors': SEASON_ANCHORS,
        'coverage_objective': {**TARGETS, 'note': 'Objective, not authorization to accept questionable examples or weaken gates.'},
        'confusion_pairs': [{'left': left, 'right': right} for left, right in PAIR_NAMES],
        'candidate_counts': {'source_reconciled_species': len(candidates),
                             'source_unresolved_names': len(set().union(*unresolved.values())) if unresolved else 0,
                             'selected': len(rows), 'pilot_selected': sum(row['pilot'] for row in rows)},
        'unresolved_scope': {location: len(names) for location, names in unresolved.items()},
        'species': rows,
        'limitations': [
            'Selection uses historical submitted-checklist fractions, not abundance or encounter probability.',
            'Source taxonomy release is unknown; crosswalks use unique common names plus target scientific-name agreement.',
            'Unresolved, non-species and split/lump-ambiguous names remain excluded rather than guessed.',
            'Media availability is a snapshot at selection time; accepted coverage is measured again after curation.'],
    }, {'candidates': sorted(candidates.values(), key=lambda row: row['ebird_species_code']),
        'unresolved_names_by_county': unresolved}


def derive(directory=PRIVATE / 'occurrence/incoming', *, output=UNIVERSE, reference_date=DEFAULT_DATE,
           limit=100, media_path=None):
    files = sorted(directory.glob('ebird_*_barchart.txt'))
    if len(files) != len(COUNTIES):
        raise ValueError('Exactly seven annual county references required')
    taxonomy = Client(budget=0).get('https://api.ebird.org/v2/ref/taxonomy/ebird', {'fmt': 'json', 'cat': 'species'})
    sources = [parse_source(path, taxonomy) for path in files]
    poc = json.loads((ROOT / 'experiments/poc-species.json').read_text())
    media_file = Path(media_path) if media_path else PRIVATE / 'local-mvp/approved-media.json'
    if not media_file.exists():
        media_file = PRIVATE / 'phase05/approved-media.json'
    media = json.loads(media_file.read_text()) if media_file.exists() else {'assets': []}
    universe, private = build_universe(sources, '2026', poc, media,
                                       reference_date=reference_date, limit=limit)
    save(output, universe)
    save(PRIVATE / 'occurrence/teaching-universe-candidates.json', private)
    print(json.dumps({key: universe[key] for key in ['schema', 'reference_date', 'selection_limit',
        'candidate_counts', 'unresolved_scope']}, indent=2))
    return universe


def status(directory=PRIVATE / 'occurrence/incoming', output=UNIVERSE):
    return {'incoming_exports': len(list(directory.glob('ebird_*_barchart.txt'))),
            'universe_exists': output.exists(),
            'selected': len(json.loads(output.read_text())['species']) if output.exists() else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['derive', 'status'], nargs='?', default='derive')
    parser.add_argument('--directory', type=Path, default=PRIVATE / 'occurrence/incoming')
    parser.add_argument('--output', type=Path, default=UNIVERSE)
    parser.add_argument('--reference-date', default=DEFAULT_DATE)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--media', type=Path, default=None)
    args = parser.parse_args()
    if args.command == 'status':
        print(json.dumps(status(args.directory, args.output), indent=2))
    else:
        derive(args.directory, output=args.output, reference_date=args.reference_date,
               limit=args.limit, media_path=args.media)


if __name__ == '__main__':
    main()
