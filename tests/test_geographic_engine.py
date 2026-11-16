"""Synthetic integration coverage. These fixtures do not establish real EBD parity."""
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import duckdb

from tooling.discover import PRIVATE, save
from tooling.geographic_engine import build, identity, SCHEMAS
from tooling.geography_io import Limits, digest
from tooling.geographic_validation import compare


class GeographicEngineTests(unittest.TestCase):
    def setUp(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        self.root=Path(tempfile.mkdtemp(prefix='test-geographic-',dir=PRIVATE))
        self.limits=Limits(disk_reserve_bytes=1,max_spill_bytes=100_000_000,memory_mb=256)
        self.sed=self.root/'sed.txt';self.ebd=self.root/'ebd.txt';self.cross=self.root/'cross.csv'
        self.cross.write_text('scientific_name,species_code,decision,rationale\nFixture species,fixture,accepted,scientific concept agreement\nFixture subspecies,fixture,accepted,documented parent\nAmbiguous bird,,unresolved,split unresolved\n')
        self.members=[self.event('a','G'),self.event('b','G'),self.event('zero'),self.event('next',day='2021-02-28'),self.event('other',county='US-AA-002',lon=-86.5),self.event('incomplete',complete='0')]
        self.observations=[['a','Fixture species','X','1'],['b','Fixture subspecies','3','1'],['a','Ambiguous bird','X','1'],['next','Fixture species','2','1'],['other','Fixture species','3','0']]
        self.config={'start_year':2020,'end_year':2021,'minimum_support':2,'effort':{},'locations':[
            {'id':'state','kind':'state','name':'Synthetic state','coverage_states':['US-AA'],'selector':{'type':'state','ids':['US-AA']}},
            {'id':'county','kind':'county','name':'Synthetic county','coverage_states':['US-AA'],'parent':'state','selector':{'type':'county','ids':['US-AA-001']}},
            {'id':'destination','kind':'destination','name':'Synthetic visit','coverage_states':['US-AA'],'parent':'county','selector':{'type':'bbox','bounds':[-88,37,-87,39]}}]}
        self.config_path=self.root/'config.json';self.snapshot_path=self.root/'snapshot.json'
        self.write()
    def tearDown(self):shutil.rmtree(self.root)
    def event(self,id,group='',complete='1',day='2020-01-01',county='US-AA-001',lon=-87.5,duration='30'):
        return [id,group,complete,day,'US-AA',county,'Lfixture','38',str(lon),'P22',duration,'1','2']
    def write(self):
        for kind,rows,path in [('sed',self.members,self.sed),('ebd',self.observations,self.ebd)]:
            with path.open('w',newline='') as stream:
                w=csv.writer(stream,delimiter='\t');w.writerow(SCHEMAS[kind]);w.writerows(rows)
        self.snapshot={'snapshot_id':'fixture-2026','source_taxonomy_version':'fixture','target_taxonomy_version':'fixture',
                       'grant_reference':'synthetic-not-a-grant','terms_url':'https://example.invalid/synthetic','intended_use':'integration test',
                       'states':['US-AA'],'start_year':2020,'end_year':2021,'all_species':True,'all_months':True,
                       'source_scope':{'kind':'states','ids':['US-AA']},
                       'evidence':'synthetic_integration','artifacts':{}}
        for kind,p in [('sed',self.sed),('ebd',self.ebd),('crosswalk',self.cross)]:
            self.snapshot['artifacts'][kind]={'path':p.name,'bytes':p.stat().st_size,'sha256':digest(p),'snapshot_id':'fixture-2026'}
        save(self.snapshot_path,self.snapshot);save(self.config_path,self.config)
    def run_build(self):return build(self.snapshot_path,self.config_path,self.root/'engine',self.limits)
    def query(self,path,sql):
        with duckdb.connect() as db:
            return db.execute(sql,[str(path/'profiles/**/*.parquet')]).fetchall()
    def test_complete_denominators_shared_rollup_years_and_missingness(self):
        path,manifest,reused=self.run_build();self.assertFalse(reused)
        self.assertEqual(manifest['metrics']['events'],4)
        self.assertEqual(manifest['metrics']['detections'],2)
        self.assertEqual(manifest['metrics']['taxonomy_holds'],1)
        rows=self.query(path,"SELECT sample_size,detections,reporting_frequency,value_status FROM read_parquet(?,hive_partitioning=true) WHERE location='county' AND period='multi' AND native_bin=1")
        self.assertEqual(rows,[(2,1,.5,'supported')])
        rows=self.query(path,"SELECT sample_size,detections,reporting_frequency,value_status FROM read_parquet(?,hive_partitioning=true) WHERE location='county' AND period='2021' AND native_bin IN (1,8) ORDER BY native_bin")
        self.assertEqual(rows,[(0,0,None,'no_eligible_events'),(1,1,1.,'insufficient_support')])
        self.assertEqual(self.query(path,"SELECT count(*) FROM read_parquet(?,hive_partitioning=true)"),[(3*3*48,)])
    def test_cache_reuse_config_changes_and_deterministic_rebuild(self):
        path,first,_=self.run_build();_,second,reused=self.run_build()
        self.assertTrue(reused);self.assertEqual(first,second)
        shutil.rmtree(path)
        _,rebuilt,reused=self.run_build();self.assertTrue(reused);self.assertEqual(first,rebuilt)
        self.config['minimum_support']=10;save(self.config_path,self.config)
        changed,report,reused=self.run_build();self.assertTrue(reused)
        self.assertNotEqual(changed,path);self.assertEqual(first['normalized_identity'],report['normalized_identity'])
    def test_conflicting_group_and_effort_filters(self):
        self.members[1][-3]='45';self.config['effort']={'max_duration_minutes':40};self.write()
        _,report,_=self.run_build();self.assertEqual(report['metrics']['events'],3)
        self.assertEqual(report['metrics']['excluded_groups'],2)
    def test_polygon_and_shared_boundary_rule(self):
        geom={'type':'Polygon','coordinates':[[[-88,37],[-87,37],[-87,39],[-88,39],[-88,37]]]}
        self.config['locations'][-1]['selector']={'type':'polygon','boundary':{'geometry':geom,'sha256':identity(geom),'crs':'EPSG:4326','source_url':'https://example.invalid/fixture','license':'synthetic'}}
        self.write();path,_,_=self.run_build()
        self.assertEqual(self.query(path,"SELECT sample_size FROM read_parquet(?,hive_partitioning=true) WHERE location='destination' AND period='multi' AND native_bin=1"),[(2,)])
    def test_scope_mismatch_orphans_bad_taxonomy_and_parent_cycles_fail(self):
        self.snapshot['artifacts']['sed']['snapshot_id']='different';save(self.snapshot_path,self.snapshot)
        with self.assertRaises(ValueError):self.run_build()
        self.write();self.observations.append(['orphan','Fixture species','1','1']);self.write()
        with self.assertRaises(ValueError):self.run_build()
        self.observations.pop();self.config['locations'][0]['parent']='county';self.write()
        with self.assertRaises(ValueError):self.run_build()
    def test_empty_eligible_population_stays_missing(self):
        for member in self.members:member[2]='0'
        self.write();path,_,_=self.run_build()
        self.assertEqual(self.query(path,"SELECT DISTINCT sample_size,reporting_frequency,value_status FROM read_parquet(?,hive_partitioning=true)"),[(0,None,'no_eligible_events')])
    def test_hash_and_budget_fail_closed(self):
        self.sed.write_text(self.sed.read_text()+'corruption')
        with self.assertRaises(ValueError):self.run_build()
    def test_denominator_comparison_precedes_rate_comparison(self):
        path,_,_=self.run_build();references=self.root/'references';references.mkdir()
        sizes=[0]*48;sizes[0]=2;sizes[7]=1
        reference={'metadata':{'sample_sizes':sizes,'location':'county','source_sha256':'synthetic','start_year':2020,'end_year':2021},
                   'rows':[{'start':'2001-01-01','species_code':'fixture','frequency':.5},{'start':'2001-02-22','species_code':'fixture','frequency':1.}]}
        save(references/'reference.json',reference)
        report=compare(path,references);self.assertEqual(report['evidence'],'synthetic_integration')
        self.assertEqual(report['counties'][0]['denominator_status'],'matched')
        self.assertEqual(report['counties'][0]['frequencies']['max_absolute_difference'],0.)
        reference['metadata']['sample_sizes'][0]=99;save(references/'reference.json',reference)
        report=compare(path,references)
        self.assertEqual(report['counties'][0]['max_absolute_denominator_difference'],97)
        self.assertIn('not compared',report['counties'][0]['frequencies']['status'])
    def test_county_pilot_cannot_claim_statewide_coverage(self):
        self.snapshot['source_scope']={'kind':'counties','ids':['US-AA-001','US-AA-002']}
        save(self.snapshot_path,self.snapshot)
        with self.assertRaises(ValueError):self.run_build()


if __name__=='__main__':unittest.main()
