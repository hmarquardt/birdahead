"""Bounded Phase 0.5 candidate acquisition. Credentials never enter artifacts."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from tooling.discover import ROOT, PRIVATE, UA, credential, now, save, photo_candidate, Client

WORK = PRIVATE / 'phase05'
CATALOG = WORK / 'catalog.json'
COMMERCIAL_CODES = {'cc0','cc-by','cc-by-sa'}
NONCOMMERCIAL_CODES = COMMERCIAL_CODES | {'cc-by-nc','cc-by-nc-sa'}


class SafeClient:
    """Only XC uses query authentication; no URL/exception with keys is emitted."""
    def __init__(self, budget=65):
        self.budget = budget
        self.calls = 0
        self.last = 0.0
        self.events = []

    def json(self, endpoint, params, xc=False):
        public_params = dict(params)
        if any(k in public_params for k in ['key','token','api_key']):
            raise ValueError('Use the protected authentication path')
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme != 'https' or parsed.hostname not in {'xeno-canto.org','api.inaturalist.org'}:
            raise ValueError('Unapproved API host')
        cache_key = hashlib.sha256(json.dumps([endpoint,public_params],sort_keys=True).encode()).hexdigest()
        cache = WORK / 'cache' / (cache_key+'.json')
        if cache.exists():
            return json.loads(cache.read_text())
        if self.calls >= self.budget:
            raise RuntimeError('Bounded API request budget exhausted')
        actual_params = dict(public_params)
        secret = None
        if xc:
            if endpoint != 'https://xeno-canto.org/api/3/recordings':
                raise ValueError('Query authentication is limited to XC API v3')
            secret = credential('XENO_CANTO_API_KEY')
            if not secret:
                raise RuntimeError('XENO_CANTO_API_KEY unavailable')
            actual_params['key'] = secret
        time.sleep(max(0, 1.2-(time.monotonic()-self.last)))
        self.last = time.monotonic()
        self.calls += 1
        start = time.monotonic()
        request = urllib.request.Request(endpoint+'?'+urllib.parse.urlencode(actual_params),headers={'User-Agent':UA})
        try:
            with urllib.request.urlopen(request,timeout=40) as response:
                raw = response.read(12_000_001)
                if len(raw)>12_000_000:
                    raise RuntimeError('API response exceeds budget')
                data = json.loads(raw)
                status = response.status
        except urllib.error.HTTPError as exc:
            self.events.append({'source':parsed.hostname,'query':public_params,'status':exc.code,'at':now()})
            raise RuntimeError(f'{parsed.hostname} HTTP {exc.code}; URL/body withheld') from None
        except Exception:
            raise RuntimeError(f'{parsed.hostname} request failed; URL and exception withheld') from None
        if secret and secret.encode() in raw:
            raise RuntimeError('Response unexpectedly contains credential; not retained')
        self.events.append({'source':parsed.hostname,'query':public_params,'status':status,'bytes':len(raw),'seconds':round(time.monotonic()-start,3),'at':now()})
        save(cache,data)
        return data


def load_catalog():
    return json.loads(CATALOG.read_text()) if CATALOG.exists() else []


def license_info(url):
    match = re.fullmatch(r'https?://creativecommons.org/(?:licenses/(by(?:-nc)?(?:-sa)?)/(\d\.\d)|publicdomain/(zero)/(1\.0))/?',url or '')
    if not match:
        return {'license_code':None,'license_version':None,'license_url':url,'commercial_compatible':False,'derivatives_permitted':False}
    code = 'cc-'+match[1] if match[1] else 'cc0'
    return {'license_code':code,'license_version':match[2] or match[4],'license_url':url,
            'commercial_compatible':code in COMMERCIAL_CODES,'derivatives_permitted':code in NONCOMMERCIAL_CODES,
            'share_alike':code.endswith('-sa')}


def inat_license_info(code):
    """Mapping verified from iNaturalist Shared::LicenseModule, Git blob 0fba8c7."""
    if code not in NONCOMMERCIAL_CODES:return license_info(None)
    url='https://creativecommons.org/publicdomain/zero/1.0/' if code=='cc0' else 'https://creativecommons.org/licenses/'+code.removeprefix('cc-')+'/4.0/'
    return {**license_info(url),'rights_evidence':{
        'asset_license_field':'photo.license_code (independent of observation license)',
        'version_mapping_source':'https://github.com/inaturalist/inaturalist/blob/main/app/models/shared/license_module.rb',
        'source_blob_sha':'0fba8c7870f89a84f3d0f021a4706c7742ef9761',
        'mapping_kind':'official source implementation; CC_VERSION=4.0, CC0_VERSION=1.0'}}


def file_download(url, dest, limit=15_000_000):
    parsed=urllib.parse.urlsplit(url)
    allowed={'inaturalist-open-data.s3.amazonaws.com','static.inaturalist.org','xeno-canto.org','upload.wikimedia.org'}
    if parsed.scheme!='https' or parsed.hostname not in allowed or any(k in dict(urllib.parse.parse_qsl(parsed.query)) for k in ['key','token']):
        raise ValueError('Unapproved media URL')
    if dest.exists():
        return dest.read_bytes()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=45) as response:
            final=urllib.parse.urlsplit(response.geturl())
            # XC redirects its public file to its own storage/CDN. No credentials follow.
            if final.scheme!='https' or not (final.hostname in allowed or final.hostname.endswith('.xeno-canto.org')):
                raise RuntimeError('Unapproved media redirect')
            raw=response.read(limit+1)
            typ=response.headers.get('Content-Type','')
        if len(raw)>limit or len(raw)<100 or 'text/html' in typ:
            raise RuntimeError('Rejected media size/type')
    except Exception:
        raise RuntimeError('Media transfer failed; URL and exception withheld') from None
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_bytes(raw);tmp.replace(dest)
    time.sleep(0.4)
    return raw


def image_metrics(path):
    from PIL import Image, ImageFilter, ImageStat, ImageOps
    with Image.open(path) as im:
        im.load();gray=ImageOps.grayscale(im).resize((256,256));edges=gray.filter(ImageFilter.FIND_EDGES)
        # Ignore the artificial border from FIND_EDGES; this is a triage metric.
        edge_variance=ImageStat.Stat(edges.crop((2,2,254,254))).var[0]
        luminosity=ImageStat.Stat(gray).mean[0]
        tiny=gray.resize((9,8));pixels=list(tiny.tobytes());bits=0
        for y in range(8):
            for x in range(8):bits=(bits<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
        return {'width':im.width,'height':im.height,'edge_variance_256':round(edge_variance,3),
                'mean_luminance':round(luminosity,3),'dhash':f'{bits:016x}',
                'quality_method':'Pillow decoded; edge/luminance are screening heuristics, not biological confidence'}


def expand_photos(client,alternates=False):
    catalog=load_catalog();species=json.loads((ROOT/'experiments/poc-species.json').read_text())
    risky={name for pair in [("Cooper's Hawk","Sharp-shinned Hawk"),('Downy Woodpecker','Hairy Woodpecker'),('Turkey Vulture','Black Vulture'),('Greater Yellowlegs','Lesser Yellowlegs')] for name in pair}
    gaps={'Northern Cardinal','American Robin','Snow Goose','Sandhill Crane','Bufflehead','Wood Duck','Blue-winged Teal'}
    for target in species:
        if alternates and target['common_name'] not in risky|gaps:continue
        existing=[r for r in catalog if r['kind']=='photo' and r['species_code']==target['ebird_species_code']]
        desired=(8 if target['common_name'] in risky else 7) if alternates else 5
        if len(existing)>=desired:continue
        data=client.json('https://api.inaturalist.org/v1/observations',{
            'taxon_id':target['taxon_id'],'quality_grade':'research','captive':'false',
            'photo_license':','.join(sorted(NONCOMMERCIAL_CODES)),'per_page':12,'order_by':'votes' if alternates else 'id','order':'desc',
            'swlat':24,'swlng':-100,'nelat':52,'nelng':-60})
        contributors=Counter(r['contributor_id'] for r in existing)
        chosen_ids={r['id'] for r in catalog}
        for obs in data['results']:
            if len(catalog)>=240:break
            owner=str(obs['user']['id'])
            if contributors[owner]>=2:continue
            if obs.get('community_taxon_id')!=target['taxon_id'] or obs.get('flags'):continue
            if alternates:
                supporters={str(i['user']['id']) for i in obs.get('identifications',[]) if i.get('current') and str(i.get('user',{}).get('id'))!=owner
                    and (i.get('taxon',{}).get('id')==target['taxon_id'] or target['taxon_id'] in i.get('taxon',{}).get('ancestor_ids',[]))}
                if len(supporters)<(2 if target['common_name'] in risky else 1):continue
            for photo in obs.get('photos',[]):
                asset_id=f"inat-{photo['id']}"
                if asset_id in chosen_ids or photo.get('license_code') not in NONCOMMERCIAL_CODES or photo.get('hidden') or photo.get('flags'):continue
                url=photo['url'].replace('/square.','/large.')
                dest=WORK/'media'/(asset_id+Path(urllib.parse.urlsplit(url).path).suffix)
                try:
                    raw=file_download(url,dest,5_000_000);metrics=image_metrics(dest)
                except RuntimeError:
                    continue
                source=photo_candidate(obs,photo,target)
                concordant=[]
                for identification in obs.get('identifications',[]):
                    if identification.get('current') and str(identification.get('user',{}).get('id'))!=owner:
                        taxon=identification.get('taxon',{})
                        if taxon.get('id')==target['taxon_id'] or target['taxon_id'] in taxon.get('ancestor_ids',[]):concordant.append(str(identification['user']['id']))
                record={**source,'id':asset_id,'kind':'photo','species_code':target['ebird_species_code'],
                    'common_name':target['common_name'],'scientific_name':target['scientific_name'],
                    'contributor_id':owner,'local_path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),
                    'bytes':len(raw),'technical_metrics':metrics,'source_verified':True,
                    'source_evidence':{'quality_grade':obs.get('quality_grade'),'community_taxon_id':obs.get('community_taxon_id'),
                        'concordant_non_owner_identifiers':sorted(set(concordant)),
                        'owner_used_computer_vision':obs.get('owners_identification_from_vision'),
                        'source_assertion_not_independent_ground_truth':True},
                    'commercial_compatible':photo['license_code'] in COMMERCIAL_CODES,
                    'machine_screened':True,'human_approved':False,'expert_verified':False,
                    'rights_approved':False,'biology_approved':False,'review_state':'candidate','model_results':[]}
                record.update(inat_license_info(photo['license_code']))
                record.update(uploaded=obs.get('created_at'),acquisition_pass='supported replacement' if alternates else 'latest observations')
                catalog.append(record);chosen_ids.add(asset_id);contributors[owner]+=1
                save(CATALOG,catalog)
                break # one image per observation/encounter
            if sum(r['kind']=='photo' and r['species_code']==target['ebird_species_code'] for r in catalog)>=desired:break
        print(target['common_name'],sum(r['kind']=='photo' and r['species_code']==target['ebird_species_code'] for r in catalog),'photo candidates',flush=True)


def xc_query(target, extra=''):
    return f'sp:"{target["scientific_name"]}" grp:birds box:24,-100,52,-60 id?:no q:">C" {extra}'.strip()


def expand_audio(client):
    catalog=load_catalog();species=json.loads((ROOT/'experiments/poc-species.json').read_text())
    for target in species:
        existing=[r for r in catalog if r['kind']=='audio' and r['species_code']==target['ebird_species_code']]
        if len(existing)>=3:continue
        data=client.json('https://xeno-canto.org/api/3/recordings',{'query':xc_query(target),'per_page':50,'page':1},xc=True)
        aliases={'Astur cooperii':['Accipiter cooperii'],
                 'Leuconotopicus villosus':['Dryobates villosus','Picoides villosus'],
                 'Antigone canadensis':['Grus canadensis']}
        for alias in aliases.get(target['scientific_name'],[]):
            if data.get('recordings'):break
            data=client.json('https://xeno-canto.org/api/3/recordings',{'query':xc_query({**target,'scientific_name':alias}),'per_page':50,'page':1},xc=True)
        records=data.get('recordings',[])
        # Source labels may use older genera; exact epithet/common name alignment is logged.
        records=sorted(records,key=lambda r:(not license_info(r.get('lic')).get('commercial_compatible'),r.get('q')!='A',-int(r.get('id','0'))))
        contributors=Counter(r['contributor_id'] for r in existing)
        types=Counter(r.get('vocalization') for r in existing)
        transfer_attempts=0
        for row in records:
            if transfer_attempts>=6:break
            info=license_info(row.get('lic'));source_status=row.get('status')
            if not info['derivatives_permitted'] or source_status not in [None,'','identified']:continue
            if row.get('q') not in ['A','B'] or row.get('auto')=='yes':continue
            duration=row.get('length','').split(':')
            try:seconds=sum(float(v)*60**i for i,v in enumerate(reversed(duration)))
            except ValueError:continue
            if not 3<=seconds<=180:continue
            if contributors[row.get('rec')]>=1 and len({r.get('rec') for r in records})>=3:continue
            # Retain source identity evidence; never silently map an unexpected species.
            if row.get('en')!=target['common_name'] and f"{row.get('gen')} {row.get('sp')}"!=target['scientific_name']:continue
            asset_id='xc-'+row['id']
            if any(r['id']==asset_id for r in catalog):continue
            url=row.get('file','')
            if url.startswith('//'):url='https:'+url
            dest=WORK/'media'/(asset_id+'.mp3')
            transfer_attempts+=1
            try:raw=file_download(url,dest)
            except RuntimeError:continue
            record={'id':asset_id,'kind':'audio','source':'xeno_canto','source_record_id':row['id'],
                'species_code':target['ebird_species_code'],'common_name':target['common_name'],'scientific_name':target['scientific_name'],
                'source_scientific_name':f"{row.get('gen')} {row.get('sp')}",'source_url':'https://xeno-canto.org/'+row['id'],
                'media_url':url,'creator':row.get('rec'),'contributor_id':row.get('rec'),**info,
                'attribution':f"{row.get('rec')}, XC{row['id']}, {row.get('lic')}",
                'vocalization':row.get('type') or None,'sex':row.get('sex') or None,'age':row.get('stage') or None,
                'plumage':None,'quality_grade':row.get('q'),'identification_status':source_status,
                'observed_on':row.get('date'),'uploaded':row.get('uploaded'),'country':row.get('cnt'),
                'source_evidence':{'identification_status':source_status,'animal_seen':row.get('animal-seen'),
                    'recording_method':row.get('method'),'background_species':row.get('also'),
                    'annotation_set_present':bool(row.get('annotation-set')),'source_assertion_not_independent_ground_truth':True},
                'local_path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                'source_verified':True,'machine_screened':False,'human_approved':False,'expert_verified':False,
                'rights_approved':False,'biology_approved':False,'review_state':'candidate','model_results':[],
                'technical_metrics':{'source_duration':row.get('length'),'source_sample_rate':row.get('smp')},'retrieved_at':now()}
            catalog.append(record);contributors[row.get('rec')]+=1;types[row.get('type')]+=1;save(CATALOG,catalog)
            if sum(r['kind']=='audio' and r['species_code']==target['ebird_species_code'] for r in catalog)>=3:break
        print(target['common_name'],sum(r['kind']=='audio' and r['species_code']==target['ebird_species_code'] for r in catalog),'audio candidates',flush=True)


def validate_xc(client):
    base='https://xeno-canto.org/api/3/recordings'
    query='sp:"Cardinalis cardinalis" grp:birds box:24,-100,52,-60 id?:no q:">C"'
    first=client.json(base,{'query':query,'per_page':50,'page':1},xc=True)
    second=client.json(base,{'query':query,'per_page':50,'page':2},xc=True) if int(first.get('numPages',0))>1 else None
    records=first.get('recordings',[])
    disputed=client.json(base,{'query':'grp:birds box:24,-100,52,-60 id?:yes','per_page':50,'page':1},xc=True)
    evidence={'at':now(),'auth_success':bool(records),'page_1':first.get('page'),'page_2':second.get('page') if second else None,
        'num_pages':first.get('numPages'),'recordings_total':first.get('numRecordings'),'page_size':len(records),
        'page_ids_disjoint':not bool({r['id'] for r in records}&{r['id'] for r in second['recordings']}) if second else None,
        'all_in_requested_box':all(r.get('lat') and r.get('lon') and 24<=float(r['lat'])<=52 and -100<=float(r['lon'])<=-60 for r in records),
        'quality_counts':dict(Counter(r.get('q') for r in records)),
        'identification_status_counts':dict(Counter(str(r.get('status')) for r in records)),
        'vocalization_counts':dict(Counter(r.get('type') for r in records)),
        'license_counts':dict(Counter(r.get('lic') for r in records)),
        'disputed_query_total':disputed.get('numRecordings'),
        'disputed_status_counts':dict(Counter(str(r.get('status')) for r in disputed.get('recordings',[]))),
        'api_documentation':'https://xeno-canto.org/explore/api','search_documentation':'https://xeno-canto.org/help/search',
        'scope':'Cardinal pagination/filter test and bounded disputed-record metadata query; no sensitive coordinates exported'}
    save(ROOT/'experiments/xc-validation.json',evidence)
    print(json.dumps(evidence,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['photos','photo-alternates','audio','xc-validate'])
    args=parser.parse_args();client=SafeClient()
    try:{'photos':expand_photos,'photo-alternates':lambda c:expand_photos(c,alternates=True),'audio':expand_audio,'xc-validate':validate_xc}[args.command](client)
    finally:
        if client.events:save(WORK/'request-logs'/(args.command+'-'+str(time.time_ns())+'.json'),client.events)


if __name__=='__main__':main()
