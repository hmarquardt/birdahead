"""Denominator-first comparison with private seven-county histogram references."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics

import duckdb

from tooling.discover import PRIVATE, ROOT, save
from tooling.geography_io import digest


def compare(build_path=None, references=PRIVATE/'occurrence/profiles'):
    files=sorted(Path(references).glob('*.json'))
    baseline=[]
    for path in files:
        profile=json.loads(path.read_text())
        if 'metadata' not in profile or 'sample_sizes' not in profile['metadata']:continue
        baseline.append((path,profile))
    report={'schema':'birdahead-geographic-validation-v1','reference_count':len(baseline),
            'reference_samples':sum(sum(p['metadata']['sample_sizes']) for _,p in baseline),
            'historical_validation':'blocked_source_unavailable' if not build_path else 'measured',
            'evidence':'real_histogram_reference_inventory_only' if not build_path else None,
            'build_identity':None,'counties':[],
            'investigation_axes':['snapshot vintage','complete/effort/provisional filters','taxonomy split/lump and crosswalk',
                                  'shared-event deduplication and conflicts','source rounding and presence markers']}
    if not build_path:
        report['frequency_comparison']='not performed: no matching approved EBD/SED snapshot'
        report['synthetic_tests']='separate integration tests; no real EBD denominator/frequency parity claim'
        return report
    build_path=Path(build_path)
    manifest=json.loads((build_path/'manifest.json').read_text())
    report.update(build_identity=manifest['identity'],evidence=manifest['evidence'])
    locations=[p['metadata']['location'] for _,p in baseline]
    if not locations:raise ValueError('No reference locations available')
    with duckdb.connect() as db:
        data=db.execute("SELECT location,native_bin,species_code,sample_size,detections,reporting_frequency FROM read_parquet(?,hive_partitioning=true) WHERE period='multi' AND location IN ("+','.join('?' for _ in locations)+')',
                        [str(build_path/'profiles/**/*.parquet'),*locations]).fetchall()
    by_key={(l,b,s):(n,k,f) for l,b,s,n,k,f in data}
    support={}
    for l,b,s,n,k,f in data:support.setdefault((l,b),set()).add(n)
    for path,p in baseline:
        m=p['metadata'];location=m['location']
        item={'location':location,'reference_sha256':digest(path),'source_sha256':m['source_sha256'],
              'scope':[m['start_year'],m['end_year']],'denominators':[]}
        scope_matches=item['scope']==[manifest['config']['start_year'],manifest['config']['end_year']]
        for index,expected in enumerate(m['sample_sizes'],1):
            counts=support.get((location,index),set())
            if len(counts)>1:raise ValueError('Inconsistent per-species denominators')
            actual=next(iter(counts)) if counts else None
            item['denominators'].append({'native_bin':index,'reference':expected,'actual':actual,
                                         'difference':actual-expected if actual is not None else None})
        matched=scope_matches and all(d['difference']==0 for d in item['denominators'])
        item['denominator_status']='matched' if matched else 'scope_or_support_mismatch'
        item['max_absolute_denominator_difference']=max((abs(d['difference']) for d in item['denominators'] if d['difference'] is not None),default=None)
        if matched:
            differences=[];excluded=0;compared_species=set()
            for row in p['rows']:
                value=row.get('frequency')
                # Native bins are 4 per month; no invented numerator from rounded rate.
                month=int(row['start'][5:7]);day=int(row['start'][8:10]);b=(month-1)*4+min(4,(day-1)//7+1)
                actual=by_key.get((location,b,row['species_code']))
                if value is None or actual is None or actual[2] is None:
                    excluded+=1;continue
                differences.append(abs(actual[2]-value));compared_species.add(row['species_code'])
            item['frequencies']={'compared_cells':len(differences),'compared_species':len(compared_species),'excluded_missing_or_held_cells':excluded,
                                 'max_absolute_difference':max(differences,default=None),
                                 'median_absolute_difference':statistics.median(differences) if differences else None,
                                 'reference_rounding_tolerance':5e-7,'within_rounding_tolerance':sum(d<=5e-7 for d in differences)}
        else:item['frequencies']={'status':'not compared until scope and actual denominators match; investigate first'}
        report['counties'].append(item)
    report['publication_decision']='requires recorded review of discrepancies and coverage; numerical parity is never fabricated'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/phase-eight-validation.json')
    args=parser.parse_args();report=compare(args.build);save(args.output,report)
    print(json.dumps(report,indent=2))
