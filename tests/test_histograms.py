import tempfile
from pathlib import Path
import unittest
from tooling.histograms import parse_native, native_bin, MONTHS


class HistogramTests(unittest.TestCase):
    """Synthetic native-format fixtures; no restricted source data committed."""
    def fixture(self, directory, values, sizes=None):
        path=Path(directory)/'ebird_US-IN-051__2016_2025_1_12_barchart.txt'
        header='\t'+'\t'.join(name if k==0 else '' for name in MONTHS for k in range(4))+'\t'
        path.write_text('\n\nFrequency of observations in the selected location(s).:\nNumber of taxa: \t1\n\n'+header+'\nSample Size:\t'+'\t'.join(map(str,sizes or [100]*48))+'\t\n\nFixture bird\t'+'\t'.join(map(str,values))+'\t\n')
        return path
    def parse(self,path):
        return parse_native(path,[{'comName':'Fixture bird','sciName':'Fixture test','speciesCode':'fixture'}],
                            [{'ebird_species_code':'fixture','ebird_scientific_name':'Fixture test'}])[0]
    def test_48_bins_are_not_iso_weeks(self):
        self.assertEqual(native_bin(1,4)['end'],'2001-02-01')
        self.assertEqual(native_bin(12,4)['end'],'2002-01-01')
        self.assertEqual(native_bin(2,3)['start'],'2001-02-15')
    def test_preserve_marker_and_zero_support_as_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            values=[.2]*48;values[0]=.0015;values[1]=0
            sizes=[100]*48;sizes[1]=0
            p=self.parse(self.fixture(d,values,sizes))
            self.assertIsNone(p['rows'][0]['frequency']);self.assertEqual(p['rows'][0]['source_value'],.0015)
            self.assertIsNone(p['rows'][1]['frequency']);self.assertEqual(p['rows'][2]['frequency'],.2)
            self.assertIsNone(p['metadata']['source_taxonomy_version'])
    def test_invalid_shape_or_fraction_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):self.parse(self.fixture(d,[.2]*47))
            with self.assertRaises(ValueError):self.parse(self.fixture(d,[20]*48))
    def test_noninteger_numerator_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.parse(self.fixture(d,[.12345]*48))
            self.assertTrue(all(r['frequency'] is None for r in p['rows']))
            self.assertEqual(p['metadata']['anomalies_pilot']['nonintegral_detection_count'],48)


if __name__=='__main__':unittest.main()
