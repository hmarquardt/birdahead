"""Import owner-supplied eBird exports offline; retain originals, native bins and uncertainty."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re

from tooling.discover import Client, PRIVATE, ROOT, save
from tooling.seasonal import COUNTIES, demonstrate

BIN_DEFINITION = 'ebird-48-month-periods: days 1-7,8-14,15-21,22-month-end'
MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
UNIVERSE = ROOT/'config/geography/teaching-universe.json'


def native_bin(month, period):
    start = date(2001, month, [1,8,15,22][period-1])
    end = date(2001, month, [8,15,22][period-1]) if period < 4 else date(2001 + (month == 12), month % 12 + 1, 1)
    return {'start':start.isoformat(), 'end':end.isoformat(), 'month':month, 'period':period}


def parse_source(path: Path, taxonomy):
    """Validate one native export and expose every uniquely reconciled source taxon.

    Bins are days 1-7, 8-14, 15-21 and 22-month-end; they are not ISO weeks.
    Source bodies do not embed geography, years or a taxonomy release.
    """
    match = re.fullmatch(r'ebird_(US-[A-Z]{2}-\d{3})__(\d{4})_(\d{4})_1_12_barchart.txt', path.name)
    if not match or match[1] not in COUNTIES: raise ValueError('Unrecognized annual county export filename')
    location, start_year, end_year = match.groups()
    if int(start_year) > int(end_year): raise ValueError('Reversed year scope')
    raw = path.read_bytes(); lines = raw.decode('utf-8-sig').splitlines()
    sample_lines = [i for i,line in enumerate(lines) if line.startswith('Sample Size:\t')]
    if len(sample_lines) != 1: raise ValueError('Expected exactly one sample-size row')
    idx = sample_lines[0]

    def fields(line):
        values = line.split('\t')
        if values[-1] == '': values.pop()  # One trailing delimiter, not a missing 48th value.
        if len(values) != 49: raise ValueError('Expected label and 48 native values')
        return values

    months = fields(lines[idx-1])[1:]
    if months != [name if k == 0 else '' for name in MONTHS for k in range(4)]: raise ValueError('Unexpected month/bin header')
    sizes=[]
    for value in fields(lines[idx])[1:]:
        number=float(value)
        if number < 0 or not number.is_integer(): raise ValueError('Invalid sample size')
        sizes.append(int(number))
    data={}
    for line in lines[idx+1:]:
        if not line.strip(): continue
        cells=fields(line); name=cells[0]
        if name in data: raise ValueError('Duplicate source taxon')
        values=[]
        for value in cells[1:]:
            if value.strip() in {'','NA','N/A','null'}: values.append(None); continue
            number=float(value)
            if not 0 <= number <= 1: raise ValueError('Non-fraction frequency')
            values.append(number)
        data[name]=values
    counts=[int(line.split('\t')[1]) for line in lines if line.startswith('Number of taxa:')]
    if counts != [len(data)]: raise ValueError('Declared taxon count differs from parsed rows')
    by_name={}
    for taxon in taxonomy: by_name.setdefault(taxon['comName'],[]).append(taxon)
    matches={name:by_name[name][0] for name in data if len(by_name.get(name,[]))==1}
    mapped={t['speciesCode']:name for name,t in matches.items()}
    return {'location':location,'start_year':int(start_year),'end_year':int(end_year),'raw':raw,
            'sizes':sizes,'data':data,'matches':matches,'mapped':mapped}


def parse_native(path: Path, taxonomy, selected, *, taxonomy_version='2026'):
    """Select a reviewed species list from one validated native export.

    Crosswalks use an exact unique common-name match against the cached target
    authority plus scientific-name agreement. No split/lump concept equivalence
    is inferred, and the source taxonomy release remains explicitly unknown.
    """
    source = parse_source(path, taxonomy)
    location, sizes, data, matches, mapped = (source[key] for key in ['location','sizes','data','matches','mapped'])
    start_year, end_year, raw = source['start_year'], source['end_year'], source['raw']
    rows=[]; anomaly_counts={'possible_presence_marker':0,'nonintegral_detection_count':0,'missing':0}
    for species in selected:
        code=species['ebird_species_code']; name=mapped.get(code)
        if name and matches[name]['sciName'] != species['ebird_scientific_name']: raise ValueError('Selected scientific crosswalk mismatch')
        for index, n in enumerate(sizes):
            value=data[name][index] if name else None
            status='reported_fraction'; source_value=None
            # A literal 0.0015 cannot be an integer numerator for the supplied
            # denominator at this scale. Retain it, but do not rank on it.
            if value is not None:
                numerator=value*n
                # Source values carry up to seven decimals; allow only the error
                # that export rounding can introduce. A literal 0.0015 marker is
                # still incompatible at this scale and remains non-numeric.
                tolerance=max(1e-6,5e-7*n)
                if abs(numerator-round(numerator))>tolerance:
                    status='possible_presence_marker' if abs(value-0.0015)<1e-12 else 'nonintegral_detection_count'
                    anomaly_counts[status]+=1;source_value=value;value=None
            if value is None:
                origin='missing_source_taxon' if name is None else 'missing_or_unknown'
                if name is not None: anomaly_counts['missing']+=1
            elif n==0:
                # Zero support means the frequency is unknown, not an absence.
                status='zero_sample_size';source_value=value;value=None;origin='zero_sample_size'
            else:
                origin='value_at_source_precision'
            bin_value=native_bin(index//4+1,index%4+1)
            rows.append({'species_code':code,'start':bin_value['start'],'end':bin_value['end'],'frequency':value,
                'sample_size':None if n==0 else n,'source_value':source_value,'value_status':status,
                'origin':origin})
    pilot_codes={s['ebird_species_code'] for s in json.loads((ROOT/'experiments/poc-species.json').read_text())}
    metadata={'schema':'birdahead-native-histogram-v1','location':location,'county':COUNTIES[location],
              'source_filename':path.name,'source_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),
              'start_year':start_year,'end_year':end_year,
              'scope_evidence':'Owner supplied download; geography and years encoded in filename, not embedded in body',
              'source_taxonomy_version':None,'taxonomy_version':taxonomy_version,
              'crosswalk':'Exact unique common-name lookup against cached authority, scientific-name agreement with the selected versioned universe; no split/lump inference',
              'units':'fraction_of_complete_checklists','bin_definition':BIN_DEFINITION,
              'missing_semantics':'Missing row/value or zero support => null; suspicious 0.0015/noninteger cells retained raw but excluded from numeric ranking',
              'source_taxa':len(data),'species_name_matches':len(matches),
              'unresolved_or_non_species_taxa':len(data)-len(matches),
              'selected_species':len(selected),
              'selected_species_matched':sum(s['ebird_species_code'] in mapped for s in selected),
              'pilot_species_matched':sum(code in mapped for code in pilot_codes),
              'sample_sizes':sizes,'checklist_total':sum(sizes),'anomalies_selected':anomaly_counts,
              # Retained alias for the original pilot importer contract.
              'anomalies_pilot':anomaly_counts}
    return {'metadata':metadata,'rows':rows}, {'source_names':data,'crosswalk':matches}


def selected_species():
    """Prefer the derived 100-species teaching universe; retain the pilot fallback."""
    if UNIVERSE.exists():
        universe=json.loads(UNIVERSE.read_text())
        if universe.get('schema')!='birdahead-teaching-universe-v1':raise ValueError('Unsupported teaching universe schema')
        return [{**row,'ebird_scientific_name':row['scientific_name']} for row in universe['species']]
    return json.loads((ROOT/'experiments/poc-species.json').read_text())


def run(directory=PRIVATE/'occurrence/incoming'):
    selected=selected_species()
    taxonomy=Client(budget=0).get('https://api.ebird.org/v2/ref/taxonomy/ebird',{'fmt':'json','cat':'species'})
    profiles=[];files=sorted(directory.glob('ebird_*_barchart.txt'))
    if len(files)!=len(COUNTIES): raise ValueError('Exactly seven annual county references required')
    for path in files:
        profile, evidence=parse_native(path,taxonomy,selected)
        location=profile['metadata']['location']
        profiles.append(profile)
        save(PRIVATE/'occurrence/profiles'/f'{location}.json',profile)
        save(PRIVATE/'occurrence/validation'/f'{location}.json',evidence)
    if {p['metadata']['location'] for p in profiles} != set(COUNTIES): raise ValueError('Missing or repeated county')
    demos=demonstrate(profiles)
    save(PRIVATE/'occurrence/seasonal-demonstration.json',demos)
    # Derived, small aggregate report, not redistribution of full raw exports.
    summary={'schema':'birdahead-histogram-validation-v2','source':'Owner-supplied official eBird downloads; eBird/Cornell attribution and terms apply',
             'reference_only':True,'teaching_universe':UNIVERSE.name if UNIVERSE.exists() else 'pilot fallback',
             'selected_species':len(selected),'county_summaries':[p['metadata'] for p in profiles],
             'demonstrations':[],'bulk_aggregation_validated_against_ebd':False}
    names={s['ebird_species_code']:s['common_name'] for s in selected}
    for demo in demos:
        seasons={label:[{**row,'name':names[row['species_code']]} for row in ranking[:8]] for label,ranking in demo['scenarios'].items()}
        # Arriving Soon is its own sort, not a current-frequency shortlist.
        profile=next(p for p in profiles if p['metadata']['location']==demo['location'])
        from tooling.seasonal import rank
        arrivals=sorted(rank(profile,date(2026,4,1)),key=lambda r:-(r['approaching_window_rise'] or 0))[:5]
        summary['demonstrations'].append({'location':demo['location'],'seasons':seasons,
             'april_1_arriving_soon':[{**r,'name':names[r['species_code']]} for r in arrivals]})
    save(ROOT/'experiments/histogram-validation.json',summary)
    print(json.dumps({'counties':len(profiles),'selected_species':len(selected),'species_bin_rows':sum(len(p['rows']) for p in profiles),
                      'source_bytes':sum(p['metadata']['source_bytes'] for p in profiles),
                      'annual_checklist_samples':sum(p['metadata']['checklist_total'] for p in profiles),
                      'private_profiles':'experiments/private/occurrence/profiles'},indent=2))
    return profiles


if __name__=='__main__': run()
