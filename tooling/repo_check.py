"""Check staged/tracked files for restricted artifacts and locally known credentials."""
from pathlib import Path
import os
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MEDIA = {'.jpg','.jpeg','.png','.webp','.gif','.mp3','.wav','.ogg','.flac','.m4a','.mp4','.mov','.zip','.gz','.parquet','.sqlite','.db','.bin','.pth','.pt','.onnx','.tflite','.safetensors','.h5','.keras'}
PRIVATE_PARTS = {'private', '.venv', 'node_modules', 'dist', '.wrangler', '__pycache__'}
RESTRICTED_PREFIXES = ('experiments/photo-candidates/','experiments/commons-candidates/','experiments/request-logs/','experiments/phase05/')
RESTRICTED_FILES = {'experiments/sample-assets.json','experiments/audio-samples.json'}


def known_secrets():
    values = set()
    path = Path.home() / '.config/secrets/shared.env'
    pairs = list(os.environ.items())
    if path.exists():
        for line in path.read_text().splitlines():
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == 'export':
                parts = parts[1:]
            if len(parts) == 1 and '=' in parts[0]:
                pairs.append(parts[0].split('=', 1))
    for key, value in pairs:
        if any(x in key.upper() for x in ['TOKEN','SECRET','PASSWORD','API_KEY']) and len(value) >= 12:
            values.add(value.encode())
    return values


def main():
    names = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0')
    secrets = known_secrets()
    issues = []
    for name in filter(None, names):
        path = Path(name)
        public_icon = name.startswith('app/public/') and path.suffix.lower() == '.png'
        if ((not public_icon) and (PRIVATE_PARTS.intersection(path.parts) or path.suffix.lower() in MEDIA or path.name.startswith(('.env','.dev.vars'))
            or path.name.endswith('_barchart.txt') or path.name.startswith(('ebd_', 'ebd_sampling_'))
            or name.startswith(RESTRICTED_PREFIXES) or name in RESTRICTED_FILES)):
            issues.append(f'restricted artifact: {name}')
            continue
        # Scan the index, which is exactly what a commit would publish.
        raw = subprocess.check_output(['git','show',f':{name}'], cwd=ROOT)
        if any(value in raw for value in secrets):
            issues.append(f'known credential value in: {name}')
    if issues:
        print('\n'.join(issues))
        return 1
    print(f'PASS: {sum(bool(n) for n in names)} indexed files; restricted artifacts and known credentials excluded.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
