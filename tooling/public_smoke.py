"""Verify public/private boundaries and the anonymous public learning path."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import socket
import urllib.error
import urllib.parse
import urllib.request

from tooling.discover import ROOT, save

UA = 'BirdAhead-PublicSmoke/1.0'

def request(base, path, method='GET', follow=True):
    req = urllib.request.Request(base.rstrip('/') + path, method=method, headers={'User-Agent': UA})
    try:
        opener = urllib.request.build_opener() if follow else urllib.request.build_opener(urllib.request.HTTPHandler())
        with opener.open(req, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://birdahead.com')
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--resolve-ip', default=None, help='Local DNS workaround for the apex host')
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--evidence', type=Path, default=ROOT / 'experiments/phase-three-public.json')
    args = parser.parse_args()
    base = 'http://127.0.0.1:8788' if args.local else args.base.rstrip('/')
    if args.resolve_ip:
        host = urllib.parse.urlsplit(base).hostname
        original = socket.getaddrinfo
        def resolved(name, port, *rest, **kwargs):
            return original(args.resolve_ip if name == host else name, port, *rest, **kwargs)
        socket.getaddrinfo = resolved
    checks = []
    def check(name, passed, detail=''):
        checks.append({'name': name, 'passed': bool(passed), 'detail': str(detail)[:300]})
    status, headers, body = request(base, '/')
    html = body.decode('utf-8', 'replace')
    check('public homepage', status == 200 and 'BirdAhead' in html)
    check('indexable metadata', 'index,follow' in html and 'rel="canonical"' in html and 'og:title' in html)
    check('inline SVG favicon', 'rel="icon" href="data:image/svg+xml,' in html)
    check('standard tagline', "Learn the birds you're about to meet." in html)
    check('analytics client', 'analytics.aismallbizguru.com/script.js' in html and 'as_Bq4kGnf2EkSW3dS0HZAddF' in html)
    status, _, body = request(base, '/robots.txt')
    robots = body.decode('utf-8', 'replace')
    check('robots public rules', status == 200 and 'Allow: /' in robots and 'Allow: /media/public/' in robots and 'Sitemap:' in robots)
    status, _, body = request(base, '/sitemap.xml')
    sitemap = body.decode('utf-8', 'replace')
    check('sitemap species/region entries', status == 200 and '/birds/mallar3' in sitemap and '/regions/US-IN-051' in sitemap)
    status, _, body = request(base, '/api/public/bootstrap')
    boot = json.loads(body)
    check('anonymous public bootstrap', status == 200 and boot.get('public_assets', 0) > 0 and len(boot.get('species', [])) == 100)
    status, _, body = request(base, '/api/public/curriculum?location=US-IN-051&day=2026-11-16')
    curriculum = json.loads(body)
    check('anonymous seasonal curriculum', status == 200 and len(curriculum.get('priorities', [])) == 100)
    status, _, body = request(base, '/api/public/library?location=US-IN-051&day=2026-11-16')
    library = json.loads(body)
    assets = [a for row in library.get('species', []) for a in row.get('assets', [])]
    check('anonymous eligible media library', status == 200 and len(assets) > 0 and all(a.get('media_url', '').startswith('/media/public/') for a in assets))
    check('offline download metadata', len(assets) > 0 and all(isinstance(a.get('bytes'), int) and a.get('bytes', 0) > 0 and len(str(a.get('sha256', ''))) == 64 for a in assets))
    status, _, body = request(base, '/sw.js')
    sw = body.decode('utf-8', 'replace')
    check('offline shell preserves pack cache', status == 200 and 'birdahead-pack-assets-v1' in sw and "key.startsWith('birdahead-shell-')" in sw)
    status, _, body = request(base, '/narration/manifest.json')
    narration = json.loads(body)
    check('road-trip narration manifest', status == 200 and narration.get('narration_version') == 'kokoro-82m-af_heart-v1' and len(narration.get('files', {})) >= 100)
    status, mh, mb = request(base, '/narration/names/mallar3.wav')
    check('road-trip narration audio', status == 200 and (mh.get('Content-Type') or mh.get('content-type') or '').startswith('audio/') and len(mb) > 1000)
    status, _, _ = request(base, '/narration/names/mallar3.m4a')
    check('legacy narration not delivered', status == 404, status)
    status, _, body = request(base, '/discovery.json')
    discovery = json.loads(body)
    check('public annual discovery catalog', status == 200 and discovery.get('schema') == 'birdahead-discovery-v1' and len(discovery.get('species', [])) == 333 and len(discovery.get('bins', [])) == 48)
    status, _, body = request(base, '/migration')
    migration_html = body.decode('utf-8', 'replace')
    check('crawlable migration discovery page', status == 200 and 'Annual migration explorer' in migration_html and 'reconciled species' in migration_html and 'checklists' in migration_html)
    status, _, body = request(base, '/comparisons.json')
    comparisons = json.loads(body)
    check('public comparison catalog', status == 200 and comparisons.get('schema') == 'birdahead-comparison-catalog-v1' and len(comparisons.get('pairs', [])) == 4 and all(pair.get('gaps') for pair in comparisons.get('pairs', [])))
    photo = next((a for a in assets if a.get('kind') == 'photo'), None)
    if photo:
        ms, mh, mb = request(base, photo['media_url'])
        check('anonymous public media bytes', ms == 200 and (mh.get('Content-Type') or mh.get('content-type') or '').startswith('image/') and len(mb) > 1000)
    status, _, body = request(base, '/api/public/practice?location=US-IN-051&day=2026-11-16&kind=photo&mode=choice&focus=now')
    practice = json.loads(body)
    check('anonymous guest practice', status == 200 and len(practice.get('questions', [])) >= 1 and practice.get('guest') is True)
    if not args.local:
        for path in ('/api/bootstrap', '/api/admin/releases', '/media/inat-152058977'):
            status, _, _ = request(base, path)
            check('private boundary ' + path, status == 401, status)
    status, _, body = request(base, '/birds/coohaw')
    species_html = body.decode('utf-8', 'replace')
    check('species comparison navigation', status == 200 and 'Compare with Sharp-shinned Hawk' in species_html and 'tab=compare' in species_html)
    status, _, body = request(base, '/birds/mallar3')
    species_html = body.decode('utf-8', 'replace')
    check('crawlable species page', status == 200 and '<title>Mallard · BirdAhead</title>' in species_html and 'application/ld+json' in species_html and 'rel="canonical"' in species_html)
    status, _, body = request(base, '/sources')
    sources_html = body.decode('utf-8', 'replace')
    check('sources page', status == 200 and 'rel="icon" href="data:image/svg+xml,' in sources_html and "Learn the birds you're about to meet." in sources_html)
    status, _, _ = request(base, '/privacy')
    check('privacy page', status == 200)
    if args.browser:
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            launch_args = [f'--host-resolver-rules=MAP {urllib.parse.urlsplit(base).hostname} {args.resolve_ip}'] if args.resolve_ip else []
            browser = p.chromium.launch(channel='chrome', headless=True, args=launch_args)
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.goto(base)
            expect(page.get_by_role('heading', name='Know what’s arriving.')).to_be_visible(timeout=20000)
            page.get_by_role('button', name='Field guide', exact=True).click()
            expect(page.get_by_role('heading', name='Your regional reference shelf.')).to_be_visible(timeout=15000)
            page.get_by_label('Search a bird').fill('Mallard')
            page.locator('.species-card').first.locator('.species-head').click()
            image = page.locator('.asset-gallery img').first
            expect(image).to_be_visible()
            import time
            deadline = time.monotonic() + 15
            while image.evaluate('(e)=>e.naturalWidth') == 0 and time.monotonic() < deadline: page.wait_for_timeout(100)
            check('guest browser image decode', image.evaluate('(e)=>e.naturalWidth') > 0)
            page.get_by_role('button', name='Practice', exact=True).click()
            page.get_by_role('button', name='Start photo practice').click()
            expect(page.get_by_text('LOOK CLOSELY')).to_be_visible(timeout=20000)
            page.locator('.choice-grid button').first.click()
            expect(page.get_by_text('Next example')).to_be_visible(timeout=10000)
            guest_attempts = page.evaluate("JSON.parse(localStorage.getItem('birdahead-guest-history-v1') || '[]').length")
            check('guest browser practice flow', guest_attempts > 0, guest_attempts)
            page.get_by_role('button', name='Progress', exact=True).click()
            expect(page.get_by_text('GUEST NOTEBOOK · THIS BROWSER ONLY')).to_be_visible()
            page.reload()
            page.get_by_role('button', name='Progress', exact=True).click()
            expect(page.get_by_text('GUEST NOTEBOOK · THIS BROWSER ONLY')).to_be_visible()
            persisted = page.evaluate("JSON.parse(localStorage.getItem('birdahead-guest-history-v1') || '[]').length")
            check('guest local history persists', persisted > 0, persisted)
            browser.close()
    from datetime import datetime, timezone
    report = {'schema': 'birdahead-public-smoke-v1', 'at': datetime.now(timezone.utc).isoformat(), 'base': base, 'browser': args.browser, 'checks': checks, 'passed': all(c['passed'] for c in checks)}
    save(args.evidence, report)
    for c in checks: print(c['name'], 'PASS' if c['passed'] else 'FAIL', c['detail'])
    print('PASS' if report['passed'] else 'FAIL')
    raise SystemExit(0 if report['passed'] else 1)

if __name__ == '__main__':
    main()
