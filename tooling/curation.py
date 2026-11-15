"""Tiered automated acceptance; preliminary source-proxy calibration is not biological certification."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
from tooling.acquire import CATALOG,WORK,inat_license_info,license_info
from tooling.discover import ROOT,save
from tooling.review_store import Store

POLICY='recreational-tiered-v1-source-proxy'
PAIR_NAMES=[("Cooper's Hawk","Sharp-shinned Hawk"),('Downy Woodpecker','Hairy Woodpecker'),('Turkey Vulture','Black Vulture'),('Greater Yellowlegs','Lesser Yellowlegs')]


def pair_codes():
    species=json.loads((ROOT/'experiments/poc-species.json').read_text());names={r['common_name']:r['ebird_species_code'] for r in species};pairs={}
    for a,b in PAIR_NAMES:pairs[names[a]]=names[b];pairs[names[b]]=names[a]
    return pairs


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def rights_gate(asset):
    reasons=[]
    if asset.get('license_code') not in {'cc0','cc-by','cc-by-sa','cc-by-nc','cc-by-nc-sa'}:reasons.append('license disallows default noncommercial derivative workflow')
    if not asset.get('license_version') or not asset.get('license_url'):reasons.append('exact license version/link missing')
    if not asset.get('attribution') or not asset.get('creator'):reasons.append('creator/attribution missing')
    if not asset.get('source_url') or not asset.get('source_record_id') or not asset.get('sha256'):reasons.append('source/provenance/checksum missing')
    parsed=license_info(asset.get('license_url'))
    if parsed['license_code']!=asset.get('license_code') or parsed['license_version']!=asset.get('license_version'):reasons.append('license code/version and deed URL do not agree')
    return not reasons,reasons


def calibrate(photos,model):
    """Contributor-separated fitting/evaluation; labels are independent source assertions only."""
    by_id={r['asset_id']:r for r in model['predictions']};train=set();test=set();parameters={}
    for code in sorted({a['species_code'] for a in photos}):
        assets=[a for a in photos if a['species_code']==code]
        contributors=sorted({a['contributor_id'] for a in assets},key=lambda v:digest([code,v]))
        n=max(1,math.ceil(.6*len(contributors)));fit=set(contributors[:min(n,len(contributors)-1)])
        for a in assets:(train if a['contributor_id'] in fit else test).add(a['id'])
    for code in sorted({a['species_code'] for a in photos}):
        positive=[by_id[a['id']]['source_cosine'] for a in photos if a['id'] in train and a['species_code']==code and by_id[a['id']]['source_rank']==1]
        # High-scoring wrong-target training examples set a stricter species cutoff.
        negative=[by_id[a['id']]['all_cosines'][code] for a in photos if a['id'] in train and a['species_code']!=code and by_id[a['id']]['top_species']==code]
        parameters[code]={'min_cosine':round(max(.20,min(positive)-.005 if positive else 1.0,max(negative)+.005 if negative else .20),6),
            'fitting_positive_count':len(positive),'fitting_wrong_target_count':len(negative),'min_margin':.025 if code in pair_codes() else .015}
    return {'method':'contributor-separated source-proxy operating thresholds; not probability calibration',
            'independently_adjudicated_labels':0,'train_ids':sorted(train),'heldout_ids':sorted(test),'parameters':parameters,
            'risk':'Source labels may be wrong; source/model errors and model errors can be correlated. Sampled audit is still required before expanding use.'}


def photo_decision(a,bioclip,bio2,calibration,claimed=None):
    claimed=claimed or a['species_code'];high=claimed in pair_codes();p=calibration['parameters'][claimed]
    reasons=[]
    source=a.get('source_evidence',{});support=len(source.get('concordant_non_owner_identifiers',[]))
    if source.get('quality_grade')!='research' or support<(2 if high else 1):reasons.append('insufficient independent source identifier support for risk tier')
    primary=bio2['top_species']==claimed and bio2['all_cosines'][claimed]>=p['min_cosine'] and bio2['top_margin']>=p['min_margin']
    if not primary:reasons.append('BioCLIP 2 agreement/threshold/margin failed')
    if high and not (bioclip['top_species']==claimed and bioclip['top_margin']>=.015):reasons.append('confusion pair requires BioCLIP corroboration and margin')
    if not high and claimed not in {r['code'] for r in bioclip['top5']}:reasons.append('BioCLIP fails top-five corroboration')
    if p['fitting_positive_count']<1:reasons.append('no fitting support for this species')
    metric=a.get('technical_metrics',{})
    if min(metric.get('width',0),metric.get('height',0))<240 or max(metric.get('width',0),metric.get('height',0))<500:reasons.append('image resolution insufficient')
    if metric.get('edge_variance_256',0)<15:reasons.append('global detail screening failed')
    if not 15<=metric.get('mean_luminance',0)<=240:reasons.append('exposure screening failed')
    if a.get('duplicate_flags'):reasons.append('duplicate or conflicting near-duplicate requires replacement')
    subject=a.get('subject_screen')
    if not subject or not subject.get('screen_passed'):reasons.append('single source-consistent target not established by automated localization screen')
    elif subject.get('localized_classification',{}).get('margin',0)<p['min_margin']:reasons.append('localized target margin below species risk threshold')
    return not reasons,reasons


def calibrate_audio(assets,predictions):
    parameters={}
    for code in sorted({a['species_code'] for a in assets if a['kind']=='audio'}):
        group=sorted([a for a in assets if a['kind']=='audio' and a['species_code']==code and a['id'] in predictions],key=lambda a:digest(a['contributor_id']))
        fitting=group[:-1] if len(group)>1 else []
        values=[predictions[a['id']]['best_source_score'] for a in fitting if predictions[a['id']]['source_dominant_windows']>0]
        base=.97 if code in pair_codes() else .90
        parameters[code]={'min_score':min(.9999,max(base,min(values)-.02 if values else .9999)),
                          'fitting_records':len(fitting),'source_proxy_positives':len(values),
                          'heldout_record':group[-1]['id'] if group else None}
    return {'method':'preliminary recordist-ordered source-proxy cutoffs; one held-out record where available',
            'independently_adjudicated_labels':0,'parameters':parameters,'scores_are_probabilities':False}


def audio_decision(a,prediction,calibration=None):
    high=a['species_code'] in pair_codes();threshold=.97 if high else .90;reasons=[]
    if calibration:
        parameter=calibration['parameters'].get(a['species_code'])
        if not parameter or not parameter['source_proxy_positives']:reasons.append('audio species calibration lacks fitting support')
        else:threshold=max(threshold,parameter['min_score'])
    source=a.get('source_evidence',{})
    if source.get('identification_status')!='identified' or a.get('quality_grade') not in {'A','B'}:reasons.append('source identification or recording quality insufficient')
    if high and source.get('animal_seen')!='yes':reasons.append('high-risk call requires source bird-seen evidence')
    if not prediction.get('source_label_present'):reasons.append('source species absent from model taxonomy')
    good=[s for s in prediction['segments'] if s.get('source_rank')==1 and (s.get('source_score') or 0)>=threshold and s['top_margin']>=.10]
    adjacent=any(abs(a['end']-b['start'])<.01 for a,b in zip(good,good[1:]))
    if not adjacent:reasons.append('no two adjacent dominant high-scoring source-species windows')
    if prediction['source_dominant_windows']/max(1,prediction['window_count'])<.60:reasons.append('target not dominant across enough of full recording; replace or make verified clip')
    metrics=prediction['technical_metrics']
    if metrics['clipped_sample_fraction']>.01 or metrics['rms_amplitude']<.0001:reasons.append('audio clipping/silence screen failed')
    if a.get('duplicate_flags'):reasons.append('duplicate recording candidate')
    if any(term in (a.get('vocalization') or '').lower() for term in ['uncertain','?']):reasons.append('source vocalization description is uncertain')
    return not reasons,reasons,threshold


def duplicates(assets,audio_predictions=None):
    for a in assets:a['duplicate_flags']=[]
    for i,a in enumerate(assets):
        for b in assets[:i]:
            if a['sha256']==b['sha256']:
                a['duplicate_flags'].append({'other':b['id'],'kind':'exact byte match'})
                if a['species_code']!=b['species_code']:b['duplicate_flags'].append({'other':a['id'],'kind':'conflicting source identity for same bytes'})
            elif a['kind']==b['kind']=='photo':
                ha=a.get('technical_metrics',{}).get('dhash');hb=b.get('technical_metrics',{}).get('dhash')
                if ha and hb and (int(ha,16)^int(hb,16)).bit_count()<=3:
                    a['duplicate_flags'].append({'other':b['id'],'kind':'near duplicate dHash<=3; screening flag, not identity proof'})
                    if a['species_code']!=b['species_code']:b['duplicate_flags'].append({'other':a['id'],'kind':'cross-label near duplicate'})
            elif a['kind']==b['kind']=='audio' and audio_predictions:
                pa=audio_predictions.get(a['id']);pb=audio_predictions.get(b['id'])
                if not pa or not pb:continue
                fa=pa['acoustic_fingerprint_64'];fb=pb['acoustic_fingerprint_64']
                similarity=sum(x*y for x,y in zip(fa,fb))
                if (a['contributor_id']==b['contributor_id'] and a.get('observed_on')==b.get('observed_on')
                    and abs(pa['duration_seconds']-pb['duration_seconds'])<=max(.1,.02*pa['duration_seconds']) and similarity>=.9999):
                    a['duplicate_flags'].append({'other':b['id'],'kind':'possible acoustic near duplicate; same contributor/date, duration and spectral fingerprint','similarity':similarity})


def run():
    assets=json.loads(CATALOG.read_text());photos=[a for a in assets if a['kind']=='photo']
    m1=json.loads((WORK/'inference/bioclip.json').read_text());m2=json.loads((WORK/'inference/bioclip-2.json').read_text())
    audio_path=WORK/'inference/birdnet.json';audio=json.loads(audio_path.read_text()) if audio_path.exists() else None
    subject_path=WORK/'inference/subjects.json';subjects=json.loads(subject_path.read_text()) if subject_path.exists() else None
    subject_results={r['asset_id']:r for r in subjects['predictions']} if subjects else {}
    p1={p['asset_id']:p for p in m1['predictions']};p2={p['asset_id']:p for p in m2['predictions']};pa={p['asset_id']:p for p in audio['predictions']} if audio else {}
    for a in photos:
        screen=subject_results.get(a['id'])
        if screen and screen['sha256']!=a['sha256']:raise ValueError('Subject screen hash does not match candidate bytes')
        a['subject_screen']=screen
        a['subject_model_provenance']={k:v for k,v in subjects.items() if k!='predictions'} if subjects else None
        a['target_bbox_xyxy']=screen.get('localized_classification',{}).get('bbox_xyxy') if screen and screen.get('localized_classification') else None
        a['presentation_modification_notice']='BirdAhead target box overlay; downloaded source image pixels unchanged.' if a['target_bbox_xyxy'] else 'Downloaded source rendition; no local pixel modifications.'
    calibration=calibrate(photos,m2);calibration['audio']=calibrate_audio(assets,pa);save(WORK/'calibration.json',calibration);calibration_sha=digest(calibration)
    duplicates(assets,pa)
    for a in assets:
        if a['kind']=='photo' and any(p[a['id']]['sha256']!=a['sha256'] for p in [p1,p2]):raise ValueError('Image inference hash does not match candidate bytes')
        if a['kind']=='audio' and a['id'] in pa and pa[a['id']]['sha256']!=a['sha256']:raise ValueError('Audio inference hash does not match candidate bytes')
        if a['kind']=='photo':a.update(inat_license_info(a['license_code']))
        rights,right_reasons=rights_gate(a)
        a['rights_approved']=rights;a['taxonomy_version']='eBird/Clements 2026'
        if rights:
            a.update(permitted_storage=True,permitted_modification=True,permitted_delivery=True,permitted_offline=True,
                     permitted_scope='recreational noncommercial; retain exact attribution and license',share_alike=a['license_code'].endswith('-sa'))
        if a['kind']=='photo':
            biology,reasons=photo_decision(a,p1[a['id']],p2[a['id']],calibration)
            a['model_results']=[{'model':m['model'],'result':{k:v for k,v in p[a['id']].items() if k!='all_cosines'}} for m,p in [(m1,p1),(m2,p2)]]
        elif a['id'] in pa:
            biology,reasons,threshold=audio_decision(a,pa[a['id']],calibration['audio']);a['technical_metrics'].update(pa[a['id']]['technical_metrics']);a['technical_metrics']['duration_seconds']=pa[a['id']]['duration_seconds']
            a['model_results']=[{'model':audio['model'],'model_sha256':audio['model_sha256'],'license':audio['model_license'],'result':pa[a['id']],'preliminary_score_cutoff':threshold}]
        else:biology=False;reasons=['BirdNET inference unavailable'];a['model_results']=[]
        a['machine_screened']=bool(a['model_results']);a['biology_approved']=biology;a['human_approved']=False;a['expert_verified']=False
        a['automated_decision']={'policy':POLICY,'calibration_sha256':calibration_sha,'calibration_status':'preliminary source-proxy; biological precision unaudited',
            'rights':'approved' if rights else 'pending','biology':'approved' if biology else 'defer',
            'status':'automatically_accepted' if rights and biology else 'defer','reasons':right_reasons+reasons,
            'acceptance_rationale':'source evidence + exact rights/provenance + specialized model agreement + risk-tier thresholds + technical/deduplication gates' if rights and biology else 'Replace with stronger candidate or use a bounded sampled review; do not lower gates to fill quota',
            'owner_review_required_per_asset':False}
        a['review_state']=a['automated_decision']['status']
    # Audit selection is stable and independent of displayed confidence order.
    accepted=[a for a in assets if a['automated_decision']['status']=='automatically_accepted']
    audited_ids=set()
    for kind,cap in [('photo',90),('audio',40)]:
        group=sorted([a for a in accepted if a['kind']==kind],key=lambda a:digest([POLICY,a['sha256']]))
        limit=min(cap,math.ceil(.20*len(group)))
        audited_ids.update(a['id'] for a in group[:limit])
    for a in assets:a['audit_selected']=a['id'] in audited_ids
    save(CATALOG,assets)
    store=Store();store.sync(assets);export=store.export(WORK/'approved-media.json');used=store.used_seconds();store.close()
    # Evaluate clean source labels and deliberate label corruptions without editing originals.
    tests=[]
    by_code={a['species_code'] for a in photos};pairs=pair_codes()
    for a in photos:
        for claimed in sorted(by_code):
            if claimed==a['species_code']:continue
            okay,_=photo_decision(a,p1[a['id']],p2[a['id']],calibration,claimed)
            tests.append({'asset_id':a['id'],'original_source':a['species_code'],'deliberately_wrong_label':claimed,'accepted':okay,'confusion_pair':pairs.get(a['species_code'])==claimed,'split':'heldout' if a['id'] in calibration['heldout_ids'] else 'fitting'})
    save(WORK/'mislabeled-controls.json',tests)
    audio_controls=[]
    species_by_code={a['species_code']:a for a in assets if a['kind']=='audio'}
    for a in [a for a in assets if a['kind']=='audio' and a['id'] in pa]:
        original=pa[a['id']]
        for code,other in species_by_code.items():
            if code==a['species_code']:continue
            target=other['common_name'];segments=[]
            for s in original['segments']:
                matching=[(i,v) for i,v in enumerate(s['top5'],1) if v['label'].split('_')[-1]==target or v['label'].split('_')[0]==other['scientific_name']]
                rank,found=matching[0] if matching else (None,{'score':0})
                segments.append({**s,'source_rank':rank,'source_score':found['score']})
            counterfactual={**original,'segments':segments,'source_dominant_windows':sum(s['source_rank']==1 for s in segments),'source_label_present':True}
            fake_asset={**a,'species_code':code}
            passed,_,_=audio_decision(fake_asset,counterfactual,calibration['audio'])
            audio_controls.append({'asset_id':a['id'],'original_source':a['species_code'],'wrong_label':code,'accepted':passed,
                'confusion_pair':pair_codes().get(a['species_code'])==code,
                'known_background_species':other['scientific_name'] in a.get('source_evidence',{}).get('background_species',[])})
    save(WORK/'audio-mislabeled-controls.json',audio_controls)
    coverage=[]
    for s in json.loads((ROOT/'experiments/poc-species.json').read_text()):
        rows=[a for a in assets if a['species_code']==s['ebird_species_code']]
        coverage.append({'species':s['common_name'],'code':s['ebird_species_code'],'photo_candidates':sum(a['kind']=='photo' for a in rows),
            'audio_candidates':sum(a['kind']=='audio' for a in rows),'automatically_accepted_photos':sum(a['kind']=='photo' and a['biology_approved'] and a['rights_approved'] for a in rows),
            'automatically_accepted_audio':sum(a['kind']=='audio' and a['biology_approved'] and a['rights_approved'] for a in rows),
            'photo_contributors':len({a['contributor_id'] for a in rows if a['kind']=='photo'}),'audio_contributors':len({a['contributor_id'] for a in rows if a['kind']=='audio'}),
            'source_vocalization_types':dict(Counter(a.get('vocalization') or 'unknown' for a in rows if a['kind']=='audio')),
            'verified_plumage_labels':0,'verified_sex_labels':0,'verified_age_labels':0,
            'source_sex_labels':dict(Counter(a.get('sex') or 'unknown' for a in rows)),
            'commercial_compatible_candidates':sum(bool(a.get('commercial_compatible')) for a in rows)})
    heldout=[t for t in tests if t['split']=='heldout'];pair_tests=[t for t in tests if t['confusion_pair']]
    summary={'at':datetime.now(timezone.utc).isoformat(),'policy':POLICY,'scope':'recreational noncommercial local validation; production remains on hold',
        'candidates':len(assets),'photo_candidates':len(photos),'audio_candidates':len(assets)-len(photos),
        'automatically_accepted':len(accepted),'human_approved':0,'expert_verified':0,'owner_review_seconds_recorded':round(used,3),
        'owner_total_review_limit_seconds':7200,'sampled_audit_queue':len(audited_ids),'rights_complete_candidates':sum(a['rights_approved'] for a in assets),
        'commercial_compatible_media':sum(bool(a.get('commercial_compatible')) for a in assets),
        'candidate_media_bytes':sum(a['bytes'] for a in assets),
        'accepted_by_modality':dict(Counter(a['kind'] for a in accepted)),
        'supported_replacement_photos':sum(a.get('acquisition_pass')=='supported replacement' for a in assets),
        'photo_upload_years':dict(Counter((a.get('uploaded') or 'unknown')[:4] for a in photos)),
        'audio_upload_years':dict(Counter((a.get('uploaded') or 'unknown')[:4] for a in assets if a['kind']=='audio')),
        'licenses':dict(Counter(a['license_code'] for a in assets)),
        'photo_source_agreement':{'bioclip':m1['source_top1_agreement'],'bioclip2':m2['source_top1_agreement'],'both':sum(p1[a['id']]['source_rank']==p2[a['id']]['source_rank']==1 for a in photos)},
        'correlated_disagreements':sum(p1[a['id']]['source_rank']!=1 and p2[a['id']]['source_rank']!=1 for a in photos),
        'same_wrong_top_label':sum(p1[a['id']]['source_rank']!=1 and p1[a['id']]['top_species']==p2[a['id']]['top_species'] for a in photos),
        'mislabeled_controls':len(tests),'mislabeled_accepted':sum(t['accepted'] for t in tests),'heldout_mislabeled_controls':len(heldout),'heldout_mislabeled_accepted':sum(t['accepted'] for t in heldout),
        'confusion_pair_controls':len(pair_tests),'confusion_pair_mislabeled_accepted':sum(t['accepted'] for t in pair_tests),
        'audio_mislabeled_controls':len(audio_controls),'audio_mislabeled_accepted':sum(t['accepted'] for t in audio_controls),
        'audio_confusion_pair_controls':sum(t['confusion_pair'] for t in audio_controls),'audio_confusion_pair_mislabeled_accepted':sum(t['accepted'] and t['confusion_pair'] for t in audio_controls),
        'calibration_limit':'Source-proxy labels, tiny per-species samples; no independently measured biological precision, no calibrated probabilities',
        'coverage':coverage,'approved_manifest':export}
    save(ROOT/'experiments/phase05-results.json',summary)
    for name,m in [('bioclip',m1),('bioclip-2',m2),('birdnet',audio)]:
        if m:save(ROOT/'experiments'/('benchmark-'+name+'.json'),{k:v for k,v in m.items() if k!='predictions'})
    if subjects:save(ROOT/'experiments/benchmark-subjects.json',{k:v for k,v in subjects.items() if k!='predictions'})
    print(json.dumps({k:v for k,v in summary.items() if k not in {'coverage','licenses'}},indent=2))


if __name__=='__main__':run()
