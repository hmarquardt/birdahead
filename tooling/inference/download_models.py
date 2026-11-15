"""Download only requested public model weights into ignored local storage."""
from pathlib import Path
import hashlib
import json
import shutil
import time
import urllib.request
import os

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'experiments/private/phase05'
os.environ['HF_HOME']=str(WORK/'hf-cache')
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from huggingface_hub import hf_hub_download


def main():
    records=[]
    for name in ['bioclip','bioclip-2']:
        directory=WORK/'models'/name;directory.mkdir(parents=True,exist_ok=True)
        evidence=directory/'provenance.json'
        if evidence.exists():
            records.append(json.loads(evidence.read_text()));continue
        with urllib.request.urlopen('https://huggingface.co/api/models/imageomics/'+name,timeout=30) as response:info=json.load(response)
        filenames={r['rfilename'] for r in info['siblings']}
        options=['open_clip_model.safetensors','open_clip_pytorch_model.safetensors','model.safetensors','open_clip_pytorch_model.bin']
        filename=next((x for x in options if x in filenames),None)
        if not filename:raise ValueError('Requested model checkpoint not found')
        started=time.monotonic()
        for file in ['open_clip_config.json',filename,'README.md']:
            src=Path(hf_hub_download('imageomics/'+name,file,revision=info['sha'],cache_dir=str(WORK/'hf-cache'),token=False))
            dst=directory/file
            if not dst.exists():dst.symlink_to(src.resolve())
        checkpoint=directory/filename
        digest=hashlib.sha256()
        with checkpoint.open('rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024),b''):digest.update(chunk)
        record={'model':'imageomics/'+name,'revision':info['sha'],'filename':filename,'bytes':checkpoint.stat().st_size,
                'sha256':digest.hexdigest(),'license':info.get('cardData',{}).get('license'),
                'download_seconds':round(time.monotonic()-started,3),'source_url':'https://huggingface.co/imageomics/'+name}
        evidence.write_text(json.dumps(record,indent=2)+'\n');records.append(record);print(json.dumps(record),flush=True)
    (WORK/'model-provenance.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
