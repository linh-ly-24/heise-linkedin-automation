import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from app import server
from tests.test_domain import post

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.old_db=server.DB
        server.DB=Path(cls.temp.name)/'test.sqlite'
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        server.DB=cls.old_db;cls.temp.cleanup()
    def request(self,path,data=None):
        req=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        with urlopen(req) as r:return json.load(r)
    def test_demo_and_import_review(self):
        initial=self.request('/api/posts')
        self.assertTrue(all(p['source']=='demo' and not p['url'] for p in initial))
        self.assertTrue(all(len(p['comments'])==3 for p in initial))
        id=self.request('/api/posts',post())['id']
        path='/api/posts/'+id
        self.request(path+'/review',{'selected':'B','draft':'Ein manuell bearbeiteter Entwurf.','unsuitable':True})
        saved=next(p for p in self.request('/api/posts') if p['id']==id)
        self.assertEqual(saved['review']['draft'],'Ein manuell bearbeiteter Entwurf.')
        self.assertTrue(saved['review']['unsuitable'])
        self.request(path+'/regenerate',{})
        regenerated=next(p for p in self.request('/api/posts') if p['id']==id)
        self.assertNotIn('draft',regenerated['review'])
        self.assertEqual(regenerated['review']['variant'],1)
        self.assertTrue(regenerated['review']['unsuitable'])
    def test_invalid_import_and_origin(self):
        with self.assertRaises(HTTPError) as exc:self.request('/api/posts',post(url='https://evil.test/'))
        self.assertEqual(exc.exception.code,400)
        req=Request(self.url+'/api/posts',data=json.dumps(post()).encode(),headers={'Origin':'https://evil.test'})
        with self.assertRaises(HTTPError) as exc:urlopen(req)
        self.assertEqual(exc.exception.code,403)
    def test_dashboard_health(self):
        self.assertEqual(self.request('/api/health')['status'],'ok')
        with urlopen(self.url+'/') as r:
            self.assertIn('Dialogstudio',r.read().decode())
            self.assertIn("script-src 'self'",r.headers['Content-Security-Policy'])
