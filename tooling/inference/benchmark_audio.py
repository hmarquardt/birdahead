"""BirdNET-Analyzer 2.4 local inference without geography priors or source-label restriction."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));WORK=ROOT/'experiments/private/phase05'
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import numpy as np
import psutil
import soundfile as sf
import scipy.signal
from tooling.discover import save,now


def main():
    process=psutil.Process();peak={'rss':process.memory_info().rss};stop=threading.Event()
    def monitor():
        while not stop.wait(.05):peak['rss']=max(peak['rss'],process.memory_info().rss)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    started=time.monotonic()
    import birdnet_analyzer.config as cfg
    from birdnet_analyzer import model
    directory=WORK/'models/birdnet/checkpoints/V2.4'
    model_path=directory/'BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite'
    labels=(directory/'BirdNET_GLOBAL_6K_V2.4_Labels.txt').read_text().splitlines()
    cfg.MODEL_PATH=str(model_path);cfg.TFLITE_THREADS=4;cfg.CUSTOM_CLASSIFIER=None;cfg.USE_PERCH=False
    all_audio=[r for r in json.loads((WORK/'catalog.json').read_text()) if r['kind']=='audio']
    report_path=WORK/'inference/birdnet.json'
    prior=json.loads(report_path.read_text()) if report_path.exists() else None
    done={r['asset_id'] for r in (prior or {}).get('predictions',[])}
    audio=[r for r in all_audio if r['id'] not in done]
    if not audio:
        print(json.dumps({'new_audio_files':0,'message':'No new audio assets to infer'},indent=2));stop.set();thread.join();return
    model.load_model();load_seconds=time.monotonic()-started
    warm=time.monotonic();model.predict(np.zeros((1,144000),dtype='float32'));warmup=time.monotonic()-warm
    rows=[];total_duration=0;segments=0;start=time.monotonic()
    for record in audio:
        t=time.monotonic();wave,sample_rate=sf.read(ROOT/record['local_path'],always_2d=True,dtype='float32');mono=wave.mean(axis=1)
        duration=len(mono)/sample_rate;total_duration+=duration
        peak_level=float(np.max(np.abs(mono)));rms=float(np.sqrt(np.mean(mono**2)));clipped=float(np.mean(np.abs(mono)>=.999))
        if sample_rate!=48000:
            from math import gcd
            divisor=gcd(sample_rate,48000);mono=scipy.signal.resample_poly(mono,48000//divisor,sample_rate//divisor).astype('float32')
        candidates=[]
        # Full recording, independent three-second windows; no label-aware window selection before inference.
        starts=list(range(0,max(1,len(mono)-144000+1),144000))
        for offset in range(0,len(starts),8):
            offsets=starts[offset:offset+8];batch=[]
            for position in offsets:
                segment=mono[position:position+144000]
                if len(segment)<144000:segment=np.pad(segment,(0,144000-len(segment)))
                batch.append(segment)
            logits=model.predict(np.stack(batch));scores=model.flat_sigmoid(np.array(logits),sensitivity=-1,bias=1.0)
            for position,prediction in zip(offsets,scores):
                order=np.argsort(prediction)[::-1]
                target_indices=[i for i,label in enumerate(labels) if label.split('_')[-1]==record['common_name'] or label.split('_')[0]==record['scientific_name']]
                target=max(target_indices,key=lambda i:prediction[i]) if target_indices else None
                candidates.append({'start':position/48000,'end':min((position+144000)/48000,duration),
                    'top_label':labels[int(order[0])],'top_score':float(prediction[order[0]]),
                    'source_score':float(prediction[target]) if target is not None else None,
                    'source_rank':int(np.where(order==target)[0][0])+1 if target is not None else None,
                    'top_margin':float(prediction[order[0]]-prediction[order[1]]),
                    'top5':[{'label':labels[int(i)],'score':float(prediction[i])} for i in order[:5]]})
            segments+=len(offsets)
        # A compact acoustic fingerprint is a near-duplicate flag, not identification.
        n=4096;_,_,spectrum=scipy.signal.stft(mono[:min(len(mono),48000*60)],fs=48000,nperseg=n)
        energy=np.log1p(np.abs(spectrum)).mean(axis=1);fingerprint=np.array([x.mean() for x in np.array_split(energy,64)])
        norm=np.linalg.norm(fingerprint);fingerprint=fingerprint/norm if norm else fingerprint
        best=max(candidates,key=lambda r:r['source_score'] or 0)
        row={'asset_id':record['id'],'sha256':record['sha256'],'source_species':record['species_code'],'source_common_name':record['common_name'],
            'source_label_present':any(c['source_score'] is not None for c in candidates),'segments':candidates,
            'best_source_score':best['source_score'],'best_source_interval':[best['start'],best['end']],
            'source_dominant_windows':sum(r['source_rank']==1 for r in candidates),'window_count':len(candidates),
            'duration_seconds':duration,'inference_and_processing_seconds':round(time.monotonic()-t,4),
            'technical_metrics':{'sample_rate_hz':sample_rate,'channels':wave.shape[1],'peak_amplitude':peak_level,'rms_amplitude':rms,'clipped_sample_fraction':clipped},
            'acoustic_fingerprint_64':fingerprint.tolist(),'score_is_probability':False}
        rows.append(row);save(WORK/'inference/birdnet-partial.json',{'predictions':(prior.get('predictions',[]) if prior else [])+rows})
        print('BirdNET',len(rows),'/',len(audio),record['common_name'],flush=True)
    elapsed=time.monotonic()-start;stop.set();thread.join()
    merged=(prior.get('predictions',[]) if prior else [])+rows
    prior_seconds=sum(r.get('duration_seconds',0) for r in (prior.get('predictions',[]) if prior else []))
    report={'at':now(),'model':'BirdNET_GLOBAL_6K_V2.4_FP32','model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'labels_sha256':hashlib.sha256((directory/'BirdNET_GLOBAL_6K_V2.4_Labels.txt').read_bytes()).hexdigest(),
        'model_bytes':model_path.stat().st_size,'model_license':'CC-BY-NC-SA-4.0','code_license':'MIT',
        'packages':{p:importlib.metadata.version(p) for p in ['birdnet-analyzer','tensorflow','numpy','soundfile']},
        'backend':'TensorFlow Lite CPU, four threads; no Apple Metal delegate configured','load_seconds':round(load_seconds,3),
        'warmup_seconds':round(warmup,3),'audio_files':len(merged),'new_audio_files':len(audio),
        'incremental':bool(prior),'total_audio_seconds':round(prior_seconds+total_duration,3),'windows':segments,
        'new_audio_seconds':round(total_duration,3),'processing_seconds':round(elapsed,3),
        'audio_seconds_per_wall_second':round(total_duration/elapsed,3),
        'peak_process_rss_bytes':peak['rss'],'label_count':len(labels),'geography_prior':False,'restricted_species_list':False,
        'scores':'BirdNET sigmoid activations; not calibrated probabilities','predictions':merged}
    save(report_path,report);print(json.dumps({k:v for k,v in report.items() if k!='predictions'},indent=2))


if __name__=='__main__':main()
