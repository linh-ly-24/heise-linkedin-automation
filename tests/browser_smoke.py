import os, subprocess, tempfile, time, json, socket
from pathlib import Path
from urllib.request import urlopen
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, expect
os.chdir(Path(__file__).resolve().parent.parent)
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0))
    port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, APP_DB=tmp+'/app.sqlite', PORT=str(port))
    proc = subprocess.Popen(['python3','-m','app.server'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            try:
                with urlopen(base+'/api/health') as r: assert json.load(r)['status']=='ok'
                break
            except OSError:time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1100})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/')
            page.locator('.card').first.wait_for()
            assert page.locator('.card').count()==4
            page.locator('#topic').select_option('KI')
            assert page.locator('.card').count()==1
            page.locator('.option').nth(1).click()
            page.locator('.draft').fill('Manuell geprüfter Testentwurf.')
            page.get_by_role('button',name='Entwurf speichern').click()
            expect(page.locator("#toast")).to_have_text("Entwurf gespeichert.")
            page.reload();page.locator('.card').first.wait_for()
            page.locator('#topic').select_option('KI')
            assert page.locator('.draft').input_value()=='Manuell geprüfter Testentwurf.'
            page.get_by_role('button',name='Als ungeeignet markieren').click()
            page.locator('.empty').wait_for()
            page.locator('#unsuitable').check();page.locator('.card').wait_for()
            page.get_by_role('button',name='Wieder aufnehmen').click()
            page.locator('#topic').select_option('')
            # Real browser smoke; no screenshot artifact required.
            page.locator('#open-import').click()
            page.locator('[name=url]').fill('https://www.linkedin.com/posts/browser-smoke-test')
            page.locator('[name=author]').fill('Technischer Test – wird anschließend gelöscht')
            page.locator('[name=author_type]').select_option('person')
            page.locator('[name=published_at]').fill((datetime.now()-timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
            page.locator('[name=text]').fill('Beim Software-Testing habe ich gelernt, dass die Architektur unsere Fehleranalyse erschwert. Eine Herausforderung ist die Abstimmung zwischen Teams. Welche Erfahrungen habt ihr damit gemacht und wie prüft ihr die Entscheidungen?')
            page.get_by_role('button',name='Beitrag prüfen & hinzufügen').click()
            page.locator('.author').filter(has_text='Technischer Test').wait_for()
            assert page.locator('.card').count()==1
            assert page.locator('.option').count()==3
            assert page.get_by_role('link',name='Originalbeitrag').get_attribute('href')=='https://www.linkedin.com/posts/browser-smoke-test'
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors,errors
            browser.close()
            print('Browser smoke passed: demo, topic filter, option selection, editing, persistence, exclusion, import, original link, mobile layout; no JS errors.')
    finally:
        proc.terminate();proc.wait()
