"""Bootstrap the pinned Analyzer 2.4 bundle in private storage, not another project."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));WORK=ROOT/'experiments/private/phase05'
if importlib.metadata.version('birdnet-analyzer')!='2.4.0':raise SystemExit('This bootstrap is pinned to BirdNET-Analyzer 2.4.0')
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import birdnet_analyzer.config as cfg
from birdnet_analyzer import utils


def main():
    directory=WORK/'models/birdnet';directory.mkdir(parents=True,exist_ok=True);utils.SCRIPT_DIR=str(directory)
    checkpoint=directory/'checkpoints/V2.4';model=checkpoint/'BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite'
    cfg.BIRDNET_MODEL_PATH=str(model);cfg.BIRDNET_LABELS_FILE=str(checkpoint/'BirdNET_GLOBAL_6K_V2.4_Labels.txt')
    cfg.MDATA_MODEL_PATH=str(checkpoint/'BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite')
    if not model.exists():utils.ensure_model_exists()
    record={'analyzer_version':'2.4.0','model_version':'V2.4','model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
        'model_bytes':model.stat().st_size,'source':'official Analyzer 2.4.0 bootstrap URL',
        'source_url':'https://tuc.cloud/index.php/s/886x39f5N3sdsAM/download/V2.4.zip',
        'model_license':'CC-BY-NC-SA-4.0','code_license':'MIT'}
    (directory/'provenance.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))


if __name__=='__main__':main()
