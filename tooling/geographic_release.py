"""Compile only reviewed, real, publicly eligible compact geographic products.

The package is private staging until the existing token-authenticated publisher uploads it.
No source artifacts, exact points, grants, paths or private validation notes are serialized.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import duckdb

from tooling.discover import save
from tooling.geographic_engine import identity, SAFE_ID
from tooling.geography_io import digest, private_path
from tooling.seasonal import COUNTIES


def compact(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def compile_package(build_path, decision_path, validation_path, output):
    build_path,decision_path,validation_path=map(Path,[build_path,decision_path,validation_path])
    manifest=json.loads((build_path/'manifest.json').read_text())
    decision=json.loads(decision_path.read_text()); validation=json.loads(validation_path.read_text())
    if manifest.get('evidence')!='real_ebd_sed' or validation.get('evidence')!='real_ebd_sed':
        raise ValueError('Synthetic/unvalidated inputs cannot be published')
    if decision.get('build_identity')!=manifest['identity'] or validation.get('build_identity')!=manifest['identity']:
        raise ValueError('Publication evidence must match this exact build')
    if decision.get('validation_sha256')!=digest(validation_path) or decision.get('validation_decision')!='accepted_with_recorded_limitations' or not decision.get('validation_rationale'):
        raise ValueError('Recorded review of measured real-data validation required')
    if validation.get('historical_validation')!='measured' or validation.get('reference_count')!=7 or len(validation.get('counties',[]))!=7:
        raise ValueError('Seven reference comparisons required before geographic release')
    if {r.get('location') for r in validation['counties']}!=set(COUNTIES):
        raise ValueError('Seven distinct pilot county references required')
    if any(not decision.get(k) for k in ['terms_url','attribution','public_use_basis','reviewed_by','reviewed_at','approved_regions']):
        raise ValueError('Explicit public noncommercial eligibility and attribution required')
    if decision.get('public_noncommercial_eligible') is not True:
        raise ValueError('Public-use eligibility gate failed')
    for p,h in manifest['outputs'].items():
        if digest(build_path/p)!=h:raise ValueError('Build output changed after validation')
    locations={l['id']:l for l in manifest['config']['locations']}
    if not set(decision['approved_regions'])<=set(locations):raise ValueError('Unknown approved region')
    if any(locations[r].get('parent') and locations[r]['parent'] not in decision['approved_regions'] for r in decision['approved_regions']):
        raise ValueError('All declared fallback parents must also be eligible')
    root=private_path(output)
    if (root/'manifest.json').exists():raise ValueError('Immutable publication package already exists')
    version=identity({'build':manifest['identity'],'decision':decision,'validation':digest(validation_path)})
    regions=[]
    with duckdb.connect() as db:
        for region in sorted(decision['approved_regions']):
            if not SAFE_ID.fullmatch(region):raise ValueError('Unsafe region ID')
            loc=locations[region]
            rows=db.execute("SELECT species_code,native_bin,sample_size,detections,reporting_frequency,value_status,day_support FROM read_parquet(?,hive_partitioning=true) WHERE location=? AND period='multi' ORDER BY species_code,native_bin",[str(build_path/'profiles/**/*.parquet'),region]).fetchall()
            species={}
            for code,b,n,k,f,status,days in rows:
                species.setdefault(code,[]).append([b,n,k,round(f,7) if f is not None else None,status,days])
            product={'schema':'birdahead-geographic-profile-v1','version':version,'region':region,
                     'parent':loc.get('parent'),'signal':'historical_reporting_frequency',
                     'calendar':manifest['calendar'],'years':[manifest['config']['start_year'],manifest['config']['end_year']],
                     'minimum_support':manifest['config']['minimum_support'],
                     'columns':['native_bin','sample_size','detections','reporting_frequency','value_status','day_support'],
                     'species':species,'source_snapshot':manifest['snapshot']['snapshot_id'],
                     'source_taxonomy_version':manifest['snapshot']['source_taxonomy_version'],
                     'target_taxonomy_version':manifest['snapshot']['target_taxonomy_version'],
                     'attribution':decision['attribution'],'terms_url':decision['terms_url'],
                     'limitations':decision.get('public_limitations',[])}
            raw=compact(product)
            if len(raw)>2_000_000:raise ValueError('Regional profile exceeds compact delivery ceiling')
            key=f'releases/geography/{version}/{region}.json'
            path=root/(region+'.json');path.write_bytes(raw)
            regions.append({'id':region,'name':loc['name'],'kind':loc['kind'],'parent':loc.get('parent'),
                            'key':key,'bytes':len(raw),'sha256':digest(path)})
    index={'schema':'birdahead-geographic-index-v1','version':version,'regions':regions,
           'public_noncommercial_eligible':True,'attribution':decision['attribution'],'terms_url':decision['terms_url']}
    save(root/'manifest.json',index)
    return index


def load_package(path):
    path=Path(path)
    index=json.loads((path/'manifest.json').read_text())
    import re
    if index.get('schema')!='birdahead-geographic-index-v1' or index.get('public_noncommercial_eligible') is not True or not re.fullmatch('[a-f0-9]{64}',index.get('version','')):
        raise ValueError('Ineligible geography package')
    if not index.get('regions') or len(index['regions'])>5000:
        raise ValueError('Bounded regional index required')
    ids=set()
    for row in index['regions']:
        if not SAFE_ID.fullmatch(row['id']) or row['id'] in ids or row['key']!=f"releases/geography/{index['version']}/{row['id']}.json":
            raise ValueError('Invalid package region')
        ids.add(row['id'])
        p=path/(row['id']+'.json')
        if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('Package checksum mismatch')
    return index


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['build','decision','validation','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=compile_package(a.build,a.decision,a.validation,a.output)
    print(json.dumps({'version':result['version'],'regions':len(result['regions'])}))
