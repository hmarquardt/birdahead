"""Reproducible source-agreement benchmark; source labels are proxies, not ground truth."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import resource
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
WORK=ROOT/'experiments/private/phase05'
os.environ['HF_HOME']=str(WORK/'hf-cache');os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import numpy as np
import torch
import open_clip
import psutil
from PIL import Image
from tooling.discover import Client,ROOT as REPO,save,now


def labels():
    client=Client(budget=0)
    taxonomy=client.get('https://api.ebird.org/v2/ref/taxonomy/ebird',{'fmt':'json','cat':'species'})
    codes=set()
    for region in ['US-IN-051','US-IN-125','US-IN-055','US-IN-129','US-IN-083','US-IN-163','US-IN-173']:
        codes.update(client.get('https://api.ebird.org/v2/product/spplist/'+region,{}))
    rows=[{'code':r['speciesCode'],'common':r['comName'],'scientific':r['sciName']} for r in taxonomy if r['speciesCode'] in codes]
    for label in ['a tree branch without a bird','an empty sky','a domestic cat','a domestic dog','a squirrel','a human','a bird illustration','a blurred unidentifiable animal']:
        rows.append({'code':'control-'+str(len(rows)),'common':label,'scientific':''})
    return sorted(rows,key=lambda r:r['code'])


def sync(device):
    if device=='mps':torch.mps.synchronize()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('model',choices=['bioclip','bioclip-2']);parser.add_argument('--incremental',action='store_true',help='Reuse existing predictions and process only new catalog assets');args=parser.parse_args()
    torch.manual_seed(0);torch.set_num_threads(4)
    all_images=[r for r in json.loads((WORK/'catalog.json').read_text()) if r['kind']=='photo']
    prior=None;done=set()
    report_path=WORK/'inference'/(args.model+'.json')
    if args.incremental and report_path.exists():
        prior=json.loads(report_path.read_text());done={p['asset_id'] for p in prior.get('predictions',[])}
    dataset=[r for r in all_images if r['id'] not in done]
    if not dataset:
        print(json.dumps({'model':args.model,'new_images':0,'message':'No new photo assets to infer'},indent=2));return
    candidates=labels();codes=[r['code'] for r in candidates];index={v:i for i,v in enumerate(codes)}
    directory=WORK/'models'/args.model
    provenance=json.loads((directory/'provenance.json').read_text())
    monitor={'peak_rss':0};stop=threading.Event()
    def sample():
        process=psutil.Process()
        while not stop.wait(.05):monitor['peak_rss']=max(monitor['peak_rss'],process.memory_info().rss)
    thread=threading.Thread(target=sample,daemon=True);thread.start();start=time.monotonic()
    device='mps' if torch.backends.mps.is_available() else 'cpu'
    model,_,preprocess=open_clip.create_model_and_transforms('local-dir:'+str(directory),device=device)
    model.eval();tokenizer=open_clip.get_tokenizer('local-dir:'+str(directory))
    sync(device);load_seconds=time.monotonic()-start
    prompts=[]
    for r in candidates:
        prompts.extend([f"a photo of {r['common']}.",f"a photo of {r['common']}, {r['scientific']}."])
    started=time.monotonic();text=[]
    with torch.inference_mode():
        for offset in range(0,len(prompts),32):
            features=model.encode_text(tokenizer(prompts[offset:offset+32]).to(device));features/=features.norm(dim=-1,keepdim=True);text.append(features)
        features=torch.cat(text).reshape(len(candidates),2,-1).mean(dim=1);features/=features.norm(dim=-1,keepdim=True)
    sync(device);text_seconds=time.monotonic()-started
    # Warm the image path; this time is excluded from steady-state throughput.
    with Image.open(ROOT/dataset[0]['local_path']) as im:first=preprocess(im.convert('RGB'))
    warm=time.monotonic()
    with torch.inference_mode():model.encode_image(first.unsqueeze(0).to(device))
    sync(device);warmup_seconds=time.monotonic()-warm
    predictions=[];batch_times=[];start=time.monotonic();driver_peak=0
    with torch.inference_mode():
        for offset in range(0,len(dataset),4):
            batch=dataset[offset:offset+4];batch_start=time.monotonic();images=[]
            for r in batch:
                with Image.open(ROOT/r['local_path']) as im:images.append(preprocess(im.convert('RGB')))
            visual=model.encode_image(torch.stack(images).to(device));visual/=visual.norm(dim=-1,keepdim=True)
            cosine=visual@features.T;scores=(100*cosine).softmax(dim=-1)
            sync(device);batch_times.append(time.monotonic()-batch_start)
            cosine=cosine.float().cpu().numpy();scores=scores.float().cpu().numpy()
            for r,similarities,relative in zip(batch,cosine,scores):
                order=np.argsort(similarities)[::-1];source=index[r['species_code']]
                predictions.append({'asset_id':r['id'],'sha256':r['sha256'],'source_species':r['species_code'],
                    'top_species':codes[int(order[0])],'source_rank':int(np.where(order==source)[0][0])+1,
                    'source_cosine':float(similarities[source]),'top_cosine':float(similarities[order[0]]),
                    'top_margin':float(similarities[order[0]]-similarities[order[1]]),
                    'source_relative_score':float(relative[source]),'relative_score_is_probability':False,
                    'top5':[{'code':codes[int(i)],'cosine':float(similarities[i])} for i in order[:5]],
                    'all_cosines':{code:float(value) for code,value in zip(codes,similarities)},
                    'contributor_id':r['contributor_id'],'source_uploaded_after_training':None})
            if device=='mps':driver_peak=max(driver_peak,torch.mps.driver_allocated_memory())
            if offset%20==0:print(args.model,offset+len(batch),'/',len(dataset),flush=True)
    elapsed=time.monotonic()-start
    # A small CPU comparison uses the same loaded checkpoint/preprocessing.
    model.to('cpu');gc.collect()
    if device=='mps':torch.mps.empty_cache()
    cpu_images=[]
    for r in dataset[:8]:
        with Image.open(ROOT/r['local_path']) as im:cpu_images.append(preprocess(im.convert('RGB')))
    with torch.inference_mode():model.encode_image(torch.stack(cpu_images[:1]))
    started=time.monotonic()
    with torch.inference_mode():model.encode_image(torch.stack(cpu_images))
    cpu_seconds=time.monotonic()-started
    stop.set();thread.join()
    predictions=(prior.get('predictions',[]) if prior else [])+predictions
    provenance=prior.get('model',provenance) if prior else provenance
    report={'at':now(),'model':provenance,'packages':{p:importlib.metadata.version(p) for p in ['torch','torchvision','open-clip-torch']},
        'device':device,'precision':'fp32','threads':4,'batch_size':4,'candidate_labels':len(candidates),
        'candidate_label_sha256':hashlib.sha256(json.dumps(candidates,sort_keys=True).encode()).hexdigest(),
        'image_count':len(predictions),'new_images':len(dataset),'incremental':bool(prior),
        'load_seconds':round(load_seconds,3),'text_embedding_seconds':round(text_seconds,3),
        'warmup_seconds':round(warmup_seconds,3),'image_processing_seconds':round(elapsed,3),
        'images_per_second':round(len(dataset)/elapsed,3),'median_batch_seconds':round(float(np.median(batch_times)),3),
        'cpu_comparison_images':len(cpu_images),'cpu_comparison_seconds':round(cpu_seconds,3),
        'peak_process_rss_bytes':monitor['peak_rss'],'peak_mps_driver_allocated_bytes':driver_peak,
        'source_top1_agreement':sum(r['source_rank']==1 for r in predictions),
        'accuracy_claim':'Source-label agreement only. No independently adjudicated accuracy or calibrated probabilities.',
        'prompts':'two common/scientific photo prompts; mean normalized text embeddings; center-crop source images',
        'predictions':predictions}
    save(report_path,report)
    print(json.dumps({k:v for k,v in report.items() if k!='predictions'},indent=2),flush=True)


if __name__=='__main__':main()
