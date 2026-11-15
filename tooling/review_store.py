"""Local-only auditable curation, independent rights/biology gates and review budget."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid
from tooling.discover import ROOT,PRIVATE,save

WORK=PRIVATE/'phase05'
DB=WORK/'reviews.sqlite'
BUDGET_SECONDS=7200
ACTIONS={'approve','reject','quarantine','defer'}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def timestamp():return datetime.now(timezone.utc).isoformat()


def evidence_fingerprint(asset):
    keys=['sha256','species_code','source_url','creator','license_url','license_version','rights_evidence','target_bbox_xyxy','target_interval','derivative_recipe']
    return hashlib.sha256(canonical({key:asset.get(key) for key in keys}).encode()).hexdigest()


class Store:
    def __init__(self,path=DB,budget=BUDGET_SECONDS):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.budget=budget
        self.connection=sqlite3.connect(self.path,timeout=10)
        self.connection.row_factory=sqlite3.Row
        self.connection.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, actor TEXT NOT NULL, role TEXT NOT NULL, started TEXT NOT NULL, start_epoch REAL NOT NULL, ended TEXT, elapsed REAL);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'audit events are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'audit events are append-only'); END;
        ''')
        self.connection.commit()

    def close(self):self.connection.close()

    def sync(self,assets):
        with self.connection:
            for asset in assets:self.connection.execute('INSERT INTO assets VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(asset['id'],canonical(asset)))

    def assets(self):
        rows=[json.loads(r['payload']) for r in self.connection.execute('SELECT payload FROM assets ORDER BY id')]
        for asset in rows:
            asset['review']=self.state(asset['id'])
        return rows

    def state(self,asset_id):
        row=self.connection.execute('SELECT payload FROM assets WHERE id=?',(asset_id,)).fetchone()
        if row is None:raise ValueError('Unknown asset')
        asset=json.loads(row['payload']);auto=asset.get('automated_decision',{})
        state={'rights':auto.get('rights','pending'),'biology':auto.get('biology','pending'),
               'status':auto.get('status','candidate'),'human_approved':False,'expert_verified':False,'events':[]}
        for row in self.connection.execute('SELECT payload FROM events ORDER BY seq'):
            event=json.loads(row['payload'])
            if event['asset_id']!=asset_id:continue
            state['events'].append(event)
            if event['action']=='approve' and event.get('evidence_fingerprint')!=evidence_fingerprint(asset):continue
            if event['gate'] in ['rights','biology']:state[event['gate']]='approved' if event['action']=='approve' else event['action']
            elif event['gate']=='asset':state['status']=event['action']
        blocking={'reject','quarantine','defer'}
        gate_states={state['rights'],state['biology']}
        if gate_states&blocking:
            state['status']=next(x for x in ['reject','quarantine','defer'] if x in gate_states)
        if state['rights']=='approved' and state['biology']=='approved' and state['status'] not in blocking:
            human_events=[e for e in state['events'] if e['gate']=='biology' and e['action']=='approve' and e.get('evidence_fingerprint')==evidence_fingerprint(asset)]
            state['human_approved']=bool(human_events)
            state['expert_verified']=bool(human_events and human_events[-1]['role']=='expert')
            state['status']='expert_verified' if state['expert_verified'] else ('human_approved' if state['human_approved'] else 'automatically_accepted')
        return state

    def used_seconds(self):
        # Include active sessions, so concurrent tabs cannot each spend the budget.
        total=self.connection.execute('SELECT COALESCE(SUM(elapsed),0) FROM sessions WHERE ended IS NOT NULL').fetchone()[0]
        for row in self.connection.execute('SELECT start_epoch FROM sessions WHERE ended IS NULL'):
            total+=max(0,time.time()-row['start_epoch'])
        return total

    def active_session(self):
        row=self.connection.execute('SELECT * FROM sessions WHERE ended IS NULL ORDER BY started LIMIT 1').fetchone()
        return dict(row) if row else None

    def start(self,asset_id,actor,role='owner'):
        if role not in {'owner','expert'} or not actor.strip():raise ValueError('Reviewer name and valid role required')
        self.state(asset_id)
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            if self.used_seconds()>=self.budget:raise ValueError('Two-hour total owner review budget exhausted; reduce coverage or replace candidates')
            # Only one active review at a time; avoids abandoned duplicate-tab timers.
            if self.connection.execute('SELECT COUNT(*) FROM sessions WHERE ended IS NULL').fetchone()[0]:raise ValueError('Finish the active review session first')
            session=str(uuid.uuid4())
            self.connection.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,NULL,NULL)',(session,asset_id,actor,role,timestamp(),time.time()))
        return session

    def finish(self,session_id,gate,action,reason,evidence='',tags=None):
        if gate not in {'rights','biology','asset'} or action not in ACTIONS:raise ValueError('Invalid review action')
        if action in {'reject','quarantine','defer'} and not reason.strip():raise ValueError('A reason is required')
        if action=='approve' and not evidence.strip():raise ValueError('Approval requires evidence, not confidence alone')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            session=self.connection.execute('SELECT * FROM sessions WHERE id=? AND ended IS NULL',(session_id,)).fetchone()
            if session is None:raise ValueError('Active review session not found')
            elapsed=max(0,time.time()-session['start_epoch']);over_budget=self.used_seconds()>self.budget
            if over_budget and action=='approve':raise ValueError('Review budget exhausted; approval blocked, defer or quarantine this asset')
            asset=json.loads(self.connection.execute('SELECT payload FROM assets WHERE id=?',(session['asset_id'],)).fetchone()[0])
            event={'asset_id':session['asset_id'],'asset_sha256':asset.get('sha256'),'evidence_fingerprint':evidence_fingerprint(asset),'actor':session['actor'],'role':session['role'],'gate':gate,'action':action,
                   'reason':reason,'evidence':evidence,'tags':tags or {},'review_seconds':round(elapsed,3),'at':timestamp(),'session_id':session_id}
            prior=self.connection.execute('SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1').fetchone();previous=prior[0] if prior else '0'*64
            encoded=canonical(event);digest=hashlib.sha256((previous+encoded).encode()).hexdigest()
            self.connection.execute('INSERT INTO events(payload,previous_hash,event_hash) VALUES(?,?,?)',(encoded,previous,digest))
            self.connection.execute('UPDATE sessions SET ended=?,elapsed=? WHERE id=?',(timestamp(),elapsed,session_id))
        return self.state(session['asset_id'])

    def verify(self):
        previous='0'*64
        for row in self.connection.execute('SELECT * FROM events ORDER BY seq'):
            if row['previous_hash']!=previous or hashlib.sha256((previous+row['payload']).encode()).hexdigest()!=row['event_hash']:return False
            previous=row['event_hash']
        return True

    def export(self,path):
        if not self.verify():raise ValueError('Review audit integrity check failed')
        approved=[]
        for asset in self.assets():
            state=asset['review']
            if state['status'] not in {'automatically_accepted','human_approved','expert_verified'}:continue
            if not asset.get('sha256') or not asset.get('license_url') or not asset.get('creator') or not asset.get('source_url'):continue
            local=(ROOT/asset['local_path']).resolve()
            if not local.is_relative_to(PRIVATE.resolve()) or not local.is_file():raise ValueError('Approved media path invalid')
            if hashlib.sha256(local.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Approved asset checksum changed')
            approved.append(asset)
        approved.sort(key=lambda r:r['id'])
        # No export timestamp in the signed payload: identical inputs yield identical bytes.
        body={'schema':'birdahead-approved-media-v1','scope':'recreational noncommercial','assets':approved,
              'audit_tail':self.connection.execute('SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()}
        body['audit_tail']=body['audit_tail'][0] if body['audit_tail'] else None
        payload=canonical(body).encode();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload+b'\n')
        return {'approved_assets':len(approved),'sha256':hashlib.sha256(payload+b'\n').hexdigest()}
