import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from app import server
from app.transport import ProviderError
from tests.test_domain import post
from tests.test_providers import OPTIONS, ai_response

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.before=server.DB
        server.DB=Path(self.tmp.name)/'data.sqlite'
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':'','OPENAI_PROCESSING_AUTHORIZED':'false','BRAVE_SEARCH_API_KEY':'','SEARCH_USE_AUTHORIZED':'false','SEARCH_PROVIDER':'none','MAX_AI_CALLS_PER_DAY':'10','MAX_SEARCH_CALLS_PER_DAY':'5','MAX_POSTS_PROCESSED_PER_DAY':'10','DATA_RETENTION_DAYS':'30'},clear=False);self.env.start()
        self.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.http.server_port}'
    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join()
        self.env.stop();server.DB=self.before;self.tmp.cleanup()
    def request(self,path,data=None):
        req=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        with urlopen(req) as r:return json.load(r)
    def error(self,path,data,code):
        with self.assertRaises(HTTPError) as err:self.request(path,data)
        self.assertEqual(err.exception.code,code)
        try:
            return json.load(err.exception)['error']
        finally:
            err.exception.close()
    def add(self,**changes):
        data=post(import_authorized=True,**changes)
        id=self.request('/api/posts',data)['id']
        return id,data
    def verify(self,id,data):
        return self.request('/api/posts/'+id+'/verify',{**data,'original_checked':True,'author_checked':True,'time_checked':True,'publication_evidence':'Am Original geprüft: angezeigte Uhrzeit mit Zeitzone.'})
    def configure_ai(self):
        os.environ.update(OPENAI_API_KEY='test-only',OPENAI_PROCESSING_AUTHORIZED='true')
    def configure_search(self):
        os.environ.update(SEARCH_PROVIDER='brave',BRAVE_SEARCH_API_KEY='test-only',SEARCH_USE_AUTHORIZED='true')
    def test_no_automatic_calls_and_demo_is_explicit(self):
        self.configure_ai();self.configure_search()
        with patch('app.generators.request_json') as ai,patch('app.providers.request_json') as search:
            self.assertEqual(self.request('/api/posts'),[])
            self.assertEqual(len(self.request('/api/posts?mode=demo')),4)
            self.request('/api/status');self.request('/api/candidates')
            ai.assert_not_called();search.assert_not_called()
        self.assertEqual(self.request('/api/status')['usage']['ai_calls'],0)
    def test_verification_required_missing_timestamp_and_company(self):
        id,data=self.add(published_at='')
        p=self.request('/api/posts')[0]
        self.assertFalse(p['assessment']['eligible']);self.assertEqual(p['comments'],[])
        self.assertIsNone(p['published_at'])
        self.error('/api/posts/'+id+'/generate',{'authorized':True},400)
        self.error('/api/posts/'+id+'/verify',{**data,'original_checked':True,'author_checked':True,'time_checked':True,'publication_evidence':'Beleg'},400)
        id,data=self.add(url='https://linkedin.com/posts/company',author_type='company')
        assessment=self.verify(id,data)['assessment']
        self.assertFalse(assessment['eligible'])
        self.error('/api/posts/'+id+'/generate',{'authorized':True},400)
    def test_old_future_and_advertising_excluded_after_verification(self):
        for n,changes in enumerate([{'published_at':(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()},
                                    {'published_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()},
                                    {'text':'Jetzt buchen: unser Kurs für Softwareentwicklung. '+post()['text']} ]):
            id,data=self.add(url=f'https://linkedin.com/posts/filter-{n}',**changes)
            self.assertFalse(self.verify(id,data)['assessment']['eligible'])
            self.error('/api/posts/'+id+'/generate',{'authorized':True},400)
    def test_duplicate_canonical_url_and_import_permission(self):
        self.error('/api/posts',post(),403)
        self.add(url='https://linkedin.com/posts/duplicate?tracking=1')
        self.error('/api/posts',post(url='https://www.linkedin.com/posts/duplicate/',import_authorized=True),409)
        self.assertEqual(len(self.request('/api/posts')),1)
    def test_missing_ai_key_and_consent_no_budget_spent(self):
        id,data=self.add();self.verify(id,data)
        self.error('/api/posts/'+id+'/generate',{},403)
        self.assertIn('OPENAI_API_KEY',self.error('/api/posts/'+id+'/generate',{'authorized':True},503))
        self.assertEqual(self.request('/api/status')['usage']['ai_calls'],0)
        self.assertEqual(self.request('/api/posts')[0]['comments'],[])
    def test_ai_cache_edits_review_and_regeneration(self):
        self.configure_ai();id,data=self.add();self.verify(id,data)
        path='/api/posts/'+id
        with patch('app.generators.request_json',return_value=ai_response()) as provider:
            generated=self.request(path+'/generate',{'authorized':True})
            self.assertEqual(len(generated['comments']),3)
            self.assertFalse(generated['cached'])
            self.request('/api/posts');self.request('/api/posts')
            self.assertTrue(self.request(path+'/generate',{'authorized':True})['cached'])
            self.assertEqual(provider.call_count,1)
            self.request(path+'/review',{'selected':'B','draft':'Persönlich bearbeiteter und geprüfter Entwurf.','reviewed':True})
            self.assertTrue(self.request('/api/posts')[0]['review']['reviewed'])
            self.request(path+'/regenerate',{'authorized':True})
            p=self.request('/api/posts')[0]
            self.assertEqual(p['review']['draft'],'Persönlich bearbeiteter und geprüfter Entwurf.')
            self.assertFalse(p['review']['reviewed'])
            self.assertEqual(provider.call_count,2)
            self.assertEqual(self.request('/api/status')['usage']['ai_calls'],2)
    def test_review_invalidated_by_changes(self):
        self.configure_ai();id,data=self.add();self.verify(id,data)
        with patch('app.generators.request_json',return_value=ai_response()):self.request('/api/posts/'+id+'/generate',{'authorized':True})
        path='/api/posts/'+id+'/review'
        self.request(path,{'draft':'Prüfung eins','selected':'A','reviewed':True})
        self.request(path,{'draft':'Änderung nach Prüfung','selected':'A'})
        self.assertFalse(self.request('/api/posts')[0]['review']['reviewed'])
    def test_ai_failure_never_falls_back_and_keeps_old_data(self):
        self.configure_ai();id,data=self.add();self.verify(id,data)
        path='/api/posts/'+id
        with patch('app.generators.request_json',side_effect=ProviderError('Anbieter gestört',503)):
            self.error(path+'/generate',{'authorized':True},503)
        self.assertEqual(self.request('/api/posts')[0]['comments'],[])
        with patch('app.generators.request_json',return_value=ai_response()):self.request(path+'/generate',{'authorized':True})
        self.request(path+'/review',{'draft':'Erhaltene Bearbeitung'})
        with patch('app.generators.request_json',return_value=ai_response({'comments':[],'note':''})):
            self.error(path+'/regenerate',{'authorized':True},502)
        p=self.request('/api/posts')[0]
        self.assertEqual(len(p['comments']),3);self.assertEqual(p['review']['draft'],'Erhaltene Bearbeitung')
    def test_limits_stop_calls(self):
        self.configure_ai();os.environ['MAX_AI_CALLS_PER_DAY']='1'
        id,data=self.add();self.verify(id,data)
        path='/api/posts/'+id
        with patch('app.generators.request_json',return_value=ai_response()) as provider:
            self.request(path+'/generate',{'authorized':True})
            self.error(path+'/regenerate',{'authorized':True},429)
            self.assertEqual(provider.call_count,1)
        os.environ['MAX_AI_CALLS_PER_DAY']='10';os.environ['MAX_POSTS_PROCESSED_PER_DAY']='1'
        id2,data2=self.add(url='https://linkedin.com/posts/second');self.verify(id2,data2)
        with patch('app.generators.request_json') as provider:
            self.error('/api/posts/'+id2+'/generate',{'authorized':True},429);provider.assert_not_called()
    def test_search_deduplication_verification_and_date_evidence(self):
        self.configure_search()
        raw={'web':{'results':[{'url':'https://linkedin.com/posts/candidate?tracking=1','title':'KI','description':'Keine verifizierte Zeit','age':'today'}]}}
        with patch('app.providers.request_json',return_value=raw):
            self.assertEqual(self.request('/api/search',{'topic':'KI','authorized':True})['added'],1)
            self.assertEqual(self.request('/api/search',{'topic':'KI','authorized':True})['added'],0)
        candidates=self.request('/api/candidates');self.assertEqual(len(candidates),1)
        c=candidates[0];self.assertIsNone(c['published_at']);self.assertEqual(self.request('/api/posts'),[])
        self.error('/api/candidates/'+c['id']+'/verify',post(url=c['url'],import_authorized=True),400)
        data=post(url=c['url'],import_authorized=True,original_checked=True,author_checked=True,time_checked=True,publication_evidence='Originalzeit, nicht Fundzeit')
        self.request('/api/candidates/'+c['id']+'/verify',data)
        p=self.request('/api/posts')[0];self.assertTrue(p['verified']);self.assertEqual(p['source'],'brave')
        self.assertEqual(p['published_at'],data['published_at']);self.assertEqual(p['comments'],[])
        self.assertEqual(self.request('/api/candidates')[0]['status'],'verified')
    def test_missing_search_setup_errors_and_limits(self):
        self.error('/api/search',{'topic':'KI','authorized':True},503)
        self.configure_search();os.environ['MAX_SEARCH_CALLS_PER_DAY']='1'
        with patch('app.providers.request_json',side_effect=ProviderError('Ratenlimit',429)) as provider:
            self.error('/api/search',{'topic':'KI','authorized':True},429)
            self.error('/api/search',{'topic':'KI','authorized':True},429)
            self.assertEqual(provider.call_count,1)
    def test_status_has_no_secret_values(self):
        self.configure_ai();self.configure_search()
        serialized=json.dumps(self.request('/api/status'))
        self.assertNotIn('test-only',serialized)
        self.assertNotIn('OPENAI_API_KEY',serialized)
    def test_legacy_preserved_and_retention_requires_confirmation(self):
        legacy=post();old=post(id='dated',url='https://linkedin.com/posts/dated',created_at=(datetime.now(timezone.utc)-timedelta(days=40)).isoformat())
        with server.store().transaction() as db:
            for p in (legacy,old):db.execute('INSERT INTO posts VALUES (?,?)',(p['id'],json.dumps(p)))
            db.execute('INSERT INTO reviews VALUES (?,?)',('test',json.dumps({'draft':'Alte Bearbeitung'})))
        rows=self.request('/api/posts');self.assertEqual(len(rows),2)
        self.assertFalse(rows[0]['verified'])
        self.assertEqual(server.store().read('reviews')['test']['draft'],'Alte Bearbeitung')
        self.assertEqual(self.request('/api/status')['retention']['legacy_without_date'],1)
        self.error('/api/retention/purge',{},400)
        self.assertEqual(len(server.store().read('posts')),2)
        self.assertEqual(self.request('/api/retention/purge',{'confirm':True})['posts_removed'],1)
        self.assertIn('test',server.store().read('posts'))
