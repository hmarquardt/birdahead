"""Bounded official S&T inventory and private area-weighted raster extraction."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import urllib.parse

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
from shapely.geometry import box

from tooling.discover import PRIVATE, ROOT, credential, now, save
from tooling.geography_io import Limits, Transfer, digest, private_path

BASE = 'https://st-download.ebird.org/v1/'


def extract(path, bounds, *, species, product, version, band_dates, quality):
    """Area intersections in the product's equal-area CRS, with NA support preserved.

    Bounds are a deliberately coarse destination envelope, not a county polygon.
    No-estimate cells are excluded, never converted to zero.
    """
    with rasterio.Env(GDAL_CACHEMAX=64_000_000), rasterio.open(path) as src:
        if not src.crs or not src.crs.is_projected or 'equal' not in src.crs.to_wkt().lower():
            raise ValueError('Area weighting requires a documented equal-area projected raster')
        if src.transform.b or src.transform.d:
            raise ValueError('Rotated product grid unsupported')
        projected = transform_bounds('EPSG:4326', src.crs, *bounds, densify_pts=41)
        fractional = from_bounds(*projected, transform=src.transform)
        x0,y0 = math.floor(fractional.col_off),math.floor(fractional.row_off)
        x1,y1 = math.ceil(fractional.col_off+fractional.width),math.ceil(fractional.row_off+fractional.height)
        window = rasterio.windows.Window(x0,y0,x1-x0,y1-y0)
        window = window.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        if window.width * window.height * src.count > 2_000_000:
            raise ValueError('Spatial extraction exceeds cell-band ceiling')
        if len(band_dates) != src.count:
            raise ValueError('Native band calendar does not match raster')
        data = src.read(window=window, masked=True)
        affine = src.window_transform(window)
        envelope = box(*projected)
        weights = np.zeros((data.shape[1], data.shape[2]))
        for row in range(weights.shape[0]):
            for col in range(weights.shape[1]):
                x1, y1 = affine @ (col, row)
                x2, y2 = affine @ (col+1, row+1)
                weights[row, col] = box(min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)).intersection(envelope).area
        bands = []
        for index, layer in enumerate(data):
            valid = ~np.ma.getmaskarray(layer) & np.isfinite(layer.data) & (weights > 0)
            area = float(weights[valid].sum())
            bands.append({'native_date': band_dates[index], 'value': float(np.average(layer.data[valid], weights=weights[valid])) if area else None,
                          'valid_cells': int(valid.sum()), 'valid_area_m2': area,
                          'valid_area_fraction': area/envelope.area, 'status': 'estimate' if area else 'no_estimate'})
        return {'schema': 'birdahead-modeled-profile-v1', 'signal': 'modeled_'+product,
                'species_code': species, 'product_vintage': version, 'source_sha256': digest(path),
                'resolution_m': list(src.res), 'crs': src.crs.to_string(), 'nodata': src.nodata,
                'spatial_scope': 'coarse envelope transformed to product CRS; not an administrative boundary',
                'units': 'standardized occurrence rate' if product == 'occurrence' else 'standardized relative abundance',
                'effort': 'expert observer, 1 hour, 2 km, optimal time/weather (provider scenario)',
                'quality_metadata': quality, 'bands': bands, 'public_eligibility': 'blocked_written_web_app_consent_required'}


def experiment(*, version=2023, species=('norcar','bkpwar'), max_bytes=64_000_000):
    key = credential('EBIRD_ST_API_KEY')
    if not key:
        raise ValueError('S&T credential unavailable')
    root = private_path(PRIVATE/'geography/status-and-trends')
    transfer = Transfer({'st-download.ebird.org'}, Limits(max_download_bytes=max_bytes), max_requests=30)
    report = {'schema': 'birdahead-modeled-experiment-v1', 'at': now(), 'evidence': 'observed experiment',
              'version': version, 'latest_version_verified': False, 'max_requests':30, 'max_download_bytes':max_bytes,
              'documentation': 'https://ebird.github.io/ebirdst/articles/api.html', 'species': []}
    for code in species:
        item = {'species_code': code, 'products': [], 'failures': []}
        try:
            url = BASE+f'list-obj/{version}/{code}?'+urllib.parse.urlencode({'key':key})
            # Listings are capped separately; no raw bodies go to public reports.
            with transfer.open(url) as response:
                ceiling=min(500_000,transfer.remaining)
                raw = response.read(ceiling+1)
                if len(raw)>ceiling or key.encode() in raw:
                    raise ValueError('Unsafe/oversized inventory response')
                transfer.bytes += len(raw); transfer.remaining -= len(raw)
                objects = json.loads(raw)
            if not isinstance(objects,list) or any(not isinstance(p,str) or not p.startswith(f'{version}/{code}/') for p in objects):
                raise ValueError('Unexpected official inventory schema')
            save(root/f'{version}-{code}-objects.json', objects)
            item.update(object_count=len(objects), listing_bytes=len(raw),
                        product_families=sorted(set(p.split('/')[2] for p in objects)),
                        weekly_coarse_products=[p for p in objects if '/weekly/' in p and '_27km_' in p and any(t in p for t in ['occurrence_median','abundance_median'])])
            def fetch(obj):
                if obj not in objects:
                    raise ValueError('Product is not in authenticated inventory')
                path=root/obj
                url=BASE+'fetch?'+urllib.parse.urlencode({'objKey':obj,'key':key})
                details=transfer.download(url,path)
                return path,details
            dates_path, date_stats = fetch(f'{version}/{code}/weekly/band-dates.csv')
            dates_rows=list(csv.DictReader(io.StringIO(dates_path.read_text())))
            config_path, config_stats = fetch(f'{version}/{code}/config.json')
            quality=json.loads(config_path.read_text())
            # Keep provider metadata verbatim in private derived output; report only its schema keys.
            item['quality_metadata_keys']=sorted(quality) if isinstance(quality,dict) else []
            item['metadata_bytes']=date_stats['bytes']+config_stats['bytes']
            date_column=next((k for k in dates_rows[0] if 'date' in k.lower()),None)
            if date_column is None:
                raise ValueError('No native date field in band calendar')
            dates=[r[date_column] for r in dates_rows]
            for product in ['occurrence','abundance']:
                obj=f'{version}/{code}/weekly/{code}_{product}_median_27km_{version}.tif'
                try:
                    path,stats=fetch(obj)
                    result=extract(path,[-88.1,37.75,-86.6,39.3],species=code,product=product,
                                   version=version,band_dates=dates,quality=quality)
                    save(root/f'{version}-{code}-{product}-southwest-indiana.json',result)
                    vals=[b['value'] for b in result['bands'] if b['value'] is not None]
                    item['products'].append({'object':obj,**stats,'bands':len(result['bands']),
                        'resolution_m':result['resolution_m'],'crs':result['crs'],
                        'valid_cells_range':[min(b['valid_cells'] for b in result['bands']),max(b['valid_cells'] for b in result['bands'])],
                        'value_range':[min(vals),max(vals)] if vals else None,
                        'signal':result['signal'],'public_eligibility':result['public_eligibility']})
                except (ValueError,RuntimeError):
                    item['failures'].append({'object':obj,'reason':'size, permission, transport or product validation gate; see private run state'})
        except (ValueError,RuntimeError,KeyError,IndexError):
            item['failures'].append({'stage':'inventory_or_metadata','reason':'provider/schema/resource gate; no credential-bearing exception retained'})
        report['species'].append(item)
    report.update(requests=transfer.requests,transferred_bytes=transfer.bytes,events=transfer.events)
    save(ROOT/'experiments/phase-eight-modeled.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Explicit bounded experiment; default is offline')
    parser.add_argument('--max-bytes',type=int,default=64_000_000)
    args=parser.parse_args()
    if args.live:
        print(json.dumps(experiment(max_bytes=args.max_bytes),indent=2))
    else:
        print('Offline. Use --live for two species, 27 km occurrence/abundance, 30 requests, 64 MB maximum.')
