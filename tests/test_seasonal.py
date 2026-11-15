import csv
import tempfile
from datetime import date
from pathlib import Path
import unittest
from tooling.seasonal import parse_long,rank,SCHEMA,demonstrate


class SeasonalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'fixture.csv'
        self.meta={'schema':SCHEMA,'source_url':'https://example.org/synthetic-unit-fixture','source_sha256':'fixture-only','location':'fixture','start_year':2016,'end_year':2025,'taxonomy_version':'fixture-2026','units':'fraction_of_complete_checklists','bin_definition':'synthetic quarterly unit fixture; not real occurrence','missing_semantics':'explicit null'}
        self.tax={'resident':'Fixture resident','migrant':'Fixture migrant'}
    def tearDown(self):self.tmp.cleanup()
    def write(self,rows):
        with self.path.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['species_code','scientific_name','bin_start','bin_end','frequency','sample_size']);writer.writerows(rows)
    def test_approaching_window_does_not_require_current_presence(self):
        rows=[]
        for code,values in [('resident',[.1,.1,.1,.1]),('migrant',[0,.8,0,0])]:
            for start,end,value in zip(['01-01','04-01','07-01','10-01'],['04-01','07-01','10-01','01-01'],values):rows.append([code,self.tax[code],start,end,value,100])
        self.write(rows);profile=parse_long(self.path,self.meta,self.tax);result=rank(profile,date(2026,3,15))
        self.assertEqual(result[0]['species_code'],'migrant');self.assertEqual(result[0]['current_reporting_frequency'],0);self.assertEqual(result[0]['approaching_window_rise'],.8)
    def test_zero_support_is_missing_not_absence(self):
        self.write([['resident',self.tax['resident'],'01-01','01-01',0,0]])
        with self.assertRaises(ValueError):parse_long(self.path,self.meta,self.tax) # invalid zero-length annual bin
        self.write([['resident',self.tax['resident'],'01-01','07-01',0,0],['resident',self.tax['resident'],'07-01','01-01',0,100]])
        profile=parse_long(self.path,self.meta,self.tax)
        self.assertIsNone(rank(profile,date(2026,2,1))[0]['current_reporting_frequency']);self.assertEqual(rank(profile,date(2026,8,1))[0]['current_reporting_frequency'],0)
    def test_percent_units_and_taxonomy_mismatch_are_rejected(self):
        self.write([['resident','wrong name','01-01','07-01',20,100]])
        with self.assertRaises(ValueError):parse_long(self.path,self.meta,self.tax)
    def test_gaps_or_duplicate_bins_rejected(self):
        self.write([['resident',self.tax['resident'],'01-01','04-01',.2,100],['resident',self.tax['resident'],'05-01','01-01',.3,100]])
        with self.assertRaises(ValueError):parse_long(self.path,self.meta,self.tax)
    def test_scope_mismatch_blocks_comparison(self):
        a={'metadata':self.meta,'rows':[]};b={'metadata':{**self.meta,'start_year':2020},'rows':[]}
        with self.assertRaises(ValueError):demonstrate([a,b])
    def test_approaching_window_wraps_from_december_into_january(self):
        rows=[]
        for code,values in [('resident',[.1,.1,.1,.1]),('migrant',[.8,0,0,0])]:
            for start,end,value in zip(['01-01','04-01','07-01','10-01'],['04-01','07-01','10-01','01-01'],values):rows.append([code,self.tax[code],start,end,value,100])
        self.write(rows);profile=parse_long(self.path,self.meta,self.tax)
        ranked=rank(profile,date(2026,12,20));self.assertEqual(ranked[0]['species_code'],'migrant');self.assertEqual(ranked[0]['approaching_window_rise'],.8)


if __name__=='__main__':unittest.main()
