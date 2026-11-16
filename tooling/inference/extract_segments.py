"""Extract source-species-dominant intervals from intermittent recordings.

This is not synthesis: every clip is a byte-faithful interval of a real,
licensed recording. The parent stays in the catalog and a new derivative record
records parent digest, interval, tool recipe, rights and attribution. BirdNET is
re-run on the clip by the normal incremental inference step before curation.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import math
import sys
from math import gcd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
WORK=ROOT/'experiments/private/phase05'
import numpy as np
import scipy.signal
import soundfile as sf
from tooling.discover import save,now
from tooling.teaching_universe import PAIR_NAMES

RISKY={name for pair in PAIR_NAMES for name in pair}
MAX_CLIPS=150
MAX_PER_PARENT=2
MAX_CLIP_SECONDS=30.0
BYTE_BUDGET=150_000_000


def deciseconds(value):
    return int(round(float(value)*10))


def runs(segments,threshold):
    good=[s.get('source_rank')==1 and (s.get('source_score') or 0)>=threshold and (s.get('top_margin') or 0)>=.10 for s in segments]
    output=[];start=None
    for index,ok in enumerate(good+[False]):
        if ok and start is None:start=index
        if not ok and start is not None:
            output.append((start,index-1));start=None
    return output


def main():
    catalog=json.loads((WORK/'catalog.json').read_text())
    audio_report=json.loads((WORK/'inference/birdnet.json').read_text())
    predictions={row['asset_id']:row for row in audio_report['predictions']}
    calibration=json.loads((WORK/'calibration.json').read_text()) if (WORK/'calibration.json').exists() else {}
    audio_params=calibration.get('audio',{}).get('parameters',{})
    existing={asset['id'] for asset in catalog}
    parent_counts={}
    for asset in catalog:
        if isinstance(asset.get('derivative_of'),dict):
            parent_counts[asset['derivative_of'].get('asset_id')]=parent_counts.get(asset['derivative_of'].get('asset_id'),0)+1
    extracted=[];skipped={};total_bytes=0
    for asset in catalog:
        if asset.get('kind')!='audio' or isinstance(asset.get('derivative_of'),dict):continue
        if asset.get('automated_decision',{}).get('status') in {'automatically_accepted','human_approved','expert_verified'}:continue
        if len(extracted)>=MAX_CLIPS or total_bytes>=BYTE_BUDGET:break
        if parent_counts.get(asset['id'],0)>=MAX_PER_PARENT:continue
        if not asset.get('derivatives_permitted'):
            skipped['license_does_not_permit_derivative']=skipped.get('license_does_not_permit_derivative',0)+1;continue
        prediction=predictions.get(asset['id'])
        if not prediction:
            skipped['no_birdnet_prediction']=skipped.get('no_birdnet_prediction',0)+1;continue
        base=.97 if asset.get('common_name') in RISKY else .90
        threshold=max(base,(audio_params.get(asset['species_code'],{}) or {}).get('min_score',0) or 0)
        candidates=runs(prediction.get('segments',[]),threshold)
        if not candidates:
            skipped['no_two_adjacent_dominant_windows']=skipped.get('no_two_adjacent_dominant_windows',0)+1;continue
        first,last=max(candidates,key=lambda run:run[1]-run[0])
        if last-first+1<2:
            skipped['run_too_short']=skipped.get('run_too_short',0)+1;continue
        segments=prediction['segments']
        start=max(0.0,float(segments[first]['start'])-.5);end=min(float(prediction['duration_seconds']),float(segments[last]['end'])+.5)
        if end-start>MAX_CLIP_SECONDS:end=start+MAX_CLIP_SECONDS
        if end-start<6:
            skipped['clip_too_short']=skipped.get('clip_too_short',0)+1;continue
        clip_id=f"{asset['id']}-clip-{deciseconds(start):04d}-{deciseconds(end):04d}"
        if clip_id in existing:continue
        try:
            wave,sample_rate=sf.read(ROOT/asset['local_path'],always_2d=True,dtype='float32')
            mono=wave.mean(axis=1)
            if sample_rate!=48000:
                divisor=gcd(int(sample_rate),48000)
                mono=scipy.signal.resample_poly(mono,48000//divisor,int(sample_rate)//divisor).astype('float32')
                sample_rate=48000
            start_sample=max(0,int(start*sample_rate));end_sample=min(len(mono),int(end*sample_rate))
            clip=mono[start_sample:end_sample]
            if len(clip)<sample_rate*3:
                skipped['decoded_clip_too_short']=skipped.get('decoded_clip_too_short',0)+1;continue
            dest=WORK/'media'/(clip_id+'.flac')
            dest.parent.mkdir(parents=True,exist_ok=True)
            try:sf.write(dest,clip,sample_rate,format='FLAC',subtype='PCM_16');media_format='audio/flac'
            except Exception:
                dest=WORK/'media'/(clip_id+'.wav');sf.write(dest,clip,sample_rate,format='WAV',subtype='PCM_16');media_format='audio/wav'
            raw=dest.read_bytes()
        except Exception:
            skipped['audio_decode_or_write_failed']=skipped.get('audio_decode_or_write_failed',0)+1;continue
        record={**asset,
            'id':clip_id,'asset_id':clip_id,'derivative_of':{'asset_id':asset['id'],'sha256':asset.get('sha256'),'interval_seconds':[round(start,3),round(end,3)]},
            'derivative_recipe':{'tool':'birdnet-segment-extraction','version':'1.0','model':audio_report.get('model'),
                'threshold':round(threshold,4),'dominant_windows':last-first+1,'recipe':'longest contiguous source-dominant run; 0.5s padding; mono 48kHz; no other edits'},
            'local_path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
            'media_format':media_format,'technical_metrics':{**asset.get('technical_metrics',{}),'duration_seconds':round(len(clip)/sample_rate,3),
                'sample_rate_hz':sample_rate,'channels':1,'peak_amplitude':float(np.max(np.abs(clip))),'rms_amplitude':float(np.sqrt(np.mean(clip**2))),
                'clipped_sample_fraction':float(np.mean(np.abs(clip)>=.999)),'parent_duration_seconds':prediction.get('duration_seconds')},
            'attribution':(asset.get('attribution') or '')+f"; verified segment clip {start:.1f}-{end:.1f}s",
            'presentation_modification_notice':f"Derived clip {start:.1f}-{end:.1f}s of the original recording; source file unchanged.",
            'source_verified':True,'machine_screened':False,'human_approved':False,'expert_verified':False,
            'rights_approved':False,'biology_approved':False,'review_state':'candidate','model_results':[],'duplicate_flags':[],'audit_selected':False,
            'source_evidence':{**asset.get('source_evidence',{}),'derivative_clip_of':asset['id'],'clip_interval_seconds':[round(start,3),round(end,3)],
                'source_dominant_windows':last-first+1,'clip_threshold':round(threshold,4),'source_assertion_not_independent_ground_truth':True},
            'acquisition_pass':'phase two verified segment extraction','retrieved_at':now()}
        record.pop('automated_decision',None)
        catalog.append(record);existing.add(clip_id);parent_counts[asset['id']]=parent_counts.get(asset['id'],0)+1
        total_bytes+=len(raw);extracted.append({'asset_id':clip_id,'parent':asset['id'],'species_code':asset['species_code'],'seconds':round(len(clip)/sample_rate,3),'bytes':len(raw)})
        save(WORK/'catalog.json',catalog)
        print('clip',clip_id,asset['common_name'],round(len(clip)/sample_rate,1),'s',flush=True)
    report={'schema':'birdahead-audio-segment-extraction-v1','at':now(),'extracted':len(extracted),
        'total_clip_seconds':round(sum(row['seconds'] for row in extracted),3),'total_bytes':total_bytes,
        'max_clips':MAX_CLIPS,'max_per_parent':MAX_PER_PARENT,'max_clip_seconds':MAX_CLIP_SECONDS,'byte_budget':BYTE_BUDGET,
        'threshold_policy':'species calibration when available, otherwise .90 low-risk/.97 confusion pair; two adjacent dominant windows and .10 margin required',
        'skipped':skipped,'clip_species_counts':dict(__import__('collections').Counter(row['species_code'] for row in extracted)),'limitation':'A clip is a real interval with model evidence, not independent ground truth; curation gates still apply.'}
    save(ROOT/'experiments/audio-segments.json',report);print(json.dumps({k:v for k,v in report.items() if k!='clips'},indent=2))


if __name__=='__main__':main()
