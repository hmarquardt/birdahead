"""Reproducible regional EBD/SED processing; raw and intermediate data stay private.

Full snapshots replace, never append. Content-addressed normalization is reusable across
geography/filter builds; source, schema or taxonomy changes invalidate it automatically.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import duckdb
from shapely import contains_xy
from shapely.geometry import shape

from tooling.discover import PRIVATE, ROOT, save
from tooling.geography_io import Limits, digest, private_path
from tooling.histograms import BIN_DEFINITION

ENGINE = 'birdahead-geographic-engine-v1'
SCHEMAS = {
    'sed': ['SAMPLING EVENT IDENTIFIER','GROUP IDENTIFIER','ALL SPECIES REPORTED','OBSERVATION DATE',
            'STATE CODE','COUNTY CODE','LOCALITY ID','LATITUDE','LONGITUDE','PROTOCOL CODE',
            'DURATION MINUTES','EFFORT DISTANCE KM','NUMBER OBSERVERS'],
    'ebd': ['SAMPLING EVENT IDENTIFIER','SCIENTIFIC NAME','OBSERVATION COUNT','APPROVED'],
}
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$')


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def sql_name(name):
    return '"'+name.replace('"','""')+'"'


def sql_string(value):
    return "'"+str(value).replace("'","''")+"'"


def validate_snapshot(manifest, base, limits):
    required = ['snapshot_id','source_taxonomy_version','target_taxonomy_version','grant_reference',
                'terms_url','intended_use','states','source_scope','start_year','end_year','artifacts','all_species','all_months']
    if any(not manifest.get(k) for k in required):
        raise ValueError('Pinned snapshot, scope, terms and private grant evidence required')
    if manifest['all_species'] is not True or manifest['all_months'] is not True:
        raise ValueError('All-species, all-months coherent EBD and SED required')
    if not manifest['states'] or len(manifest['states']) != len(set(manifest['states'])) or any(not re.fullmatch(r'US-[A-Z]{2}',s) for s in manifest['states']):
        raise ValueError('Explicit regional state coverage required; worldwide inputs are unsupported')
    if not (1900 <= manifest['start_year'] <= manifest['end_year'] <= 2100):
        raise ValueError('Invalid snapshot years')
    scope=manifest['source_scope']
    if scope.get('kind') not in ['states','counties'] or not scope.get('ids'):
        raise ValueError('Explicit complete state or county extract coverage required')
    if scope['kind']=='states' and set(scope['ids'])!=set(manifest['states']):
        raise ValueError('State scope must match the declared source states')
    if scope['kind']=='counties' and not all(any(c.startswith(s+'-') for s in manifest['states']) for c in scope['ids']):
        raise ValueError('County scope inconsistent with source states')
    paths = {}
    declared = [manifest['artifacts'][kind]['bytes'] for kind in ['ebd','sed','crosswalk']]
    if any(not isinstance(n,int) or n<=0 for n in declared) or sum(declared)>limits.max_input_bytes:
        raise ValueError('Combined input ceiling exceeded before hashing/scanning')
    for kind in ['ebd','sed','crosswalk']:
        a = manifest['artifacts'][kind]
        p = (base/a['path']).resolve()
        if not p.is_relative_to(PRIVATE.resolve()):
            raise ValueError('Raw sources must stay in private storage')
        if a['snapshot_id'] != manifest['snapshot_id']:
            raise ValueError('EBD/SED/crosswalk must refer to the same snapshot')
        if a['bytes'] != p.stat().st_size or a['bytes'] > limits.max_input_bytes or digest(p) != a['sha256']:
            raise ValueError('Source size/checksum gate failed')
        paths[kind]=p
    if sum(p.stat().st_size for p in paths.values()) > limits.max_input_bytes:
        raise ValueError('Combined input ceiling exceeded')
    return paths


def connection(directory, limits):
    limits.check_disk(directory, limits.max_spill_bytes)
    db = duckdb.connect(str(directory/'processing.duckdb'))
    db.execute(f"SET memory_limit='{limits.memory_mb}MB'")
    db.execute(f'SET threads={limits.threads}')
    db.execute('SET preserve_insertion_order=false')
    db.execute('SET temp_directory=?',[str(directory/'spill')])
    db.execute(f"SET max_temp_directory_size='{limits.max_spill_bytes}B'")
    return db


def source_view(db, kind, path):
    # Validate the actual header independently of DuckDB inference. Read all as strings,
    # project required fields; parsing/conversion is explicit and malformed rows fail closed.
    with path.open(encoding='utf-8-sig',newline='') as stream:
        header=next(csv.reader(stream,delimiter='\t'))
    if len(header)!=len(set(header)) or set(SCHEMAS[kind])-set(header):
        raise ValueError(f'{kind} header missing/duplicate required columns')
    columns=', '.join(f'{sql_string(h)}: \'VARCHAR\'' for h in header)
    select=', '.join(sql_name(h) for h in SCHEMAS[kind])
    db.execute(f'''CREATE VIEW {kind}_raw AS SELECT {select} FROM read_csv(
        {sql_string(path)}, delim='\t',header=true,columns={{{columns}}},quote='',escape='',strict_mode=true)''')


def normalize(snapshot, paths, root, limits):
    # Include executable content and lock digest; reusing a snapshot cannot bypass code fixes.
    key=identity({'engine':ENGINE,'engine_sha256':digest(Path(__file__)),
                  'lock_sha256':digest(ROOT/'uv.lock'),'snapshot':snapshot,'schemas':SCHEMAS})
    destination=root/'normalized'/key
    if (destination/'manifest.json').exists():
        manifest=json.loads((destination/'manifest.json').read_text())
        if all((destination/p).is_file() and digest(destination/p)==h for p,h in manifest['outputs'].items()):
            return destination, manifest, True
        raise ValueError('Cached partition integrity failed')
    private_path(destination.parent)
    stage=Path(tempfile.mkdtemp(prefix='normalize-',dir=root))
    db=connection(stage,limits)
    try:
        for kind in SCHEMAS:
            source_view(db,kind,paths[kind])
        # Store only selected typed columns; raw observations are not loaded into Python.
        db.execute('''CREATE TABLE members AS SELECT DISTINCT
            "SAMPLING EVENT IDENTIFIER" checklist_id,
            CASE WHEN nullif("GROUP IDENTIFIER",'') IS NULL THEN 'event:'||"SAMPLING EVENT IDENTIFIER"
                 ELSE 'group:'||"GROUP IDENTIFIER" END event_id,
            CASE lower("ALL SPECIES REPORTED") WHEN '1' THEN true WHEN 'true' THEN true
                 WHEN '0' THEN false WHEN 'false' THEN false ELSE NULL END complete,
            try_cast("OBSERVATION DATE" AS DATE) AS day, "STATE CODE" state,
            "COUNTY CODE" county, "LOCALITY ID" hotspot,
            try_cast("LATITUDE" AS DOUBLE) latitude, try_cast("LONGITUDE" AS DOUBLE) longitude,
            "PROTOCOL CODE" protocol, try_cast("DURATION MINUTES" AS DOUBLE) duration,
            try_cast("EFFORT DISTANCE KM" AS DOUBLE) distance, try_cast("NUMBER OBSERVERS" AS INTEGER) observers
            FROM sed_raw''')
        if db.execute('''SELECT count(*) FROM members WHERE checklist_id IS NULL OR complete IS NULL OR day IS NULL
            OR state IS NULL OR county IS NULL OR NOT isfinite(latitude) OR NOT isfinite(longitude)
            OR latitude IS NULL OR longitude IS NULL OR latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180''').fetchone()[0]:
            raise ValueError('Invalid checklist identity, date, completeness or coordinates')
        if db.execute('SELECT count(*) FROM (SELECT checklist_id FROM members GROUP BY 1 HAVING count(*)>1)').fetchone()[0]:
            raise ValueError('Conflicting checklist identities')
        state_list=','.join(sql_string(s) for s in snapshot['states'])
        if db.execute(f'''SELECT count(*) FROM members WHERE state NOT IN ({state_list})
            OR year(day) NOT BETWEEN {int(snapshot['start_year'])} AND {int(snapshot['end_year'])}
            OR NOT starts_with(county,state||'-')''').fetchone()[0]:
            raise ValueError('SED exceeds declared snapshot coverage')
        if snapshot['source_scope']['kind']=='counties':
            counties=','.join(sql_string(c) for c in snapshot['source_scope']['ids'])
            if db.execute(f'SELECT count(*) FROM members WHERE county NOT IN ({counties})').fetchone()[0]:
                raise ValueError('SED exceeds declared county coverage')
        # Hold every member of conflicting shared groups. Both numerator and denominator use
        # this exact population. Union detections across agreeing shared members once.
        db.execute('''CREATE TABLE eligible_groups AS SELECT event_id FROM members GROUP BY event_id
            HAVING bool_and(complete) AND count(DISTINCT day)=1 AND count(DISTINCT state)=1
            AND count(DISTINCT county)=1 AND count(DISTINCT coalesce(hotspot,''))=1
            AND count(DISTINCT latitude)=1 AND count(DISTINCT longitude)=1
            AND count(DISTINCT coalesce(protocol,''))=1
            AND count(DISTINCT coalesce(duration,-1))=1 AND count(DISTINCT coalesce(distance,-1))=1
            AND count(DISTINCT coalesce(observers,-1))=1''')
        db.execute('''CREATE TABLE events AS SELECT event_id, min(day) AS day, year(min(day))::INTEGER AS year,
            min(state) state,min(county) county,min(hotspot) hotspot,min(latitude) latitude,min(longitude) longitude,
            min(protocol) protocol,min(duration) duration,min(distance) distance,min(observers) observers,
            ((month(min(day))-1)*4+least(4,((day(min(day))-1)//7)+1))::INTEGER native_bin,
            count(*)::INTEGER contributing_checklists FROM members JOIN eligible_groups USING(event_id) GROUP BY event_id''')
        with paths['crosswalk'].open(newline='') as stream:
            mappings=list(csv.DictReader(stream))
        if not mappings or any(not r.get('scientific_name') or r.get('decision') not in ['accepted','unresolved','excluded']
                               or (r['decision']=='accepted' and (not SAFE_ID.fullmatch(r.get('species_code','')) or not r.get('rationale'))) for r in mappings):
            raise ValueError('Crosswalk needs explicit accepted/unresolved/excluded decisions and accepted rationale')
        if len({r['scientific_name'] for r in mappings}) != len(mappings):
            raise ValueError('Ambiguous taxonomy concept crosswalk')
        db.execute('CREATE TABLE crosswalk(scientific_name VARCHAR,species_code VARCHAR,decision VARCHAR,rationale VARCHAR)')
        db.executemany('INSERT INTO crosswalk VALUES(?,?,?,?)',[(r['scientific_name'],r.get('species_code') or None,r['decision'],r.get('rationale')) for r in mappings])
        # Reject invalid quality/count fields rather than quietly treating corrupted observations as absence.
        if db.execute('''SELECT count(*) FROM ebd_raw WHERE "SAMPLING EVENT IDENTIFIER" IS NULL OR "SCIENTIFIC NAME" IS NULL
            OR "APPROVED" IS NULL OR lower("APPROVED") NOT IN ('0','1','false','true')
            OR (upper("OBSERVATION COUNT") IS DISTINCT FROM 'X' AND
                (try_cast("OBSERVATION COUNT" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("OBSERVATION COUNT" AS DOUBLE))
                 OR try_cast("OBSERVATION COUNT" AS DOUBLE)<0))''').fetchone()[0]:
            raise ValueError('Invalid observation identity, count or approval')
        orphans=db.execute('''SELECT count(*) FROM ebd_raw b LEFT JOIN members m ON b."SAMPLING EVENT IDENTIFIER"=m.checklist_id
            WHERE m.checklist_id IS NULL''').fetchone()[0]
        if orphans:
            raise ValueError('EBD contains events absent from matching SED')
        db.execute('''CREATE TABLE detections AS SELECT DISTINCT e.event_id,e.year,e.state,c.species_code
            FROM ebd_raw b JOIN members m ON b."SAMPLING EVENT IDENTIFIER"=m.checklist_id
            JOIN events e USING(event_id) JOIN crosswalk c ON b."SCIENTIFIC NAME"=c.scientific_name
            WHERE lower(b."APPROVED") IN ('1','true') AND c.decision='accepted'
            AND (upper(b."OBSERVATION COUNT")='X' OR try_cast(b."OBSERVATION COUNT" AS DOUBLE)>0)''')
        db.execute('''CREATE TABLE taxonomy_holds AS SELECT b."SCIENTIFIC NAME" scientific_name,
            coalesce(c.decision,'unmapped') decision,count(*) observations FROM ebd_raw b
            LEFT JOIN crosswalk c ON b."SCIENTIFIC NAME"=c.scientific_name
            WHERE c.decision IS DISTINCT FROM 'accepted' GROUP BY 1,2''')
        metrics={table:db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ['members','events','detections','taxonomy_holds']}
        metrics['excluded_groups']=db.execute('SELECT count(DISTINCT event_id) FROM members WHERE event_id NOT IN (SELECT event_id FROM eligible_groups)').fetchone()[0]
        # Parallel scans/joins; one deterministic writer per partition.
        db.execute('SET threads=1')
        for table in ['events','detections']:
            order='state,year,event_id'+(',species_code' if table=='detections' else '')
            db.execute(f'COPY (SELECT * FROM {table} ORDER BY {order}) TO ? (FORMAT PARQUET,PARTITION_BY(state,year),COMPRESSION ZSTD)',[str(stage/table)])
            # Empty tables have no partition files: an explicit typed empty artifact keeps rebuilds valid.
            if not list((stage/table).rglob('*.parquet')):
                db.execute(f'COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)',[str(stage/table/'empty.parquet')])
        for table in ['crosswalk','taxonomy_holds']:
            db.execute(f'COPY (SELECT * FROM {table} ORDER BY scientific_name) TO ? (FORMAT PARQUET,COMPRESSION ZSTD)',[str(stage/(table+'.parquet'))])
        db.close();db=None
        (stage/'processing.duckdb').unlink()
        shutil.rmtree(stage/'spill',ignore_errors=True)
        outputs={str(p.relative_to(stage)):digest(p) for p in sorted(stage.rglob('*.parquet'))}
        # Replacement snapshots still get a full authoritative scan (including deletions).
        # Identical normalized partitions share immutable storage across snapshot versions.
        objects=private_path(root/'partition-objects')
        for relative,h in outputs.items():
            partition=stage/relative;canonical=objects/(h+'.parquet')
            if canonical.exists():
                if digest(canonical)!=h:raise ValueError('Partition store integrity failed')
                partition.unlink();os.link(canonical,partition)
            else:os.link(partition,canonical)
        result={'schema':ENGINE,'identity':key,'snapshot':snapshot,'source_schemas':SCHEMAS,'metrics':metrics,
                'duckdb_version':duckdb.__version__,'outputs':outputs}
        save(stage/'manifest.json',result)
        stage.replace(destination)
        return destination,result,False
    finally:
        if db:db.close()
        if stage.exists():shutil.rmtree(stage)


def validate_regions(config, snapshot):
    locations=config['locations']
    ids={l['id'] for l in locations}
    if len(ids)!=len(locations) or not ids or any(not SAFE_ID.fullmatch(i) for i in ids):
        raise ValueError('Unique safe region IDs required')
    if not (snapshot['start_year'] <= config['start_year'] <= config['end_year'] <= snapshot['end_year']):
        raise ValueError('Requested years outside snapshot')
    if not isinstance(config['minimum_support'],int) or config['minimum_support']<1:
        raise ValueError('Positive minimum support required')
    for loc in locations:
        if loc.get('kind') not in ['state','county','hotspot','cell','region','park','refuge','destination']:
            raise ValueError('Unsupported geographic kind')
        if not loc.get('coverage_states') or not set(loc['coverage_states']) <= set(snapshot['states']):
            raise ValueError('Region coverage not supported by source snapshot')
        selector=loc['selector']
        scope=snapshot['source_scope']
        if scope['kind']=='counties':
            if selector['type']=='state':raise ValueError('County extract cannot supply a complete state profile')
            requested=selector.get('ids') if selector['type']=='county' else loc.get('coverage_counties')
            if not requested or not set(requested)<=set(scope['ids']):
                raise ValueError('Destination requires explicit coverage inside the county extract')
        if selector['type'] not in ['state','county','hotspot','bbox','polygon']:
            raise ValueError('Unsupported geographic selector')
        if selector['type'] in ['state','county','hotspot'] and not selector.get('ids'):
            raise ValueError('Source IDs required')
        if selector['type']=='state' and not set(selector['ids'])<=set(loc['coverage_states']):
            raise ValueError('State selector outside region coverage')
        if selector['type']=='county' and not all(any(c.startswith(s+'-') for s in loc['coverage_states']) for c in selector['ids']):
            raise ValueError('County selector outside region coverage')
        if selector['type']=='bbox':
            w,s,e,n=selector['bounds']
            if not (-180<=w<e<=180 and -90<=s<n<=90):raise ValueError('Invalid coarse cell bounds')
        if selector['type']=='polygon':
            boundary=selector['boundary']
            if boundary.get('crs')!='EPSG:4326' or any(not boundary.get(k) for k in ['source_url','license','sha256','geometry']):
                raise ValueError('Pinned licensed WGS84 boundary required')
            if identity(boundary['geometry'])!=boundary['sha256']:
                raise ValueError('Boundary checksum mismatch')
            geometry=shape(boundary['geometry'])
            if not geometry.is_valid or geometry.is_empty or geometry.geom_type not in ['Polygon','MultiPolygon']:
                raise ValueError('Invalid destination polygon')
        seen={loc['id']};parent=loc.get('parent')
        while parent:
            if parent not in ids or parent in seen:raise ValueError('Unknown/cyclic fallback parent')
            seen.add(parent);parent=next(l for l in locations if l['id']==parent).get('parent')


def build(snapshot_path, config_path, output_root, limits=Limits()):
    snapshot_path,config_path=Path(snapshot_path),Path(config_path)
    snapshot=json.loads(snapshot_path.read_text()); config=json.loads(config_path.read_text())
    root=private_path(output_root)
    paths=validate_snapshot(snapshot,snapshot_path.parent,limits)
    limits.check_disk(root,3*sum(p.stat().st_size for p in paths.values())+limits.max_spill_bytes)
    validate_regions(config,snapshot)
    normalized,norm,reused=normalize(snapshot,paths,root,limits)
    key=identity({'normalized':norm['identity'],'config':config})
    destination=root/'builds'/key
    if (destination/'manifest.json').exists():
        manifest=json.loads((destination/'manifest.json').read_text())
        if any(digest(destination/p)!=h for p,h in manifest['outputs'].items()):
            raise ValueError('Build artifact integrity failed')
        return destination,manifest,True
    private_path(destination.parent)
    stage=Path(tempfile.mkdtemp(prefix='aggregate-',dir=root));db=connection(stage,limits)
    try:
        db.execute(f"CREATE VIEW all_events AS SELECT * FROM read_parquet({sql_string(normalized/'events/**/*.parquet')},hive_partitioning=true)")
        effort=config.get('effort',{})
        allowed={'protocols','max_duration_minutes','max_distance_km','max_observers'}
        if set(effort)-allowed:raise ValueError('Unknown effort filter')
        clauses=[f"year BETWEEN {int(config['start_year'])} AND {int(config['end_year'])}"]
        if effort.get('protocols'):clauses.append('protocol IN ('+','.join(sql_string(p) for p in effort['protocols'])+')')
        for k,col in [('max_duration_minutes','duration'),('max_distance_km','distance'),('max_observers','observers')]:
            if k in effort:
                if not isinstance(effort[k],(float,int)) or effort[k]<0:raise ValueError('Invalid effort ceiling')
                clauses.append(f'{col} BETWEEN 0 AND {float(effort[k])}')
        db.execute('CREATE VIEW events AS SELECT * FROM all_events WHERE '+' AND '.join(clauses))
        db.execute(f"CREATE VIEW detections AS SELECT * FROM read_parquet({sql_string(normalized/'detections/**/*.parquet')},hive_partitioning=true)")
        db.execute(f"CREATE VIEW species AS SELECT DISTINCT species_code FROM read_parquet({sql_string(normalized/'crosswalk.parquet')}) WHERE decision='accepted'")
        db.execute('CREATE TABLE membership(location VARCHAR,event_id VARCHAR)')
        for index,loc in enumerate(config['locations']):
            selector=loc['selector'];kind=selector['type']
            coverage='state IN ('+','.join(sql_string(s) for s in loc['coverage_states'])+')'
            if kind in ['state','county','hotspot']:
                clause=kind+' IN ('+','.join(sql_string(v) for v in selector['ids'])+')'
            else:
                if kind=='polygon':
                    geom=shape(selector['boundary']['geometry']);bounds=geom.bounds
                    name=f'point_in_region_{index}'
                    def predicate(geometry):
                        def inside(x,y):return bool(contains_xy(geometry,x,y))
                        return inside
                    db.create_function(name,predicate(geom),['DOUBLE','DOUBLE'],'BOOLEAN')
                    # contains excludes boundary points, pinned as the inclusion rule.
                    clause=f'{name}(longitude,latitude)'
                else:bounds=selector['bounds'];clause='true'
                w,s,e,n=bounds
                clause+=f' AND longitude>={float(w)} AND longitude<{float(e)} AND latitude>={float(s)} AND latitude<{float(n)}'
            db.execute(f'INSERT INTO membership SELECT ?,event_id FROM events WHERE {coverage} AND ({clause})',[loc['id']])
        db.execute('CREATE TABLE locations(location VARCHAR)');db.executemany('INSERT INTO locations VALUES(?)',[(l['id'],) for l in config['locations']])
        db.execute('CREATE TABLE periods(period VARCHAR,start_year INTEGER,end_year INTEGER)')
        periods=[(str(y),y,y) for y in range(config['start_year'],config['end_year']+1)]
        periods.append(('multi',config['start_year'],config['end_year']))
        db.executemany('INSERT INTO periods VALUES(?,?,?)',periods)
        db.execute('''CREATE TABLE denominators AS SELECT m.location,p.period,e.native_bin,count(*)::BIGINT sample_size,
            count(DISTINCT e.day)::BIGINT day_support,sum(e.contributing_checklists)::BIGINT contributing_checklists
            FROM membership m JOIN events e USING(event_id) JOIN periods p ON e.year BETWEEN p.start_year AND p.end_year GROUP BY 1,2,3''')
        db.execute('''CREATE TABLE numerators AS SELECT m.location,p.period,e.native_bin,d.species_code,count(*)::BIGINT detections
            FROM membership m JOIN events e USING(event_id) JOIN detections d ON e.event_id=d.event_id
            JOIN periods p ON e.year BETWEEN p.start_year AND p.end_year GROUP BY 1,2,3,4''')
        db.execute('''CREATE TABLE profiles AS SELECT l.location,p.period,p.start_year,p.end_year,s.species_code,b.range::INTEGER native_bin,
            coalesce(n.sample_size,0)::BIGINT sample_size,coalesce(k.detections,0)::BIGINT detections,
            coalesce(n.day_support,0)::BIGINT day_support,coalesce(n.contributing_checklists,0)::BIGINT contributing_checklists,
            CASE WHEN coalesce(n.sample_size,0)>0 THEN coalesce(k.detections,0)::DOUBLE/n.sample_size ELSE NULL END reporting_frequency,
            CASE WHEN coalesce(n.sample_size,0)=0 THEN 'no_eligible_events' WHEN n.sample_size<? THEN 'insufficient_support' ELSE 'supported' END value_status
            FROM locations l CROSS JOIN periods p CROSS JOIN species s CROSS JOIN range(1,49) b
            LEFT JOIN denominators n ON l.location=n.location AND p.period=n.period AND b.range=n.native_bin
            LEFT JOIN numerators k ON l.location=k.location AND p.period=k.period AND b.range=k.native_bin AND s.species_code=k.species_code
            ORDER BY l.location,p.period,s.species_code,b.range''',[config['minimum_support']])
        if db.execute('SELECT count(*) FROM profiles WHERE detections>sample_size OR detections<0').fetchone()[0]:
            raise ValueError('Detection/denominator invariant violated')
        db.execute('SET threads=1')
        for table in ['profiles','denominators']:
            order='location,period,native_bin'+(',species_code' if table=='profiles' else '')
            db.execute(f'COPY (SELECT * FROM {table} ORDER BY {order}) TO ? (FORMAT PARQUET,PARTITION_BY(location,period),COMPRESSION ZSTD)',[str(stage/table)])
        db.close();db=None
        (stage/'processing.duckdb').unlink();shutil.rmtree(stage/'spill',ignore_errors=True)
        result={'schema':ENGINE,'identity':key,'normalized_identity':norm['identity'],'snapshot':snapshot,
                'config':config,'calendar':BIN_DEFINITION,'metrics':norm['metrics'],
                'outputs':{str(p.relative_to(stage)):digest(p) for p in sorted(stage.rglob('*.parquet'))},
                'evidence':snapshot.get('evidence','real_source_unvalidated'),
                'publication_status':'blocked_pending_real_validation_and_public_eligibility'}
        save(stage/'manifest.json',result);stage.replace(destination)
        return destination,result,reused
    finally:
        if db:db.close()
        if stage.exists():shutil.rmtree(stage)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=PRIVATE/'geography/engine')
    parser.add_argument('--max-input-bytes',type=int,default=500_000_000)
    parser.add_argument('--disk-reserve-bytes',type=int,default=20_000_000_000)
    parser.add_argument('--memory-mb',type=int,default=2048);parser.add_argument('--max-spill-bytes',type=int,default=4_000_000_000)
    args=parser.parse_args()
    path,manifest,reused=build(args.snapshot,args.config,args.output,Limits(max_input_bytes=args.max_input_bytes,
        disk_reserve_bytes=args.disk_reserve_bytes,memory_mb=args.memory_mb,max_spill_bytes=args.max_spill_bytes))
    print(json.dumps({'build':str(path.relative_to(PRIVATE)),'identity':manifest['identity'],'cache_reused':reused,'metrics':manifest['metrics']}))


if __name__=='__main__':main()
