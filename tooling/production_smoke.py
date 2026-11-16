"""Sanitized production/local-Worker smoke test; never prints credentials or media."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from tooling.discover import ROOT, save


def read_env(path):
    values = {}
    path = Path(path)
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:]
        if '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def keys(local):
    if local:
        return read_env(ROOT / '.dev.vars')
    values = read_env(Path.home() / '.config/secrets/birdahead.env')
    return {'HANK_KEY': values.get('BIRDAHEAD_HANK_KEY', ''), 'HEATHER_KEY': values.get('BIRDAHEAD_HEATHER_KEY', '')}


def request(base, path, method='GET', body=None, headers=None, follow=True):
    headers = {'User-Agent': 'BirdAhead-ProductionSmoke/1.0', **(headers or {})}
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(base + path, data=body, method=method, headers=headers or {})
    try:
        with opener.open(req, timeout=25) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def login(base, who, key):
    status, headers, body = request(base, '/api/login', 'POST', json.dumps({'profile': who, 'key': key}).encode(),
                                    {'Content-Type': 'application/json', 'Origin': base, 'X-BirdAhead-Request': '1'})
    cookie = headers.get('Set-Cookie', '').split(';')[0]
    return status, headers, body, cookie


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://birdahead.com')
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--resolve-ip', default=None, help='Local DNS workaround for the apex host')
    parser.add_argument('--evidence', type=Path, default=ROOT / 'experiments/phase-three-production.json')
    args = parser.parse_args()
    base = 'http://127.0.0.1:8788' if args.local else args.base
    if args.resolve_ip:
        import socket, urllib.parse
        host = urllib.parse.urlsplit(base).hostname
        original = socket.getaddrinfo
        def resolved(name, port, *rest, **kwargs):
            return original(args.resolve_ip if name == host else name, port, *rest, **kwargs)
        socket.getaddrinfo = resolved
    secret = keys(args.local)
    checks = []
    def check(name, condition, detail=''):
        checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
        if not condition: raise AssertionError(name + (': ' + detail if detail else ''))
    status, headers, body = request(base, '/health')
    health = json.loads(body)
    check('health', status == 200 and health.get('ok') and health.get('auth') == 'session', str(status))
    check('unauthenticated bootstrap rejected', request(base, '/api/bootstrap')[0] == 401)
    check('unauthenticated media rejected', request(base, '/media/not-authorized')[0] == 401)
    check('unauthenticated admin rejected', request(base, '/api/admin/releases')[0] == 401)
    check('cross-origin mutation rejected', request(base, '/api/logout', 'POST', b'{}', {'Content-Type':'application/json','Origin':'https://invalid.example','X-BirdAhead-Request':'1'})[0] == 403)
    check('login CSRF header required', request(base, '/api/login', 'POST', json.dumps({'profile':'hank','key':secret['HANK_KEY']}).encode(), {'Content-Type':'application/json','Origin':base})[0] == 403)
    check('wrong key rejected', login(base, 'hank', 'not-the-right-key-value')[0] == 401)
    hstatus, hheaders, hbody, hcookie = login(base, 'hank', secret['HANK_KEY'])
    check('hank login', hstatus == 200 and hcookie.startswith(('__Host-birdahead-session=', 'birdahead-local-session=')), str(hstatus))
    check('session cookie httponly/samesite', 'HttpOnly' in hheaders.get('Set-Cookie','') and 'SameSite=Strict' in hheaders.get('Set-Cookie',''))
    if base.startswith('https://'): check('session cookie secure/host', 'Secure' in hheaders.get('Set-Cookie','') and hcookie.startswith('__Host-'))
    hh = {'Cookie': hcookie}
    status, _, body = request(base, '/api/session', headers=hh); session = json.loads(body)
    check('hank session identity', status == 200 and session.get('profile_id') == 'hank')
    status, _, body = request(base, '/api/bootstrap', headers=hh); boot = json.loads(body)
    check('bootstrap release/species', status == 200 and len(boot.get('species', [])) == 100, str(len(boot.get('species', []))))
    check('actual seasonal curriculum', status == 200 and any((r.get('current_reporting_frequency') is not None) for r in json.loads(request(base, '/api/curriculum?location=US-IN-051&day=2026-11-15', headers=hh)[2]).get('priorities', [])[:10]))
    status, _, body = request(base, '/api/library?location=US-IN-051&day=2026-11-15', headers=hh); library = json.loads(body)
    check('accepted media library', status == 200 and len(library.get('species', [])) == 100)
    asset = next((a for s in library['species'] for a in s.get('assets', []) if a.get('kind') == 'photo'), None)
    check('accepted photograph present', bool(asset))
    if asset:
        mstatus, mheaders, mbody = request(base, asset['media_url'], headers=hh)
        check('authenticated photo bytes', mstatus == 200 and len(mbody) == asset.get('bytes', len(mbody)) and mheaders.get('Content-Type','').startswith('image/'), str(mstatus))
        rstatus, rheaders, rbody = request(base, asset['media_url'], headers={**hh, 'Range':'bytes=0-63'})
        check('photo byte range', rstatus == 206 and len(rbody) == 64 and rheaders.get('Content-Range','').startswith('bytes 0-63/'), str(rstatus))
    audio = next((a for s in library['species'] for a in s.get('assets', []) if a.get('kind') == 'audio'), None)
    if audio:
        astatus, aheaders, abody = request(base, audio['media_url'], headers={**hh, 'Range':'bytes=0-63'})
        check('authenticated audio range', astatus == 206 and len(abody) == 64 and aheaders.get('Content-Range','').startswith('bytes 0-63/'), str(astatus))
    check('PWA manifest', request(base, '/manifest.webmanifest')[0] == 200 and 'icon-512.png' in request(base, '/manifest.webmanifest')[2].decode())
    check('service worker', request(base, '/sw.js')[0] == 200)
    hstatus2, _, _, hcookie2 = login(base, 'heather', secret['HEATHER_KEY'])
    check('heather login', hstatus2 == 200 and hcookie2 and hcookie2 != hcookie)
    status, _, body = request(base, '/api/session', headers={'Cookie': hcookie2}); hs = json.loads(body)
    check('heather independent identity', status == 200 and hs.get('profile_id') == 'heather')
    if base.startswith('https://'):
        nofollow = request('https://www.birdahead.com', '/', follow=False)
        check('www canonical redirect', nofollow[0] in {301,302,307,308} and nofollow[1].get('Location','').startswith('https://birdahead.com'), str(nofollow[0]))
    if args.browser:
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            launch_args = []
            if args.resolve_ip:
                import urllib.parse
                launch_args = [f'--host-resolver-rules=MAP {urllib.parse.urlsplit(base).hostname} {args.resolve_ip}']
            browser = p.chromium.launch(channel='chrome', headless=True, args=launch_args)
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.goto(base)
            expect(page.get_by_role('heading', name='Welcome to BirdAhead.')).to_be_visible()
            page.get_by_role('button', name='Hank', exact=True).click()
            page.get_by_label('Access key').fill(secret['HANK_KEY'])
            page.get_by_role('button', name='Sign in').click()
            expect(page.get_by_role('heading', name='Meet the birds before you go.')).to_be_visible(timeout=15000)
            page.get_by_role('button', name='Field guide', exact=True).click()
            expect(page.get_by_role('heading', name='Your regional reference shelf.')).to_be_visible()
            page.get_by_label('Search a bird').fill('Mallard')
            page.locator('.species-card').first.locator('.species-head').click()
            image = page.locator('.asset-gallery img').first
            expect(image).to_be_visible()
            deadline = __import__('time').monotonic() + 15
            while image.evaluate('(e)=>e.naturalWidth') == 0 and __import__('time').monotonic() < deadline: page.wait_for_timeout(100)
            check('browser image decode', image.evaluate('(e)=>e.naturalWidth') > 0)
            check('no mobile horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            page.get_by_role('button', name='Sign out').click()
            expect(page.get_by_role('heading', name='Welcome to BirdAhead.')).to_be_visible()
            browser.close()
    from datetime import datetime, timezone
    report = {'schema':'birdahead-production-smoke-v1','at':datetime.now(timezone.utc).isoformat(),'base':base,'health':health,'browser':args.browser,'checks':checks,'passed':all(c['passed'] for c in checks)}
    save(args.evidence, report)
    print(json.dumps({c['name']:c['passed'] for c in checks}, indent=2)); print('PASS')


if __name__ == '__main__':
    main()
