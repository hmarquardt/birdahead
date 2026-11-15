"""Real-media browser acceptance on a disposable learner DB; never changes owner practice/reviews."""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright, expect
from tooling.discover import PRIVATE, ROOT, save


def main():
    with tempfile.TemporaryDirectory(prefix='learner-browser-',dir=PRIVATE) as temporary:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        origin=f'http://127.0.0.1:{port}'
        environment={**os.environ,'BIRDAHEAD_PORT':str(port),'BIRDAHEAD_STATE_DIRECTORY':temporary}
        process=subprocess.Popen(['npm','start','--prefix','app'],cwd=ROOT,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        try:
            deadline=time.monotonic()+20
            while True:
                try:
                    with urllib.request.urlopen(origin+'/api/bootstrap',timeout=2) as r:assert r.status==200
                    break
                except (OSError,urllib.error.URLError):
                    if time.monotonic()>deadline:raise RuntimeError('Local learner did not become ready') from None
                    time.sleep(.2)
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='chrome',headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin);expect(page.get_by_role('heading',name='Meet the birds before you go.')).to_be_visible()
                page.locator('#outing-day').fill('2026-01-15');expect(page.locator('.deck-peek')).to_contain_text('Mallard')
                winter=page.locator('.deck-peek').inner_text()
                page.locator('#outing-day').fill('2026-07-15');expect(page.locator('.deck-peek')).to_contain_text('Indigo Bunting')
                assert page.locator('.deck-peek').inner_text()!=winter
                page.locator('#outing-day').fill('2026-04-01');page.get_by_role('button',name='02 Arriving soon',exact=False).click()
                expect(page.locator('.deck-peek')).to_contain_text('Prothonotary Warbler')
                page.get_by_role('button',name='Start a five-minute session').click()
                expect(page.get_by_role('heading',name='Who’s this?')).to_be_visible()
                image=page.locator('.photo-wrap img');expect(image).to_be_visible()
                deadline=time.monotonic()+15
                while image.evaluate('(e)=>e.naturalWidth')==0 and time.monotonic()<deadline:page.wait_for_timeout(100)
                assert image.evaluate('(e)=>e.naturalWidth')>0
                expect(page.locator('.example details')).to_contain_text('Source, attribution & license')
                page.screenshot(path=str(PRIVATE/'local-mvp/practice-desktop.png'),full_page=True)
                page.get_by_role('button',name='I’m not sure',exact=True).click();expect(page.locator('.reveal')).to_be_visible()
                page.reload();expect(page.get_by_role('heading',name='Who’s this?')).to_be_visible()
                page.get_by_role('button',name='Flag a possible identification or media issue',exact=False).click()
                page.get_by_role('textbox',name='What seems wrong?').fill('Automated browser fixture; no biological finding')
                page.get_by_role('button',name='Flag and hide this example').click();expect(page.locator('.flag-status')).to_contain_text('Locally hidden')
                page.get_by_role('button',name='Continue practice').click()
                page.get_by_role('button',name='Your progress',exact=True).click();expect(page.get_by_role('heading',name='A growing sense of recognition.')).to_be_visible()
                page.locator('#learner').select_option('birder-2');expect(page.get_by_text('A clean page in your field notebook.')).to_be_visible()
                page.get_by_role('button',name='Your next outing',exact=True).click()
                page.get_by_role('button',name='01 Here now',exact=False).click();page.locator('#outing-day').fill('2026-01-15')
                page.get_by_role('button',name='By sound',exact=False).click();page.locator('.practice-mode select').select_option('recall')
                page.get_by_role('button',name='Start a five-minute session').click()
                audio=page.locator('audio');expect(audio).to_be_visible()
                deadline=time.monotonic()+15
                while audio.evaluate('(e)=>e.readyState')<1 and time.monotonic()<deadline:page.wait_for_timeout(100)
                assert audio.evaluate('(e)=>e.readyState')>=1
                audio.evaluate('(e)=>{e.muted=true;return e.play()}');assert not audio.evaluate('(e)=>e.paused');audio.evaluate('(e)=>e.pause()')
                source=audio.get_attribute('src');r=page.request.get(origin+source,headers={'Range':'bytes=0-63'})
                assert r.status==206 and len(r.body())==64
                page.get_by_role('button',name='Reveal identification',exact=True).click();expect(page.locator('.reveal')).to_be_visible()
                page.get_by_role('button',name='I recalled it',exact=True).click();page.get_by_role('button',name='Next example',exact=False).click()
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(PRIVATE/'local-mvp/practice-mobile.png'),full_page=True)
                denied=page.request.post(origin+'/api/sessions',headers={'Origin':'https://invalid.example'},data={});assert denied.status==403
                assert not errors;browser.close()
            db=sqlite3.connect(Path(temporary)/'learning.sqlite')
            assert db.execute('SELECT count(*) FROM flags').fetchone()[0]==1
            assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==2
            db.close()
            summary={'scope':'Real approved local media; disposable learner DB; no owner review or practice fabricated',
                     'browser':'Chrome headless desktop and 390px mobile','checks':['seasonal change','independent approaching priorities','photo decode',
                     'uncertain answer','reload continuation','identification flag and suppression','independent profiles','real muted audio playback',
                     'audio byte ranges','recall reveal/self-rating','no mobile horizontal overflow','cross-origin mutation rejected'],
                     'console_errors':0,'passed':True}
            save(ROOT/'experiments/local-mvp-browser.json',summary);print(json.dumps(summary,indent=2))
        finally:
            import signal
            os.killpg(process.pid,signal.SIGTERM)
            process.wait(timeout=10)


if __name__=='__main__':main()
