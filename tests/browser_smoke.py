"""Optional real-browser check. Only localhost and mocked provider responses are used."""
import json
import os
import socket
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import server
from tests.test_providers import ai_response

with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
    'OPENAI_API_KEY': '', 'OPENAI_PROCESSING_AUTHORIZED': 'false',
    'BRAVE_SEARCH_API_KEY': '', 'SEARCH_USE_AUTHORIZED': 'false', 'SEARCH_PROVIDER': 'none',
    'MAX_AI_CALLS_PER_DAY': '10', 'MAX_SEARCH_CALLS_PER_DAY': '5', 'MAX_POSTS_PROCESSED_PER_DAY': '10',
}):
    before = server.DB
    server.DB = Path(tmp) / 'browser.sqlite'
    http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_port}'
    try:
        with sync_playwright() as pw:
            executable = os.environ.get('CHROMIUM_EXECUTABLE')
            if not executable and Path('/usr/bin/chromium').exists():
                executable = '/usr/bin/chromium'
            browser = pw.chromium.launch(**({'executable_path':executable} if executable else {}), headless=True)
            page = browser.new_page(viewport={'width':1440,'height':1100})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('dialog', lambda dialog: dialog.accept())
            page.goto(base + '/')
            expect(page.locator('#ai-status')).to_contain_text('OPENAI_API_KEY fehlt')
            assert page.locator('.card').count() == 0
            page.locator('#demo-mode').check()
            expect(page.locator('.card')).to_have_count(4)
            page.locator('#topic').select_option('KI')
            expect(page.locator('.card')).to_have_count(1)
            page.locator('.option').nth(1).click()
            page.locator('.draft').fill('Manuell geprüfter Testentwurf.')
            page.get_by_role('button', name='Entwurf speichern').click()
            expect(page.locator('#toast')).to_have_text('Entwurf gespeichert.')
            page.reload()
            page.locator('#demo-mode').check()
            page.locator('#topic').select_option('KI')
            expect(page.locator('.draft')).to_have_value('Manuell geprüfter Testentwurf.')
            page.get_by_role('button', name='Als ungeeignet markieren').click()
            page.locator('.empty').wait_for()
            page.locator('#unsuitable').check()
            page.get_by_role('button', name='Wieder aufnehmen').click()
            expect(page.locator('.card')).to_have_count(1)
            page.locator('#topic').select_option('')
            page.locator('#open-import').click()
            page.locator('[name=url]').fill('https://www.linkedin.com/posts/browser-smoke-test')
            page.locator('[name=author]').fill('Technischer Test – temporäre Datenbank')
            page.locator('[name=author_type]').select_option('person')
            page.locator('[name=published_at]').fill((datetime.now()-timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
            text='Beim Software-Testing habe ich gelernt, dass die Architektur unsere Fehleranalyse erschwert. Eine Herausforderung ist die Abstimmung zwischen Teams. Welche Erfahrungen habt ihr damit gemacht und wie prüft ihr die Entscheidungen?'
            page.locator('[name=text]').fill(text)
            page.locator('[name=import_authorized]').check()
            page.locator('#import-submit').click()
            expect(page.locator('.card')).to_have_count(1)
            expect(page.locator('.badge')).to_have_text('IMPORT · UNVERIFIZIERT')
            assert page.locator('.option').count() == 0
            page.get_by_role('button', name='Original prüfen & verifizieren').click()
            page.locator('[name=publication_evidence]').fill('Originalzeit mit Zeitzone geprüft – technischer Test')
            for name in ('original_checked','author_checked','time_checked','import_authorized'):
                page.locator(f'[name={name}]').check()
            page.locator('#import-submit').click()
            expect(page.locator('.badge')).to_have_text('MENSCHLICH VERIFIZIERT')
            page.get_by_role('button', name='KI-Kommentare erzeugen', exact=True).click()
            expect(page.locator('#toast')).to_contain_text('OPENAI_API_KEY')
            assert page.locator('.option').count() == 0
            assert server.store().usage()['ai_calls'] == 0
            os.environ.update(OPENAI_API_KEY='test-only', OPENAI_PROCESSING_AUTHORIZED='true',
                              SEARCH_PROVIDER='brave', BRAVE_SEARCH_API_KEY='test-only', SEARCH_USE_AUTHORIZED='true')
            raw={'web':{'results':[{'url':'https://www.linkedin.com/posts/search-candidate','title':'KI-Testkandidat','description':'Suchausschnitt, kein bestätigter Originaltext','age':'1 hour ago'}]}}
            with patch('app.generators.request_json',return_value=ai_response()) as ai, patch('app.providers.request_json',return_value=raw) as search:
                page.reload()
                expect(page.locator('#ai-status')).to_contain_text('OpenAI bereit')
                ai.assert_not_called(); search.assert_not_called()
                page.get_by_role('button',name='KI-Kommentare erzeugen',exact=True).click()
                expect(page.locator('.option')).to_have_count(3)
                assert ai.call_count == 1
                copy=page.get_by_role('button',name='Kopieren',exact=True)
                expect(copy).to_be_disabled()
                page.get_by_role('button',name='Als geprüft markieren').click()
                expect(copy).to_be_enabled()
                page.locator('.draft').fill('Nachträglich bearbeiteter Entwurf.')
                expect(copy).to_be_disabled()
                page.get_by_role('button',name='Entwurf speichern').click()
                expect(page.locator('#toast')).to_have_text('Entwurf gespeichert.')
                page.reload()
                expect(page.locator('.draft')).to_have_value('Nachträglich bearbeiteter Entwurf.')
                assert ai.call_count == 1
                page.get_by_role('button',name='Indexierte Links suchen').click()
                expect(page.locator('.candidate-card')).to_have_count(1)
                assert search.call_count == 1
                candidate=server.store().read('candidates')
                assert next(iter(candidate.values()))['published_at'] is None
                page.locator('.candidate-card').get_by_role('button',name='Original prüfen & verifizieren').click()
                expect(page.locator('[name=published_at]')).to_have_value('')
                expect(page.locator('[name=text]')).to_have_value('')
                page.locator('#close-import').click()
                page.reload()
                expect(page.locator('.candidate-card')).to_have_count(1)
                assert search.call_count == 1
                assert ai.call_count == 1
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
            browser.close()
            print('Browser smoke passed: explicit demo, filters, persistence, import, verification, missing keys, mocked AI/search, review-gated copying, candidate evidence, mobile layout. No paid calls.')
    finally:
        http.shutdown(); http.server_close(); thread.join()
        server.DB = before
