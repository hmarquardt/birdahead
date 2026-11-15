import csv
import json
from pathlib import Path
import tempfile
import unittest
import duckdb
from tooling.checklists import aggregate


class ChecklistDenominatorTests(unittest.TestCase):
    """Synthetic source-shaped checklists. Never presented as EBD/reference parity."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.ebd=self.root/'ebd.txt';self.sed=self.root/'sed.txt';self.crosswalk=self.root/'crosswalk.csv'
        self.crosswalk.write_text('scientific_name,species_code\nFixture bird,fixture\n')
        self.config={'snapshot':'synthetic-fixture','source_taxonomy_version':'fixture','target_taxonomy_version':'fixture',
                     'start_year':2016,'end_year':2025,'crosswalk_review_status':'reviewed','source_coverage':'all_taxa_and_complete_checklists',
                     'locations':[{'id':'county','kind':'county','source_id':'US-IN-051'},{'id':'hotspot','kind':'hotspot','source_id':'Lfixture'}]}
    def tearDown(self):self.tmp.cleanup()
    def write(self,sed,ebd):
        for path,header,rows in [(self.sed,['SAMPLING EVENT IDENTIFIER','GROUP IDENTIFIER','ALL SPECIES REPORTED','OBSERVATION DATE','COUNTY CODE','LOCALITY ID'],sed),
                                 (self.ebd,['SAMPLING EVENT IDENTIFIER','SCIENTIFIC NAME','OBSERVATION COUNT','APPROVED'],ebd)]:
            with path.open('w',newline='') as f:
                writer=csv.writer(f,delimiter='\t');writer.writerow(header);writer.writerows(rows)
    def event(self,id,group='',complete=1,day='2020-01-01',hotspot='Lfixture'):
        return [id,group,complete,day,'US-IN-051',hotspot]
    def run_kernel(self):return aggregate(self.ebd,self.sed,self.crosswalk,self.config,self.root/'out')
    def test_denominator_includes_zero_detection_lists_and_shared_events_once(self):
        self.write([self.event('one','G1'),self.event('shared','G1'),self.event('zero'),self.event('incomplete',complete=0)],
                   [['one','Fixture bird','X',1],['shared','Fixture bird',3,1],['incomplete','Fixture bird',1,1]])
        report=self.run_kernel();self.assertEqual(report['metrics']['eligible_events'],2)
        db=duckdb.connect()
        rows=db.execute('SELECT * FROM read_parquet(?) WHERE location=? AND native_bin=1',[str(self.root/'out/profiles.parquet'),'county']).fetchall()
        self.assertEqual(rows[0][3:6],(2,1,.5))
        row=db.execute('SELECT sample_size,reporting_frequency,value_status FROM read_parquet(?) WHERE location=? AND native_bin=2',[str(self.root/'out/profiles.parquet'),'county']).fetchone()
        self.assertEqual(row,(0,None,'no_eligible_events'));db.close()
    def test_conflicting_shared_event_is_excluded_not_arbitrarily_counted(self):
        self.write([self.event('one','G1'),self.event('shared','G1',complete=0),self.event('valid')],[['one','Fixture bird',1,1],['valid','Fixture bird',1,0]])
        report=self.run_kernel();self.assertEqual(report['metrics']['eligible_events'],1)
        self.assertEqual(report['metrics']['selected_species_detections'],0)
    def test_crosswalk_ambiguity_and_source_conditioning_rejected(self):
        self.write([self.event('one')],[['one','Fixture bird',1,1]])
        self.crosswalk.write_text('scientific_name,species_code\nFixture bird,fixture\nFixture bird,wrong\n')
        with self.assertRaises(ValueError):self.run_kernel()
        self.config['source_coverage']='pilot_species_checklists_only'
        with self.assertRaises(ValueError):self.run_kernel()
    def test_configured_county_and_hotspot_get_distinct_support(self):
        self.write([self.event('one'),self.event('other',hotspot='Lother')],[['one','Fixture bird',1,1]])
        self.run_kernel();db=duckdb.connect()
        rows=db.execute('SELECT location,sample_size,reporting_frequency FROM read_parquet(?) WHERE native_bin=1 ORDER BY location',[str(self.root/'out/profiles.parquet')]).fetchall();db.close()
        self.assertEqual(rows,[('county',2,.5),('hotspot',1,1.0)])


if __name__=='__main__':unittest.main()
