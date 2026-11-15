"""Bounded EBD/SED denominator kernel. No downloader; real bulk-snapshot parity remains unmeasured."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import duckdb
from tooling.discover import PRIVATE, ROOT, save
from tooling.histograms import BIN_DEFINITION

SED_COLUMNS={'SAMPLING EVENT IDENTIFIER','GROUP IDENTIFIER','ALL SPECIES REPORTED','OBSERVATION DATE','COUNTY CODE','LOCALITY ID'}
EBD_COLUMNS={'SAMPLING EVENT IDENTIFIER','SCIENTIFIC NAME','OBSERVATION COUNT','APPROVED'}


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def aggregate(ebd,sed,crosswalk,config,output,*,max_bytes=50_000_000):
    """Require approved source files and an explicit concept crosswalk; keep private Parquet output.

    Initial supported geometry is source county codes/hotspot IDs. Polygon support remains a
    planned spatial adapter, not a falsely precise point-in-polygon implementation here.
    """
    ebd,sed,crosswalk,output=map(Path,[ebd,sed,crosswalk,output])
    if sum(p.stat().st_size for p in [ebd,sed])>max_bytes:raise ValueError('Input exceeds bounded experiment ceiling; perform source-size/access preflight first')
    required={'snapshot','source_taxonomy_version','target_taxonomy_version','start_year','end_year','locations','crosswalk_review_status','source_coverage'}
    if required-config.keys() or config['crosswalk_review_status']!='reviewed':raise ValueError('Explicit source scope and reviewed taxonomy crosswalk required')
    if any(not config[k] for k in ['snapshot','source_taxonomy_version','target_taxonomy_version']):raise ValueError('Pinned source and taxonomy versions required')
    if not isinstance(config['start_year'],int) or not isinstance(config['end_year'],int) or config['start_year']>config['end_year']:raise ValueError('Invalid historical year scope')
    if config['source_coverage']!='all_taxa_and_complete_checklists':raise ValueError('Species-conditioned checklist populations are not supported')
    locations=config['locations']
    if not locations or any(l.get('kind') not in {'county','hotspot'} or not l.get('id') or not l.get('source_id') for l in locations):raise ValueError('Kernel currently supports explicit county and hotspot IDs only; polygon adapter unvalidated')
    if len({l['id'] for l in locations})!=len(locations):raise ValueError('Duplicate location identifier')
    output.mkdir(parents=True,exist_ok=True)
    if (output/'manifest.json').exists():raise ValueError('Immutable output already exists; use a new release directory')
    db=duckdb.connect();start=time.monotonic()
    try:
        db.execute("SET memory_limit='1GB'");db.execute('SET threads=2');db.execute("SET temp_directory=?",[str(output/'spill')])
        for table,path,expected in [('sed_raw',sed,SED_COLUMNS),('ebd_raw',ebd,EBD_COLUMNS)]:
            db.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, delim='\t',header=true,all_varchar=true)",[str(path)])
            columns={r[0] for r in db.execute(f'DESCRIBE {table}').fetchall()}
            if expected-columns:raise ValueError('Source header missing required '+table+' columns')
        if db.execute('SELECT count(*) FROM sed_raw WHERE "SAMPLING EVENT IDENTIFIER" IS NULL').fetchone()[0]:raise ValueError('Missing sampling-event ID')
        if db.execute('''SELECT count(*) FROM sed_raw WHERE "ALL SPECIES REPORTED" IS NULL OR lower("ALL SPECIES REPORTED") NOT IN ('1','true','t','0','false','f')''').fetchone()[0]:raise ValueError('Unknown checklist completeness value')
        db.execute('CREATE TABLE crosswalk AS SELECT * FROM read_csv(?,header=true,all_varchar=true)',[str(crosswalk)])
        if not {'scientific_name','species_code'}<={r[0] for r in db.execute('DESCRIBE crosswalk').fetchall()}:raise ValueError('Crosswalk requires scientific_name and species_code')
        if db.execute('SELECT scientific_name FROM crosswalk GROUP BY 1 HAVING count(*)>1').fetchall():raise ValueError('Ambiguous source taxon crosswalk')
        if db.execute('SELECT count(*) FROM crosswalk WHERE scientific_name IS NULL OR species_code IS NULL').fetchone()[0]:raise ValueError('Null crosswalk concepts')
        # Avoid arbitrary member selection. Conflicting repeated IDs or shared events are held.
        db.execute('''CREATE TABLE members AS SELECT DISTINCT "SAMPLING EVENT IDENTIFIER" AS checklist_id,
          CASE WHEN nullif("GROUP IDENTIFIER",'') IS NOT NULL THEN 'group:'||"GROUP IDENTIFIER" ELSE 'event:'||"SAMPLING EVENT IDENTIFIER" END AS event_id,
          lower("ALL SPECIES REPORTED") IN ('1','true','t') AS complete,
          try_cast("OBSERVATION DATE" AS DATE) AS day,"COUNTY CODE" AS county,"LOCALITY ID" AS hotspot FROM sed_raw''')
        if db.execute('SELECT checklist_id FROM members GROUP BY 1 HAVING count(*)>1').fetchall():raise ValueError('Conflicting repeated sampling-event ID')
        if db.execute('SELECT count(*) FROM members WHERE day IS NULL OR complete IS NULL OR county IS NULL').fetchone()[0]:raise ValueError('Unparseable checklist date/completeness/geography')
        db.execute('''CREATE TABLE valid_groups AS SELECT event_id FROM members GROUP BY event_id
          HAVING bool_and(complete) AND count(DISTINCT day)=1 AND count(DISTINCT county)=1
          AND count(DISTINCT coalesce(hotspot,''))=1''')
        db.execute('''CREATE TABLE events AS SELECT m.event_id,min(day) AS day,min(county) AS county,min(hotspot) AS hotspot,
          year(min(day))::INTEGER AS year,split_part(min(county),'-',1)||'-'||split_part(min(county),'-',2) AS state,
          ((month(min(day))-1)*4+least(4,((day(min(day))-1)//7)+1))::INTEGER AS native_bin,
          count(*)::INTEGER AS contributing_checklists FROM members m JOIN valid_groups USING(event_id)
          WHERE year(day) BETWEEN ? AND ? GROUP BY m.event_id''',[config['start_year'],config['end_year']])
        # All approved taxa remain upstream. Crosswalk selects teachable species only after SED denominator creation.
        db.execute('''CREATE TABLE detections AS SELECT DISTINCT m.event_id,c.species_code
          FROM ebd_raw b JOIN members m ON b."SAMPLING EVENT IDENTIFIER"=m.checklist_id JOIN events e USING(event_id)
          JOIN crosswalk c ON b."SCIENTIFIC NAME"=c.scientific_name
          WHERE lower(b."APPROVED") IN ('1','true','t') AND (b."OBSERVATION COUNT"='X' OR try_cast(b."OBSERVATION COUNT" AS DOUBLE)>0)''')
        db.execute('CREATE TABLE location_members(location VARCHAR,event_id VARCHAR)')
        for location in locations:
            column='county' if location['kind']=='county' else 'hotspot'
            db.execute(f'INSERT INTO location_members SELECT ?,event_id FROM events WHERE {column}=?',[location['id'],location['source_id']])
        db.execute('CREATE TABLE locations(id VARCHAR)');db.executemany('INSERT INTO locations VALUES(?)',[(l['id'],) for l in locations])
        db.execute('''CREATE TABLE profiles AS WITH n AS (
          SELECT l.location,e.native_bin,count(*) AS sample_size FROM location_members l JOIN events e USING(event_id) GROUP BY 1,2),
          k AS (SELECT l.location,e.native_bin,d.species_code,count(*) AS detections FROM location_members l JOIN events e USING(event_id)
          JOIN detections d USING(event_id) GROUP BY 1,2,3)
          SELECT loc.id AS location,s.species_code,b.range::INTEGER AS native_bin,
          coalesce(n.sample_size,0)::BIGINT AS sample_size,coalesce(k.detections,0)::BIGINT AS detections,
          CASE WHEN coalesce(n.sample_size,0)=0 THEN NULL ELSE coalesce(k.detections,0)::DOUBLE/n.sample_size END AS reporting_frequency,
          CASE WHEN coalesce(n.sample_size,0)=0 THEN 'no_eligible_events' ELSE 'supported' END AS value_status
          FROM locations loc CROSS JOIN (SELECT DISTINCT species_code FROM crosswalk) s CROSS JOIN range(1,49) b
          LEFT JOIN n ON n.location=loc.id AND n.native_bin=b.range LEFT JOIN k ON k.location=loc.id AND k.native_bin=b.range AND k.species_code=s.species_code
          ORDER BY location,species_code,native_bin''')
        for table in ['events','detections','profiles']:
            target=output/table
            if table=='events':db.execute('COPY events TO ? (FORMAT PARQUET,PARTITION_BY(year,state),COMPRESSION ZSTD)',[str(target)])
            else:db.execute(f'COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)',[str(target)+'.parquet'])
        metrics={'eligible_events':db.execute('SELECT count(*) FROM events').fetchone()[0],
                 'selected_species_detections':db.execute('SELECT count(*) FROM detections').fetchone()[0],
                 'profile_rows':db.execute('SELECT count(*) FROM profiles').fetchone()[0],
                 'source_checklist_rows':db.execute('SELECT count(*) FROM sed_raw').fetchone()[0],
                 'shared_or_incomplete_groups_excluded':db.execute('SELECT count(DISTINCT event_id) FROM members WHERE event_id NOT IN (SELECT event_id FROM valid_groups)').fetchone()[0],
                 'orphan_observation_rows':db.execute('SELECT count(*) FROM ebd_raw b LEFT JOIN members m ON b."SAMPLING EVENT IDENTIFIER"=m.checklist_id WHERE m.checklist_id IS NULL').fetchone()[0]}
        manifest={'schema':'birdahead-checklist-kernel-v1','config':config,'bin_definition':BIN_DEFINITION,
                  'inputs':{name:sha(path) for name,path in [('ebd',ebd),('sed',sed),('crosswalk',crosswalk)]},
                  'duckdb_version':duckdb.__version__,'metrics':metrics,'limitations':'Bounded county/hotspot kernel, not full production adapter; no effort standardization or spatial polygon support',
                  'seconds':round(time.monotonic()-start,4)}
        save(output/'manifest.json',manifest)
        return manifest
    finally:db.close()


def histogram_parquet_benchmark():
    """Measure only tiny real bootstrap data; never extrapolate a bulk throughput claim."""
    rows=[]
    for path in sorted((PRIVATE/'occurrence/profiles').glob('*.json')):
        profile=json.loads(path.read_text())
        rows.extend({**r,'location':profile['metadata']['location']} for r in profile['rows'])
    path=PRIVATE/'geography/bootstrap';path.mkdir(parents=True,exist_ok=True)
    source=path/'rows.json';save(source,rows)
    db=duckdb.connect();start=time.monotonic()
    try:
        db.execute('CREATE TABLE bootstrap AS SELECT * FROM read_json_auto(?)',[str(source)])
        db.execute('COPY bootstrap TO ? (FORMAT PARQUET,PARTITION_BY(location),COMPRESSION ZSTD,OVERWRITE_OR_IGNORE)',[str(path/'parquet')])
        count=db.execute('SELECT count(*) FROM read_parquet(?)',[str(path/'parquet/**/*.parquet')]).fetchone()[0]
        assert count==len(rows)
        stats={'scope':'Actual imported histogram rows only; not an EBD throughput benchmark','duckdb_version':duckdb.__version__,
               'rows':count,'input_json_bytes':source.stat().st_size,'partitioned_parquet_bytes':sum(p.stat().st_size for p in (path/'parquet').rglob('*.parquet')),
               'seconds':round(time.monotonic()-start,4),'ebd_histogram_parity_measured':False}
        save(ROOT/'experiments/duckdb-validation.json',stats);print(json.dumps(stats,indent=2))
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['bootstrap-benchmark','aggregate']);parser.add_argument('--ebd',type=Path);parser.add_argument('--sed',type=Path);parser.add_argument('--crosswalk',type=Path);parser.add_argument('--config',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='bootstrap-benchmark':histogram_parquet_benchmark()
    else:
        if not all([args.ebd,args.sed,args.crosswalk,args.config,args.output]):parser.error('aggregate requires explicit private inputs/config/output')
        if not args.output.resolve().is_relative_to(PRIVATE.resolve()):parser.error('Raw derived output must remain in ignored private storage')
        print(json.dumps(aggregate(args.ebd,args.sed,args.crosswalk,json.loads(args.config.read_text()),args.output)['metrics'],indent=2))
