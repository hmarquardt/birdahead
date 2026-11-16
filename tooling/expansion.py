"""Bounded, resumable Phase Two media expansion over the teaching universe.

Each batch persists a checkpoint after every downloaded asset. Request, media-byte
and retry budgets are explicit. Source evidence, rights and contributor diversity
are filtered before download; Model gates remain in tooling.curation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from tooling.acquire import (CATALOG, COMMERCIAL_CODES, NONCOMMERCIAL_CODES, WORK, SafeClient,
                             file_download, image_metrics, inat_license_info, license_info)
from tooling.discover import PRIVATE, ROOT, UA, now, save
from tooling.histograms import UNIVERSE
from tooling.teaching_universe import PAIR_NAMES

STATE_DIR = WORK / 'expansion'
STATE = STATE_DIR / 'state.json'
REPORT = ROOT / 'experiments/phase-two-acquisition.json'
SCHEMA = 'birdahead-expansion-state-v1'
CANDIDATE_TARGETS = {'photos': 8, 'audio': 5}
ACCEPTED_TARGETS = {'photos': 5, 'audio': 3}
DEFAULT_BUDGETS = {'requests': 450, 'media_bytes': 1_200_000_000, 'retries': 2, 'max_assets': 900}
BOUNDING_BOX = {'swlat': 24, 'swlng': -100, 'nelat': 52, 'nelng': -60}
HIGH_RISK = {name for pair in PAIR_NAMES for name in pair}
ALIASES = {'Astur cooperii': ['Accipiter cooperii'],
           'Leuconotopicus villosus': ['Dryobates villosus', 'Picoides villosus'],
           'Antigone canadensis': ['Grus canadensis']}


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def _assets(catalog):
    return catalog.get('assets', []) if isinstance(catalog, dict) else catalog


def media_counts(catalog):
    counts = defaultdict(lambda: {'photos': 0, 'photos_accepted': 0, 'audio': 0, 'audio_accepted': 0})
    for asset in _assets(catalog):
        kind = asset.get('kind')
        if kind not in {'photo', 'audio'}:
            continue
        bucket = 'photos' if kind == 'photo' else 'audio'
        counts[asset.get('species_code')][bucket] += 1
        if asset.get('automated_decision', {}).get('status') in {'automatically_accepted', 'human_approved', 'expert_verified'}:
            counts[asset.get('species_code')][bucket + '_accepted'] += 1
    return counts


def universe_species(path=UNIVERSE):
    universe = _load(path)
    if not universe or universe.get('schema') != 'birdahead-teaching-universe-v1':
        raise ValueError('Run tooling.teaching_universe derive before expansion')
    return universe['species']


def plan(catalog, species, budgets=None):
    budgets = {**DEFAULT_BUDGETS, **(budgets or {})}
    counts = media_counts(catalog)
    rows = []
    for row in species:
        current = counts[row['ebird_species_code']]
        deficit = {}
        for kind, bucket in [('photos', 'photos'), ('audio', 'audio')]:
            if current[bucket + '_accepted'] >= ACCEPTED_TARGETS[kind]:
                deficit[kind] = 0
            else:
                deficit[kind] = max(0, CANDIDATE_TARGETS[kind] - current[bucket])
        rows.append({
            'ebird_species_code': row['ebird_species_code'],
            'common_name': row['common_name'],
            'scientific_name': row['scientific_name'],
            'priority_rank': row['priority_rank'],
            'pilot': row['pilot'],
            'current': dict(current),
            'deficit': deficit})
    return {'schema': SCHEMA, 'created_at': _utc(), 'updated_at': _utc(),
            'universe_sha256': hashlib.sha256(UNIVERSE.read_bytes()).hexdigest(),
            'candidate_targets': CANDIDATE_TARGETS, 'accepted_targets': ACCEPTED_TARGETS,
            'budgets': budgets, 'cursor': 0, 'complete': False,
            'counters': {'requests': 0, 'downloads': 0, 'media_bytes': 0, 'retries': 0,
                         'assets_added': 0, 'elapsed_seconds': 0},
            'failures': {}, 'failed_urls': {}, 'taxon_ids': {}, 'species': rows,
            'limitations': ['Candidate targets allow for curation rejection; they do not guarantee accepted coverage.',
                            'Source assertions are not independent ground truth; model/rights gates remain separate.']}


def load_state(catalog, species, budgets=None):
    state = _load(STATE)
    if state is None:
        return plan(catalog, species, budgets)
    if state.get('schema') != SCHEMA:
        raise ValueError('Unsupported expansion checkpoint; start a new bounded plan')
    if state.get('universe_sha256') != hashlib.sha256(UNIVERSE.read_bytes()).hexdigest():
        raise ValueError('Teaching universe changed; archive the old checkpoint before resuming')
    return state


def _failure(state, species_code, kind, reason):
    key = f'{kind}: {reason}'
    state['failures'][key] = state['failures'].get(key, 0) + 1
    state.setdefault('failure_by_species', {}).setdefault(species_code, []).append({kind: reason})


def _budget_left(state, client):
    used = state['counters']['requests']
    return state['budgets']['requests'] - used


def _sync_requests(state, client, before):
    state['counters']['requests'] += max(0, client.calls - before)


def _note_bytes(state, size):
    state['counters']['media_bytes'] += int(size)
    state['counters']['downloads'] += 1


def _download(url, dest, limit, state, retries):
    if url in state['failed_urls']:
        return None, 'URL previously exceeded retry budget'
    existed = Path(dest).exists()
    last = None
    for attempt in range(retries + 1):
        try:
            raw = file_download(url, Path(dest), limit)
            if not existed:
                _note_bytes(state, len(raw))
            return raw, None
        except RuntimeError as exc:
            last = str(exc)
            state['counters']['retries'] += 1
            if attempt < retries:
                time.sleep(.4 * (attempt + 1))
    state['failed_urls'][url] = {'reason': last, 'at': _utc()}
    return None, last


def _lineage(obs, target_id):
    taxon = obs.get('taxon') or {}
    lineage = set(taxon.get('ancestor_ids') or [])
    lineage.add(taxon.get('id'))
    return target_id in lineage or obs.get('community_taxon_id') == target_id


def _concordant(obs, owner, target_id):
    names = set()
    for identification in obs.get('identifications', []):
        if not identification.get('current') or str(identification.get('user', {}).get('id')) == owner:
            continue
        taxon = identification.get('taxon') or {}
        lineage = set(taxon.get('ancestor_ids') or [])
        lineage.add(taxon.get('id'))
        if target_id in lineage:
            names.add(str(identification['user']['id']))
    return sorted(names)


def _month(obs):
    value = obs.get('observed_on') or ''
    return value[:7] if value else 'unknown'


def _photo_options(data, target, target_id, contributors, existing_observations, risky):
    """Filter observations before any media transfer. Returns ordered options."""
    options = []
    for obs in data.get('results', []):
        owner = str(obs.get('user', {}).get('id'))
        if str(obs.get('id')) in existing_observations or obs.get('flags') or obs.get('captive'):
            continue
        if obs.get('quality_grade') != 'research' or not obs.get('community_taxon_id'):
            continue
        if not _lineage(obs, target_id):
            continue
        if contributors[owner] >= 2:
            continue
        concordant = _concordant(obs, owner, target_id)
        if len(concordant) < (2 if risky else 1):
            continue
        for photo in obs.get('photos', []):
            code = photo.get('license_code')
            dimensions = photo.get('original_dimensions') or {}
            width, height = int(dimensions.get('width') or 0), int(dimensions.get('height') or 0)
            if code not in NONCOMMERCIAL_CODES or photo.get('hidden') or photo.get('flags'):
                continue
            if min(width, height) < 240 or max(width, height) < 500:
                continue
            options.append({'obs': obs, 'photo': photo, 'owner': owner, 'concordant': concordant,
                            'dimensions': [width, height], 'month': _month(obs),
                            'novel_contributor': contributors[owner] == 0,
                            'source_taxon_rank': (obs.get('taxon') or {}).get('rank')})
            break  # One image per observation/encounter.
    # Prefer new contributors, then source-visible biological diversity by month.
    seen_months = Counter(option['month'] for option in options)
    options.sort(key=lambda item: (not item['novel_contributor'], seen_months[item['month']],
                                   item['source_taxon_rank'] != 'species', item['owner']))
    return options


def _local_path(dest):
    path = Path(dest).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _photo_record(option, target, target_id, raw, metrics, dest):
    obs, photo, owner = option['obs'], option['photo'], option['owner']
    taxon = obs.get('taxon') or {}
    license = inat_license_info(photo['license_code'])
    source_name = taxon.get('name') or ''
    lineage_kind = 'exact_species' if taxon.get('id') == target_id else 'target_in_source_lineage'
    record = {
        'id': f"inat-{photo['id']}", 'asset_id': photo['id'], 'kind': 'photo', 'source': 'inaturalist',
        'source_record_id': obs['id'], 'source_url': obs.get('uri'),
        'asset_page_url': f"https://www.inaturalist.org/photos/{photo['id']}",
        'media_url': photo['url'].replace('/square.', '/large.'),
        'source_taxon_id': taxon.get('id'), 'source_scientific_name': source_name,
        'source_taxon_rank': taxon.get('rank'), 'community_taxon_id': obs.get('community_taxon_id'),
        'target_taxon_id': target_id, 'ebird_species_code': target['ebird_species_code'],
        'species_code': target['ebird_species_code'], 'common_name': target['common_name'],
        'scientific_name': target['scientific_name'], 'taxonomy_version': 'eBird/Clements 2026',
        'creator': obs.get('user', {}).get('name') or obs.get('user', {}).get('login'),
        'contributor_id': owner, 'creator_basis': 'observation owner; confirm photo credit at asset page',
        'attribution': photo.get('attribution'), 'license_code': license['license_code'],
        'license_url': license['license_url'], 'license_version': license['license_version'],
        'rights_status': 'open-license candidate; verify asset page and credit before publication',
        'permitted_storage': True, 'permitted_modification': True, 'permitted_delivery': True,
        'permitted_offline': True, 'permitted_scope': 'recreational noncommercial; retain exact attribution and license',
        'share_alike': license['share_alike'], 'commercial_compatible': license['commercial_compatible'],
        'observation_license_code': obs.get('license_code'), 'source_quality_grade': obs.get('quality_grade'),
        'identification_agreements': obs.get('num_identification_agreements'),
        'identification_disagreements': obs.get('num_identification_disagreements'),
        'observed_on': obs.get('observed_on'), 'uploaded': obs.get('created_at'), 'geography': None,
        'location_policy': 'exact coordinates intentionally excluded; eastern North America query envelope only',
        'source_obscured': obs.get('obscured'), 'sex': None, 'age': None, 'plumage': None, 'pose': None,
        'vocalization': None, 'source_annotations': obs.get('annotations', []),
        'source_biological_attributes': None,
        'biological_attribute_status': 'source annotations retained but not interpreted as verified traits',
        'original_dimensions': photo.get('original_dimensions'), 'technical_metrics': metrics,
        'local_path': _local_path(dest), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'source_verified': True, 'machine_screened': False, 'human_approved': False, 'expert_verified': False,
        'rights_approved': False, 'biology_approved': False, 'review_state': 'candidate', 'model_results': [],
        'duplicate_flags': [], 'audit_selected': False, 'derivative_of': None, 'derivative_recipe': None,
        'presentation_modification_notice': 'Downloaded source rendition; no local pixel modifications.',
        'source_evidence': {'quality_grade': obs.get('quality_grade'), 'community_taxon_id': obs.get('community_taxon_id'),
            'lineage_match': lineage_kind, 'source_taxon_name': source_name,
            'concordant_non_owner_identifiers': option['concordant'],
            'owner_used_computer_vision': obs.get('owners_identification_from_vision'),
            'source_assertion_not_independent_ground_truth': True},
        'acquisition_pass': 'phase two expansion', 'acquisition_selection': 'source support + contributor diversity + resolution prefilter',
        'retrieved_at': _utc()}
    record.update(license)
    record.update(inat_license_info(photo['license_code']))
    return record


def resolve_taxon(species, state, client):
    code = species['ebird_species_code']
    cached = state['taxon_ids'].get(code)
    if cached:
        return cached['id'], None
    before = client.calls
    try:
        data = client.json('https://api.inaturalist.org/v1/taxa',
                           {'q': species['scientific_name'], 'rank': 'species', 'per_page': 3, 'is_active': 'true'})
    except RuntimeError as exc:
        _sync_requests(state, client, before)
        return None, f'iNaturalist taxon lookup failed: {exc}'
    _sync_requests(state, client, before)
    exact = [row for row in data.get('results', [])
             if row.get('rank') == 'species' and row.get('name', '').casefold() == species['scientific_name'].casefold()]
    if len(exact) != 1:
        return None, 'no unique active iNaturalist species taxon for target scientific name'
    state['taxon_ids'][code] = {'id': exact[0]['id'], 'name': exact[0]['name'], 'at': _utc()}
    save(STATE, state)
    return exact[0]['id'], None


def _observations(client, state, taxon_id, page=1):
    before = client.calls
    try:
        data = client.json('https://api.inaturalist.org/v1/observations', {
            'taxon_id': taxon_id, 'quality_grade': 'research', 'captive': 'false',
            'photo_license': ','.join(sorted(NONCOMMERCIAL_CODES)), 'per_page': 6, 'page': page,
            'order_by': 'votes', 'order': 'desc', **BOUNDING_BOX})
    finally:
        _sync_requests(state, client, before)
    return data


def expand_photos(species, state, client, catalog, *, catalog_path, media_dir, budgets, downloader, metrics_fn, risky, asset_ceiling=None):
    code = species['ebird_species_code']
    existing = [asset for asset in catalog if asset.get('kind') == 'photo' and asset.get('species_code') == code]
    accepted = sum(asset.get('automated_decision', {}).get('status') in
                   {'automatically_accepted', 'human_approved', 'expert_verified'} for asset in existing)
    deficit = 0 if accepted >= ACCEPTED_TARGETS['photos'] else max(0, CANDIDATE_TARGETS['photos'] - len(existing))
    if deficit <= 0:
        return 0, 'no photo deficit'
    ceiling = budgets['max_assets'] if asset_ceiling is None else min(asset_ceiling, budgets['max_assets'])
    target_id, reason = resolve_taxon(species, state, client)
    if target_id is None:
        _failure(state, code, 'photo', reason)
        return 0, reason
    contributors = Counter(asset.get('contributor_id') for asset in existing)
    existing_observations = {str(asset.get('source_record_id')) for asset in existing}
    added = 0
    for page in (1, 2):
        if added >= deficit or state['counters']['assets_added'] >= ceiling:
            break
        if state['counters']['media_bytes'] >= budgets['media_bytes']:
            _failure(state, code, 'photo', 'media byte budget exhausted')
            break
        if _budget_left(state, client) <= 0:
            _failure(state, code, 'photo', 'request budget exhausted')
            break
        try:
            data = _observations(client, state, target_id, page)
        except RuntimeError as exc:
            _failure(state, code, 'photo', str(exc))
            break
        options = _photo_options(data, species, target_id, contributors, existing_observations, risky)
        if not options:
            _failure(state, code, 'photo', 'no observation met source-support, contributor, resolution and rights filters')
        for option in options:
            if added >= deficit or state['counters']['assets_added'] >= ceiling:
                break
            if state['counters']['media_bytes'] >= budgets['media_bytes']:
                _failure(state, code, 'photo', 'media byte budget exhausted')
                break
            photo = option['photo']
            url = photo['url'].replace('/square.', '/large.')
            suffix = Path(url.split('?', 1)[0]).suffix or '.jpg'
            dest = Path(media_dir) / f"inat-{photo['id']}{suffix}"
            raw, error = downloader(url, dest, 5_000_000, state, budgets['retries'])
            if raw is None:
                _failure(state, code, 'photo', error or 'download failed')
                continue
            try:
                metrics = metrics_fn(dest)
            except Exception:
                _failure(state, code, 'photo', 'downloaded image could not be decoded')
                continue
            record = _photo_record(option, species, target_id, raw, metrics, dest)
            if any(asset.get('id') == record['id'] for asset in catalog):
                continue
            catalog.append(record); save(catalog_path, catalog)
            state['counters']['assets_added'] += 1; added += 1
            contributors[option['owner']] += 1
            existing_observations.add(str(option['obs'].get('id')))
            save(STATE, state)
        if len(data.get('results', [])) < 6:
            break
    return added, None

def xc_query(species, scientific=None):
    return f'sp:"{scientific or species["scientific_name"]}" grp:birds box:24,-100,52,-60 id?:no q:">C"'


def _seconds(value):
    try:
        parts = [float(part) for part in str(value or '').split(':')]
        return sum(part * 60 ** index for index, part in enumerate(reversed(parts))) if parts else 0
    except ValueError:
        return 0


def _audio_options(records, species, contributors, types, risky):
    options = []
    for row in records:
        info = license_info(row.get('lic'))
        if not info.get('derivatives_permitted'):
            continue
        if row.get('status') not in [None, '', 'identified'] or row.get('q') not in ['A', 'B'] or row.get('auto') == 'yes':
            continue
        if risky and row.get('animal-seen') != 'yes':
            continue
        if any(term in (row.get('type') or '').lower() for term in ['uncertain', '?']):
            continue
        duration = _seconds(row.get('length'))
        if not 3 <= duration <= 180:
            continue
        en, scientific = row.get('en'), f"{row.get('gen')} {row.get('sp')}"
        if en != species['common_name'] and scientific != species['scientific_name']:
            continue
        if contributors[row.get('rec')] >= 2:
            continue
        url = row.get('file') or ''
        if url.startswith('//'):
            url = 'https:' + url
        if not url.startswith('https://xeno-canto.org/'):
            continue
        options.append({'row': row, 'license': info, 'duration': duration, 'url': url,
                        'novel_contributor': contributors[row.get('rec')] == 0,
                        'type': row.get('type') or 'unknown'})
    seen_types = Counter(option['type'] for option in options)
    options.sort(key=lambda item: (not item['license'].get('commercial_compatible'), item['row'].get('q') != 'A',
                                   not item['novel_contributor'], seen_types[item['type']], -int(item['row'].get('id', '0'))))
    return options


def _audio_record(option, species, raw, dest):
    row, info = option['row'], option['license']
    record = {
        'id': 'xc-' + str(row['id']), 'asset_id': row['id'], 'kind': 'audio', 'source': 'xeno_canto',
        'source_record_id': row['id'], 'species_code': species['ebird_species_code'],
        'ebird_species_code': species['ebird_species_code'], 'common_name': species['common_name'],
        'scientific_name': species['scientific_name'], 'source_scientific_name': f"{row.get('gen')} {row.get('sp')}",
        'taxonomy_version': 'eBird/Clements 2026', 'source_url': 'https://xeno-canto.org/' + str(row['id']),
        'media_url': option['url'], 'creator': row.get('rec'), 'contributor_id': row.get('rec'),
        'attribution': f"{row.get('rec')}, XC{row['id']}, {row.get('lic')}", **info,
        'rights_status': 'open-license candidate; verify recording page and credit before publication',
        'permitted_storage': True, 'permitted_modification': True, 'permitted_delivery': True,
        'permitted_offline': True, 'permitted_scope': 'recreational noncommercial; retain exact attribution and license',
        'vocalization': row.get('type') or None, 'sex': row.get('sex') or None, 'age': row.get('stage') or None,
        'plumage': None, 'quality_grade': row.get('q'), 'identification_status': row.get('status'),
        'observed_on': row.get('date'), 'uploaded': row.get('uploaded'), 'country': row.get('cnt'),
        'biological_attribute_status': 'source-asserted vocalization/sex/age; not independently verified',
        'source_evidence': {'identification_status': row.get('status'), 'animal_seen': row.get('animal-seen'),
            'recording_method': row.get('method'), 'background_species': row.get('also'),
            'annotation_set_present': bool(row.get('annotation-set')),
            'source_species_name_match': row.get('en') == species['common_name'] or
                f"{row.get('gen')} {row.get('sp')}" == species['scientific_name'],
            'source_assertion_not_independent_ground_truth': True},
        'local_path': _local_path(dest), 'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw), 'source_verified': True, 'machine_screened': False, 'human_approved': False,
        'expert_verified': False, 'rights_approved': False, 'biology_approved': False, 'review_state': 'candidate',
        'model_results': [], 'technical_metrics': {'source_duration': row.get('length'),
            'source_sample_rate': row.get('smp'), 'duration_seconds': option['duration']},
        'duplicate_flags': [], 'audit_selected': False, 'derivative_of': None, 'derivative_recipe': None,
        'presentation_modification_notice': 'Downloaded source recording; no local audio modification.',
        'acquisition_pass': 'phase two expansion', 'acquisition_selection': 'quality + rights + recordist diversity + duration prefilter',
        'retrieved_at': _utc()}
    return record


def expand_audio(species, state, client, catalog, *, catalog_path, media_dir, budgets, downloader, risky, asset_ceiling=None):
    code = species['ebird_species_code']
    existing = [asset for asset in catalog if asset.get('kind') == 'audio' and asset.get('species_code') == code]
    accepted = sum(asset.get('automated_decision', {}).get('status') in
                   {'automatically_accepted', 'human_approved', 'expert_verified'} for asset in existing)
    deficit = 0 if accepted >= ACCEPTED_TARGETS['audio'] else max(0, CANDIDATE_TARGETS['audio'] - len(existing))
    if deficit <= 0:
        return 0, 'no audio deficit'
    ceiling = budgets['max_assets'] if asset_ceiling is None else min(asset_ceiling, budgets['max_assets'])
    contributors = Counter(asset.get('contributor_id') for asset in existing)
    types = Counter(asset.get('vocalization') or 'unknown' for asset in existing)
    added = 0
    for scientific in [species['scientific_name'], *ALIASES.get(species['scientific_name'], [])]:
        if added >= deficit:
            break
        if _budget_left(state, client) <= 0 or state['counters']['media_bytes'] >= budgets['media_bytes']:
            _failure(state, code, 'audio', 'request or byte budget exhausted')
            break
        before = client.calls
        try:
            data = client.json('https://xeno-canto.org/api/3/recordings',
                               {'query': xc_query(species, scientific), 'per_page': 50, 'page': 1}, xc=True)
        except RuntimeError as exc:
            _sync_requests(state, client, before)
            _failure(state, code, 'audio', str(exc))
            continue
        _sync_requests(state, client, before)
        options = _audio_options(data.get('recordings', []), species, contributors, types, risky)
        if not options:
            _failure(state, code, 'audio', 'no recording met quality, rights, duration, recordist and source-name filters')
        for option in options:
            if added >= deficit or state['counters']['assets_added'] >= ceiling:
                break
            if state['counters']['media_bytes'] >= budgets['media_bytes']:
                _failure(state, code, 'audio', 'media byte budget exhausted')
                break
            row = option['row']
            asset_id = 'xc-' + str(row['id'])
            if any(asset.get('id') == asset_id for asset in catalog):
                continue
            suffix = Path(option['url'].split('?', 1)[0]).suffix or '.mp3'
            dest = Path(media_dir) / (asset_id + suffix)
            raw, error = downloader(option['url'], dest, 8_000_000, state, budgets['retries'])
            if raw is None:
                _failure(state, code, 'audio', error or 'download failed')
                continue
            record = _audio_record(option, species, raw, dest)
            catalog.append(record); save(catalog_path, catalog)
            state['counters']['assets_added'] += 1; added += 1
            contributors[option['row'].get('rec')] += 1
            types[option['type']] += 1
            save(STATE, state)
        if data.get('numPages', 1) <= 1:
            break
    return added, None


def write_report(state, catalog=None):
    catalog = _assets(_load(CATALOG) or []) if catalog is None else _assets(catalog)
    counts = media_counts(catalog)
    per_species = []
    for row in state['species']:
        current = counts[row['ebird_species_code']]
        per_species.append({**{key: row[key] for key in ['priority_rank', 'ebird_species_code', 'common_name', 'pilot']},
                            'photo_candidates': current['photos'], 'photo_accepted': current['photos_accepted'],
                            'audio_candidates': current['audio'], 'audio_accepted': current['audio_accepted']})
    failures = Counter()
    for reason, count in state.get('failures', {}).items():
        failures[reason.split(': ', 1)[-1]] += count
    summary = {
        'schema': 'birdahead-phase-two-acquisition-v1', 'at': _utc(),
        'scope': 'Bounded local recreational acquisition; no bulk geographic or restricted-media download',
        'candidate_targets': state['candidate_targets'], 'accepted_targets': state['accepted_targets'],
        'budgets': state['budgets'], 'counters': state['counters'],
        'universe_species': len(state['species']), 'checkpoint_cursor': state.get('cursor'),
        'checkpoint_complete': state.get('complete'),
        'species_with_any_photo_candidate': sum(row['photo_candidates'] > 0 for row in per_species),
        'species_with_any_audio_candidate': sum(row['audio_candidates'] > 0 for row in per_species),
        'species_with_five_accepted_photos': sum(row['photo_accepted'] >= 5 for row in per_species),
        'species_with_three_accepted_audio': sum(row['audio_accepted'] >= 3 for row in per_species),
        'candidate_media_bytes_retained': sum(asset.get('bytes', 0) for asset in catalog),
        'failure_reasons': dict(failures.most_common()),
        'per_species': per_species,
        'limitations': state.get('limitations', []) + [
            'Counts include all catalog candidates; accepted coverage is determined separately by curation gates.',
            'A bounded batch may stop before every species reaches its candidate target.']}
    save(REPORT, summary)
    return summary


def run(*, max_species=None, max_assets=None, budgets=None, reset=False, catalog_path=None,
        media_dir=None, client=None, downloader=_download, metrics_fn=image_metrics):
    catalog_path = Path(catalog_path) if catalog_path else CATALOG
    media_dir = Path(media_dir) if media_dir else WORK / 'media'
    catalog = _load(catalog_path) or []
    species = universe_species()
    state = plan(catalog, species, budgets) if reset or not STATE.exists() else load_state(catalog, species, budgets)
    if budgets:
        state['budgets'].update(budgets)
    client = client or SafeClient(budget=state['budgets']['requests'])
    start = time.monotonic()
    start_assets = state['counters']['assets_added']
    processed = 0
    ceiling = state['counters']['assets_added'] + (max_assets if max_assets is not None else 10**9)
    try:
        while state['cursor'] < len(state['species']):
            if max_species is not None and processed >= max_species:
                break
            if max_assets is not None and state['counters']['assets_added'] - start_assets >= max_assets:
                break
            row = state['species'][state['cursor']]
            if not any(row['deficit'].values()):
                state['cursor'] += 1
                continue
            risky = row['common_name'] in HIGH_RISK
            expand_photos(row, state, client, catalog, catalog_path=catalog_path, media_dir=media_dir,
                          budgets=state['budgets'], downloader=downloader, metrics_fn=metrics_fn, risky=risky, asset_ceiling=ceiling)
            expand_audio(row, state, client, catalog, catalog_path=catalog_path, media_dir=media_dir,
                         budgets=state['budgets'], downloader=downloader, risky=risky, asset_ceiling=ceiling)
            state['cursor'] += 1
            processed += 1
            state['updated_at'] = _utc()
            save(STATE, state)
    finally:
        state['counters']['elapsed_seconds'] = round(state['counters'].get('elapsed_seconds', 0) + time.monotonic() - start, 3)
        state['complete'] = state['cursor'] >= len(state['species'])
        state['updated_at'] = _utc()
        save(STATE, state)
        write_report(state, catalog)
        if getattr(client, 'events', None):
            save(WORK / 'request-logs' / f"expansion-{time.time_ns()}.json", client.events)
    summary = write_report(state, catalog)
    print(json.dumps({key: summary[key] for key in ['universe_species', 'counters', 'species_with_any_photo_candidate',
        'species_with_any_audio_candidate', 'species_with_five_accepted_photos', 'species_with_three_accepted_audio']}, indent=2))
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'run', 'status', 'report'], nargs='?', default='status')
    parser.add_argument('--max-species', type=int, default=None)
    parser.add_argument('--max-assets', type=int, default=None)
    parser.add_argument('--requests', type=int, default=None)
    parser.add_argument('--media-bytes', type=int, default=None)
    parser.add_argument('--retries', type=int, default=None)
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()
    budgets = {key: value for key, value in {'requests': args.requests, 'media_bytes': args.media_bytes,
        'retries': args.retries}.items() if value is not None}
    if args.command == 'status':
        state = _load(STATE)
        print(json.dumps({'exists': bool(state), 'cursor': (state or {}).get('cursor'),
            'species': len((state or {}).get('species', [])), 'counters': (state or {}).get('counters'),
            'budgets': (state or {}).get('budgets')}, indent=2))
    elif args.command == 'plan':
        catalog = _load(CATALOG) or []
        state = plan(catalog, universe_species(), budgets)
        save(STATE, state)
        print(json.dumps({'planned_species': len(state['species']),
            'photo_deficit_candidates': sum(row['deficit']['photos'] for row in state['species']),
            'audio_deficit_candidates': sum(row['deficit']['audio'] for row in state['species']),
            'budgets': state['budgets']}, indent=2))
    elif args.command == 'report':
        state = _load(STATE)
        if not state:
            raise SystemExit('No expansion checkpoint; run plan first')
        print(json.dumps(write_report(state), indent=2))
    else:
        run(max_species=args.max_species, max_assets=args.max_assets, budgets=budgets, reset=args.reset)


if __name__ == '__main__':
    main()
