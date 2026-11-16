"""Synthetic raster tests; the real two-species extraction has separate experiment evidence."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from tooling.modeled_geography import extract


class ModeledGeographyTests(unittest.TestCase):
    def test_native_bands_nodata_zero_and_area_support_stay_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.tif'
            data=np.full((2,4,4),-999.,dtype='float32');data[0,:,:]=0
            with rasterio.open(path,'w',driver='GTiff',height=4,width=4,count=2,dtype='float32',crs='EPSG:8857',transform=from_origin(-54000,54000,27000,27000),nodata=-999) as target:target.write(data)
            result=extract(path,[-.1,-.1,.1,.1],species='fixture',product='occurrence',version=2023,band_dates=['2023-01-01','2023-01-08'],quality={'quality':'synthetic'})
            self.assertEqual(result['bands'][0]['value'],0)
            self.assertAlmostEqual(result['bands'][0]['valid_area_fraction'],1.)
            self.assertIsNone(result['bands'][1]['value'])
            self.assertEqual(result['bands'][1]['status'],'no_estimate')
            self.assertEqual(result['resolution_m'],[27000,27000])
            self.assertEqual(result['signal'],'modeled_occurrence')
            self.assertIn('consent',result['public_eligibility'])
            with self.assertRaises(ValueError):extract(path,[-.1,-.1,.1,.1],species='fixture',product='occurrence',version=2023,band_dates=[],quality={})


if __name__=='__main__':unittest.main()
