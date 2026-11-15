"""Compile a private local learner release from existing approved media and native profiles."""
from __future__ import annotations
import hashlib
import json
from tooling.discover import PRIVATE, ROOT, save
from tooling.review_store import Store, canonical
from tooling.seasonal import COUNTIES


def build():
    destination=PRIVATE/'local-mvp';destination.mkdir(parents=True,exist_ok=True)
    store=Store()
    try: store.export(destination/'approved-media.json')
    finally: store.close()
    approved=json.loads((destination/'approved-media.json').read_text())
    species=json.loads((ROOT/'experiments/poc-species.json').read_text())
    profiles={code:json.loads((PRIVATE/'occurrence/profiles'/f'{code}.json').read_text()) for code in COUNTIES}
    assets=[]
    for a in approved['assets']:
        # Keep no private source captures, model tensors, credentials or exact locations in runtime payloads.
        keys=['id','species_code','kind','local_path','sha256','creator','source_url','license_url','attribution',
              'source','source_record_id','vocalization','sex','age','plumage','target_bbox_xyxy','original_dimensions',
              'automated_decision','review_state','permitted_modification','presentation_modification_notice']
        assets.append({key:a.get(key) for key in keys})
    payload={'schema':'birdahead-local-release-v1','scope':'personal recreational noncommercial; local-only',
             'species':species,'counties':COUNTIES,'profiles':profiles,'assets':assets,
             'approved_manifest_sha256':hashlib.sha256((destination/'approved-media.json').read_bytes()).hexdigest()}
    payload['id']=hashlib.sha256(canonical(payload).encode()).hexdigest()
    save(destination/'release.json',payload)
    print(json.dumps({'release':payload['id'],'approved_media':len(assets),'counties':len(profiles),
                      'private_output':'experiments/private/local-mvp/release.json'},indent=2))
    return payload


if __name__=='__main__':build()
