"""Conservative bird-count screen; object detections do not prove species identity."""
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
import open_clip


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
    rows=[];start=time.monotonic()
    with torch.inference_mode():
        for a in assets:
            with Image.open(ROOT/a['local_path']) as im:image=to_tensor(im.convert('RGB'))
            prediction=model([image])[0];boxes=[]
            for label,score,box in zip(prediction['labels'],prediction['scores'],prediction['boxes']):
                if int(label)==bird and float(score)>=.45:boxes.append({'box_xyxy':box.tolist(),'detector_score':float(score)})
            localized=None
            if len(boxes)==1:
                with Image.open(ROOT/a['local_path']) as original:
                    x1,y1,x2,y2=boxes[0]['box_xyxy'];pad=.08*max(x2-x1,y2-y1)
                    bounds=[max(0,int(x1-pad)),max(0,int(y1-pad)),min(original.width,int(x2+pad)),min(original.height,int(y2+pad))]
                    crop=preprocess(original.convert('RGB').crop(bounds)).unsqueeze(0).to(device)
                visual=classifier.encode_image(crop);visual/=visual.norm(dim=-1,keepdim=True);scores=(visual@text.T)[0].cpu()
                top=torch.argsort(scores,descending=True);source=codes.index(a['species_code'])
                localized={'bbox_xyxy':bounds,'top_species':codes[int(top[0])],'source_cosine':float(scores[source]),'margin':float(scores[top[0]]-scores[top[1]]),
                           'source_agrees':codes[int(top[0])]==a['species_code'],'inference_only_crop':True,'pixels_modified_for_delivery':False}
            rows.append({'asset_id':a['id'],'sha256':a['sha256'],'bird_boxes':boxes,'bird_count_at_threshold':len(boxes),'localized_classification':localized,
                         'screen_passed':bool(localized and localized['source_agrees'] and localized['margin']>=.015),
                         'limitation':'Detector can miss small/obscured birds. Count is a screening signal, not proof of a single subject or species identity.'})
    checkpoint=WORK/'torch-cache/hub/checkpoints'/weights.url.rsplit('/',1)[-1]
    report={'model':'torchvision SSDLite320 MobileNetV3 Large COCO_V1','torchvision':importlib.metadata.version('torchvision'),
            'checkpoint_url':weights.url,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'checkpoint_bytes':checkpoint.stat().st_size,'backend':'CPU, four threads','threshold':.45,'image_count':len(assets),
            'localized_species_model':json.loads((WORK/'models/bioclip-2/provenance.json').read_text()),
            'load_and_download_seconds':round(load,3),'processing_seconds':round(time.monotonic()-start,3),
            'one_bird':sum(r['bird_count_at_threshold']==1 for r in rows),'multiple_birds':sum(r['bird_count_at_threshold']>1 for r in rows),
            'no_bird_detected':sum(r['bird_count_at_threshold']==0 for r in rows),'predictions':rows}
    save(WORK/'inference/subjects.json',report);print(json.dumps({k:v for k,v in report.items() if k!='predictions'},indent=2))


if __name__=='__main__':main()
