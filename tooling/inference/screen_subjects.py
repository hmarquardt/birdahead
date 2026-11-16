"""Conservative target-clarity screen; detections do not prove species identity.

One source-consistent crop is required when several bird boxes are present. A
whole-image fallback is permitted only for low-risk species with a larger
classifier margin, and never substitutes for a detected bird in a confusion pair.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));WORK=ROOT/'experiments/private/phase05'
os.environ['TORCH_HOME']=str(WORK/'torch-cache')
import torch
from PIL import Image
from torchvision.models.detection import ssdlite320_mobilenet_v3_large,SSDLite320_MobileNet_V3_Large_Weights
from torchvision.transforms.functional import to_tensor
from tooling.discover import save
from tooling.inference.benchmark_images import labels
from tooling.teaching_universe import PAIR_NAMES
import open_clip

RISKY={name for pair in PAIR_NAMES for name in pair}


def main():
    torch.set_num_threads(4);torch.manual_seed(0);weights=SSDLite320_MobileNet_V3_Large_Weights.COCO_V1
    start=time.monotonic();model=ssdlite320_mobilenet_v3_large(weights=weights).eval();load=time.monotonic()-start
    bird=weights.meta['categories'].index('bird');assets=[a for a in json.loads((WORK/'catalog.json').read_text()) if a['kind']=='photo']
    device='mps' if torch.backends.mps.is_available() else 'cpu'
    classifier,_,preprocess=open_clip.create_model_and_transforms('local-dir:'+str(WORK/'models/bioclip-2'),device=device)
    classifier.eval();tokenizer=open_clip.get_tokenizer('local-dir:'+str(WORK/'models/bioclip-2'));classes=labels();codes=[r['code'] for r in classes]
    prompts=[prompt for r in classes for prompt in [f"a photo of {r['common']}.",f"a photo of {r['common']}, {r['scientific']}."]]
    with torch.inference_mode():
        chunks=[]
        for offset in range(0,len(prompts),32):
            text=classifier.encode_text(tokenizer(prompts[offset:offset+32]).to(device));chunks.append(text/text.norm(dim=-1,keepdim=True))
        text=torch.cat(chunks).reshape(len(classes),2,-1).mean(dim=1);text/=text.norm(dim=-1,keepdim=True)

    def classify(image):
        if asset['species_code'] not in codes:
            return {'top_species':None,'source_cosine':None,'margin':0.0,'source_agrees':False,
                    'inference_only_crop':True,'pixels_modified_for_delivery':False,
                    'error':'source species absent from local classifier label set'}
        with torch.inference_mode():
            visual=classifier.encode_image(preprocess(image.convert('RGB')).unsqueeze(0).to(device));visual/=visual.norm(dim=-1,keepdim=True)
            scores=(visual@text.T)[0].cpu();top=torch.argsort(scores,descending=True);source=codes.index(asset['species_code'])
        return {'top_species':codes[int(top[0])],'source_cosine':float(scores[source]),
                'margin':float(scores[top[0]]-scores[top[1]]),'source_agrees':codes[int(top[0])]==asset['species_code'],
                'inference_only_crop':True,'pixels_modified_for_delivery':False}

    rows=[];start=time.monotonic();modes={}
    with torch.inference_mode():
        for asset in assets:
            with Image.open(ROOT/asset['local_path']) as im:
                original=im.convert('RGB');width,height=original.size;prediction=model([to_tensor(original)])[0]
                boxes=[]
                for label,score,box in zip(prediction['labels'],prediction['scores'],prediction['boxes']):
                    if int(label)==bird and float(score)>=.45:boxes.append({'box_xyxy':box.tolist(),'detector_score':float(score)})
                boxes=sorted(boxes,key=lambda item:-item['detector_score'])[:3]
                localized=None;reason=None;mode=None
                if len(boxes)==1:
                    x1,y1,x2,y2=boxes[0]['box_xyxy'];pad=.08*max(x2-x1,y2-y1)
                    bounds=[max(0,int(x1-pad)),max(0,int(y1-pad)),min(width,int(x2+pad)),min(height,int(y2+pad))]
                    localized={**classify(original.crop(bounds)),'bbox_xyxy':bounds};mode='single_detected_bird'
                elif len(boxes)>1:
                    candidates=[]
                    for box in boxes:
                        x1,y1,x2,y2=box['box_xyxy'];pad=.08*max(x2-x1,y2-y1)
                        bounds=[max(0,int(x1-pad)),max(0,int(y1-pad)),min(width,int(x2+pad)),min(height,int(y2+pad))]
                        result={**classify(original.crop(bounds)),'bbox_xyxy':bounds}
                        if result['source_agrees'] and result['margin']>=.02:candidates.append(result)
                    mode='multiple_detections'
                    if len(candidates)==1:localized=candidates[0];reason='one of several detected crops is source-consistent'
                    else:reason='multiple or no source-consistent crops among several detected birds'
                else:
                    mode='no_bird_detected'
                    result={**classify(original),'bbox_xyxy':None}
                    if asset.get('common_name') not in RISKY and result['source_agrees'] and result['margin']>=.04:
                        localized=result;reason='whole-image fallback with conservative margin'
                    else:reason='no detected bird and whole-image fallback not eligible'
            passed=bool(localized and localized['source_agrees'] and localized['margin']>=.015)
            modes[mode]=modes.get(mode,0)+1
            rows.append({'asset_id':asset['id'],'sha256':asset['sha256'],'bird_boxes':boxes,'bird_count_at_threshold':len(boxes),
                         'screen_mode':mode,'screen_reason':reason,'localized_classification':localized,
                         'screen_passed':passed,
                         'limitation':'Detector can miss small/obscured birds. Count is a screening signal, not proof of a single subject or species identity.'})
    checkpoint=WORK/'torch-cache/hub/checkpoints'/weights.url.rsplit('/',1)[-1]
    report={'model':'torchvision SSDLite320 MobileNetV3 Large COCO_V1','torchvision':importlib.metadata.version('torchvision'),
            'checkpoint_url':weights.url,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'checkpoint_bytes':checkpoint.stat().st_size,'backend':'CPU, four threads','threshold':.45,'image_count':len(assets),
            'localized_species_model':json.loads((WORK/'models/bioclip-2/provenance.json').read_text()),
            'load_and_download_seconds':round(load,3),'processing_seconds':round(time.monotonic()-start,3),
            'screen_modes':modes,'screen_passed':sum(r['screen_passed'] for r in rows),
            'one_bird':sum(r['bird_count_at_threshold']==1 for r in rows),'multiple_birds':sum(r['bird_count_at_threshold']>1 for r in rows),
            'no_bird_detected':sum(r['bird_count_at_threshold']==0 for r in rows),'predictions':rows}
    save(WORK/'inference/subjects.json',report);print(json.dumps({k:v for k,v in report.items() if k!='predictions'},indent=2))


if __name__=='__main__':main()
