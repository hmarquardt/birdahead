"""Deterministic annual occurrence import/ranking; reporting rates are not encounter probabilities."""
from __future__ import annotations
import argparse
import calendar
import csv
from datetime import date,timedelta
import hashlib
import json
from pathlib import Path
from tooling.discover import ROOT,PRIVATE,save

COUNTIES={'US-IN-051':'Gibson','US-IN-125':'Pike','US-IN-055':'Greene','US-IN-129':'Posey','US-IN-083':'Knox','US-IN-163':'Vanderburgh','US-IN-173':'Warrick'}
SCHEMA='birdahead-occurrence-long-v1'


def md(value):
    try:return date.fromisoformat('2001-'+value)
    except (ValueError,TypeError):raise ValueError('Invalid MM-DD boundary; use non-leap annual template') from None


def parse_long(path,metadata,taxonomy):
    """Explicit normalized interchange, never a guessed interpretation of a source export."""
    required={'schema','source_url','source_sha256','location','start_year','end_year','taxonomy_version','units','bin_definition','missing_semantics'}
    if required-metadata.keys():raise ValueError('Missing occurrence provenance metadata')
    if metadata['schema']!=SCHEMA or metadata['units']!='fraction_of_complete_checklists':raise ValueError('Unsupported schema or frequency units')
    if metadata['start_year']>metadata['end_year']:raise ValueError('Invalid year scope')
    rows=[];seen=set()
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        expected={'species_code','scientific_name','bin_start','bin_end','frequency','sample_size'}
        if not expected.issubset(reader.fieldnames or []):raise ValueError('Missing explicit long-format columns')
        for source in reader:
            code=source['species_code']
            if code not in taxonomy or source['scientific_name']!=taxonomy[code]:raise ValueError('Taxonomy mismatch; supply a reviewed versioned crosswalk')
            start=md(source['bin_start']);end=md(source['bin_end'])
            # 01-01 as the exclusive end of the final bin is the next calendar year.
            if end==date(2001,1,1) and start>end:end=date(2002,1,1)
            if end<=start:raise ValueError('Reversed or empty bin')
            value=source['frequency'].strip();n=source['sample_size'].strip()
            frequency=None if value in {'','NA','N/A','null'} else float(value)
            sample_size=None if n in {'','NA','N/A','null'} else int(n)
            if frequency is not None and not 0<=frequency<=1:raise ValueError('Frequency outside [0,1]; percent data require explicit conversion')
            if sample_size is not None and sample_size<0:raise ValueError('Negative sample size')
            if sample_size==0:
                if frequency not in [None,0.0]:raise ValueError('Positive frequency with zero sample size')
                frequency=None
            key=(code,start.isoformat())
            if key in seen:raise ValueError('Duplicate species/bin')
            seen.add(key);rows.append({'species_code':code,'start':start.isoformat(),'end':end.isoformat(),'frequency':frequency,'sample_size':sample_size})
    if not rows:raise ValueError('Empty occurrence data')
    for code in sorted({r['species_code'] for r in rows}):
        bins=sorted([r for r in rows if r['species_code']==code],key=lambda r:r['start'])
        if bins[0]['start']!='2001-01-01' or bins[-1]['end']!='2002-01-01':raise ValueError('Incomplete annual bin coverage')
        if any(a['end']!=b['start'] for a,b in zip(bins,bins[1:])):raise ValueError('Gap or overlap in annual bins')
    return {'metadata':metadata,'normalized_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':rows}


def rank(profile,when):
    template=date(2001,when.month,min(when.day,calendar.monthrange(2001,when.month)[1]))
    def value_at(rows,day):
        day=date(2001,day.month,min(day.day,calendar.monthrange(2001,day.month)[1]))
        return next((r['frequency'] for r in rows if date.fromisoformat(r['start'])<=day<date.fromisoformat(r['end'])),None)
    ranking=[]
    for code in sorted({r['species_code'] for r in profile['rows']}):
        rows=[r for r in profile['rows'] if r['species_code']==code]
        current=value_at(rows,template)
        future=[value_at(rows,template+timedelta(days=offset)) for offset in [14,21,28]]
        supported_future=[v for v in future if v is not None]
        peak=max(supported_future) if supported_future else None
        # Arrival priority is evaluated even when current reporting frequency is zero.
        arrival=max(0,peak-current) if peak is not None and current is not None else None
        ranking.append({'species_code':code,'current_reporting_frequency':current,'future_14_28_day_max':peak,
            'approaching_window_rise':arrival,'learning_priority':round(.6*current+.4*arrival,8) if current is not None and arrival is not None else None,
            'support':'sample sizes unknown' if all(r['sample_size'] is None for r in rows) else 'sample sizes retained',
            'meaning':'relative curriculum priority, not absolute encounter probability'})
    return sorted(ranking,key=lambda r:((r['learning_priority'] is None),-(r['learning_priority'] or 0),r['species_code']))


def demonstrate(profiles):
    scopes={(p['metadata']['start_year'],p['metadata']['end_year'],p['metadata']['taxonomy_version'],p['metadata']['units'],p['metadata']['bin_definition']) for p in profiles}
    if len(scopes)!=1:raise ValueError('Inconsistent annual export scope/bin definitions')
    output=[]
    for profile in profiles:
        scenarios={label:rank(profile,date.fromisoformat(day)) for label,day in {
            'winter':'2026-01-15','spring_migration':'2026-05-05','summer':'2026-07-15','fall_migration':'2026-09-10'}.items()}
        output.append({'location':profile['metadata']['location'],'source_sha256':profile['metadata']['source_sha256'],'scenarios':scenarios})
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['status','demo']);parser.add_argument('--directory',type=Path,default=PRIVATE/'occurrence/normalized')
    args=parser.parse_args()
    if args.command=='status':
        incoming=PRIVATE/'occurrence/incoming'
        print(json.dumps({'expected_counties':COUNTIES,'incoming_files':[p.name for p in incoming.glob('*') if p.is_file()],'instructions':'docs/manual-downloads.md'},indent=2));return
    selection=json.loads((ROOT/'experiments/poc-species.json').read_text());tax={r['ebird_species_code']:r['scientific_name'] for r in selection}
    profiles=[]
    for location in COUNTIES:
        path=args.directory/(location+'.csv');meta=args.directory/(location+'.json')
        if not path.exists() or not meta.exists():raise SystemExit('Annual data unavailable for '+location+'; follow docs/manual-downloads.md. No synthetic demonstration generated.')
        profiles.append(parse_long(path,json.loads(meta.read_text()),tax))
    save(PRIVATE/'occurrence/seasonal-demonstration.json',demonstrate(profiles));print('Saved seven-county actual-data demonstration in private occurrence storage')


if __name__=='__main__':main()
