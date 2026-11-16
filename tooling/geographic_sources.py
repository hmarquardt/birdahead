"""Offline source/resource preflight; explicit bounded API-v2 and approved direct transfers.

No portal automation or EBD endpoint discovery. Direct URLs are owner/provider supplied in
an ignored private plan. Downloading requires a pinned grant and coherent regional scope.
"""
from __future__ import annotations
import argparse
import gzip
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import zipfile

from tooling.discover import PRIVATE, ROOT, credential, now, save
from tooling.geography_io import Limits, Transfer, digest, private_path


def preflight():
    root=private_path(PRIVATE/'geography')
    physical=None
    if platform.system()=='Darwin':
        physical=int(subprocess.check_output(['sysctl','-n','hw.memsize']))
    elif hasattr(os,'sysconf'):
        physical=os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
    artifacts=[]
    for area in [PRIVATE/'geography',PRIVATE/'occurrence/incoming']:
        for path in sorted(area.rglob('*')):
            if path.is_file() and path.suffix in ['.txt','.zip','.gz','.tif','.csv']:
                artifacts.append({'kind':'histogram_reference' if 'barchart' in path.name else 'private_geography_artifact',
                                  'filename':path.name,'bytes':path.stat().st_size,'sha256':digest(path)})
    return {'schema':'birdahead-geographic-preflight-v1','at':now(),'evidence':'observed experiment',
            'credentials':{k:bool(credential(k)) for k in ['EBIRD_API_KEY','EBIRD_ST_API_KEY']},
            'credential_policy':'environment overrides ~/.config/secrets/shared.env; values omitted',
            'disk':shutil.disk_usage(root)._asdict(),'physical_memory_bytes':physical,'logical_cpus':os.cpu_count(),
            'limits':Limits().__dict__,'artifacts':artifacts,
            'ebd_approval':'unverified: API keys are independent grants; authenticated portal not inspected',
            'public_intended_use':'BirdAhead is a public, noncommercial educational bird-learning application at birdahead.com. Raw EBD/SED, exact coordinates and authenticated responses remain private. Only eligible compact attributed derived geographic summaries are distributed; optional household progress remains private.'}


def recent_probe():
    key=credential('EBIRD_API_KEY')
    if not key:raise ValueError('Recent API key unavailable')
    transfer=Transfer({'api.ebird.org'},Limits(max_download_bytes=100_000),max_requests=1)
    # One regional presence sample, never the population for a denominator.
    with transfer.open('https://api.ebird.org/v2/data/obs/US-IN/recent?back=7&maxResults=5',headers={'X-eBirdApiToken':key}) as response:
        raw=response.read(100_001)
        if len(raw)>100_000 or key.encode() in raw:raise ValueError('Unsafe recent response')
        data=json.loads(raw)
        if not isinstance(data,list):raise ValueError('Unexpected recent response schema')
    save(PRIVATE/'geography/recent/US-IN.json',{'at':now(),'signal':'recent_presence','records':data})
    return {'at':now(),'evidence':'observed experiment','endpoint':'https://api.ebird.org/v2/data/obs/US-IN/recent',
            'parameters':{'back':7,'maxResults':5},'requests':1,'http_status':200,'bytes':len(raw),'records':len(data),
            'complete_checklist_denominator':False,'signal':'recent_presence','public_raw_data':False}


def acquire(plan_path, output, limits=Limits()):
    plan_path=Path(plan_path).resolve()
    if not plan_path.is_relative_to(PRIVATE.resolve()):raise ValueError('Authorized direct URL plan must remain private')
    plan=json.loads(plan_path.read_text())
    if not plan.get('grant_reference') or not plan.get('snapshot_id') or not plan.get('states') or plan.get('all_species') is not True or plan.get('all_months') is not True:
        raise ValueError('Approved regional all-species/months snapshot required')
    if set(plan['artifacts'])!={'ebd','sed'}:raise ValueError('Paired EBD/SED acquisition required')
    if any(a.get('snapshot_id')!=plan['snapshot_id'] for a in plan['artifacts'].values()):raise ValueError('Mismatched snapshot pair')
    root=private_path(output)
    transfer=Transfer(plan['approved_hosts'],limits,max_requests=8)
    # Preflight BOTH members before any GET; never infer sizes or raise a budget.
    sizes={kind:transfer.metadata(a['url'])['bytes'] for kind,a in plan['artifacts'].items()}
    if any(not size for size in sizes.values()) or sum(sizes.values())>limits.max_download_bytes:
        raise ValueError('Paired source sizes unknown or exceed download ceiling')
    limits.check_disk(root,sum(sizes.values())+limits.max_input_bytes+limits.max_spill_bytes)
    result={}
    for kind,a in plan['artifacts'].items():
        filename=a['filename']
        if Path(filename).name!=filename:raise ValueError('Artifact name must not contain a path')
        result[kind]=transfer.download(a['url'],root/filename,expected_sha256=a['sha256'])
    save(root/'acquisition.json',{'snapshot_id':plan['snapshot_id'],'at':now(),'artifacts':result,'events':transfer.events})
    return result


def unpack(source, destination, limits=Limits()):
    """Bounded one-file gzip/zip expansion; never extract member paths or an entire archive tree."""
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if not source.is_relative_to(PRIVATE.resolve()):raise ValueError('Private source required')
    private_path(destination.parent)
    if destination.exists():raise ValueError('Immutable expanded source already exists')
    temporary=destination.with_suffix(destination.suffix+'.part')
    if temporary.exists():raise ValueError('Previous expansion partial exists; choose a fresh destination')
    archive=None
    if source.suffix=='.gz':stream=gzip.open(source,'rb')
    elif source.suffix=='.zip':
        archive=zipfile.ZipFile(source)
        members=[m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith(('.txt','.tsv'))]
        if len(members)!=1 or members[0].file_size>limits.max_input_bytes:
            archive.close();raise ValueError('Expected one bounded source text member per archive')
        stream=archive.open(members[0])
    else:raise ValueError('Only explicit gzip/zip expansion supported')
    size=0
    try:
        with stream,temporary.open('xb') as target:
            temporary.chmod(0o600)
            while chunk:=stream.read(min(1024*1024,limits.max_input_bytes-size+1)):
                size+=len(chunk)
                if size>limits.max_input_bytes:raise ValueError('Expanded source exceeds input ceiling')
                limits.check_disk(destination.parent,len(chunk));target.write(chunk)
        temporary.replace(destination)
    finally:
        if archive:archive.close()
        temporary.unlink(missing_ok=True)
    return {'bytes':size,'sha256':digest(destination)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preflight','recent','acquire','unpack'],nargs='?',default='preflight')
    parser.add_argument('--plan',type=Path);parser.add_argument('--source',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--max-download-bytes',type=int,default=64_000_000)
    parser.add_argument('--max-input-bytes',type=int,default=500_000_000)
    parser.add_argument('--disk-reserve-bytes',type=int,default=20_000_000_000)
    args=parser.parse_args();limits=Limits(max_download_bytes=args.max_download_bytes,max_input_bytes=args.max_input_bytes,disk_reserve_bytes=args.disk_reserve_bytes)
    if args.command=='preflight':
        result=preflight();save(ROOT/'experiments/phase-eight-resources.json',result)
    elif args.command=='recent':
        result=recent_probe();save(ROOT/'experiments/phase-eight-recent.json',result)
    elif args.command=='acquire':
        if not args.plan or not args.output:parser.error('Private --plan and --output required')
        result=acquire(args.plan,args.output,limits)
    else:
        if not args.source or not args.output:parser.error('Private --source and --output required')
        result=unpack(args.source,args.output,limits)
    print(json.dumps(result,indent=2))
