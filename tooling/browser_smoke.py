"""Optional real-browser workbench check; all review actions use a disposable fixture DB."""
from pathlib import Path
import copy
import json
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from tooling.review_store import Store,WORK
from tooling.workbench.server import Handler


def main():
    assets=json.loads((WORK/'catalog.json').read_text());examples=[]
    for kind in ['photo','audio']:
        a=copy.deepcopy(next(x for x in assets if x['kind']==kind));a['id']='fixture-'+kind
        a['automated_decision']={'rights':'approved','biology':'approved','status':'automatically_accepted','policy':'automated browser fixture, not a biological judgment'}
        examples.append(a)
    with tempfile.TemporaryDirectory(prefix='browser-fixture-',dir=WORK) as temporary:
        database=Path(temporary)/'review.sqlite';store=Store(database);store.sync(examples);store.close()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.database=database
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();origin=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(viewport={'width':1400,'height':1000});errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(origin);page.locator('#kind').select_option('photo');page.locator('#queue .item').first.click();image=page.locator('#image')
                deadline=time.monotonic()+10
                while image.evaluate('(e)=>e.naturalWidth')==0 and time.monotonic()<deadline:page.wait_for_timeout(100)
                assert image.evaluate('(e)=>e.naturalWidth')>0
                page.locator('#actor').fill('Automated UI fixture');page.locator('#start').click();expect(page.locator('#status')).to_contain_text('timer running')
                page.reload();expect(page.locator('#status')).to_contain_text('Resumed persistent review')
                page.locator('[data-action=quarantine]').click();expect(page.locator('#status')).to_contain_text('reason is required')
                page.locator('#reason').fill('Synthetic fixture decision; not a biological finding');page.locator('[data-action=quarantine]').click();expect(page.locator('#status')).to_contain_text('Decision saved')
                page.locator('#kind').select_option('audio');page.locator('#queue .item').first.click();audio=page.locator('audio');deadline=time.monotonic()+10
                while audio.evaluate('(e)=>e.readyState')<1 and time.monotonic()<deadline:page.wait_for_timeout(100)
                assert audio.evaluate('(e)=>e.readyState')>=1
                # Muted playback tests decoding/playback without generating a quiz or vocalization.
                audio.evaluate('(e)=>{e.muted=true; return e.play()}');assert not audio.evaluate('(e)=>e.paused');audio.evaluate('(e)=>e.pause()')
                ranged=page.request.get(origin+'/media/fixture-audio',headers={'Range':'bytes=0-63'});assert ranged.status==206 and len(ranged.body())==64
                denied=page.request.post(origin+'/api/start',headers={'Origin':'https://invalid.example'},data={'asset_id':'fixture-audio','actor':'should not start'});assert denied.status==403
                page.locator('#kind').select_option('photo');page.locator('#queue .item').first.click();page.screenshot(path=str(WORK/'workbench-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.screenshot(path=str(WORK/'workbench-mobile.png'),full_page=True)
                assert not errors;browser.close()
            store=Store(database);assert store.verify();assert store.state('fixture-photo')['status']=='quarantine'
            assert store.connection.execute('SELECT COUNT(*) FROM events').fetchone()[0]==1;store.close()
            print('PASS: desktop/mobile, image decode, audio playback/ranges, required reasons, persisted fixture decision/audit, cross-origin POST rejection; actual owner database untouched.')
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
