import json
import os
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from app.generators import OpenAICommentGenerator, validate_options
from app.providers import BraveSearchProvider
from app.transport import ProviderError, request_json, NoRedirect
from tests.test_domain import post

OPTIONS = {'comments': [
    {'key':'A','text':'Ein reproduzierbarer Testfall könnte helfen, die Auswirkungen der beschriebenen Architekturentscheidung nachvollziehbar zu machen.'},
    {'key':'B','text':'Du beschreibst die Abstimmung zwischen Teams als Herausforderung. Welche Entscheidung würdest du heute gemeinsam früher treffen?'},
    {'key':'C','text':'Als Lernaufgabe bietet sich an, unterschiedliche Lösungswege am konkreten Beispiel zu vergleichen und ihre Grenzen zu reflektieren.'},
], 'note':''}

def ai_response(data=None):
    return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(data if data is not None else OPTIONS)}}]}

class GeneratorTests(unittest.TestCase):
    def test_missing_credentials_and_authorization(self):
        for env in ({}, {'OPENAI_API_KEY':'test-only'}):
            with patch.dict(os.environ,env,clear=True), patch('app.generators.request_json') as request:
                with self.assertRaises(ProviderError):OpenAICommentGenerator().generate(post())
                request.assert_not_called()
    def test_openai_payload_and_exact_three(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_PROCESSING_AUTHORIZED':'true','OPENAI_MODEL':'gpt-4.1-mini'},clear=True), patch('app.generators.request_json',return_value=ai_response()) as request:
            result=OpenAICommentGenerator().generate(post())
            self.assertEqual([c['key'] for c in result['comments']],['A','B','C'])
            self.assertEqual(result['kind'],'ai')
            url,headers,payload,timeout=request.call_args.args
            self.assertEqual(url,'https://api.openai.com/v1/chat/completions')
            self.assertEqual(payload['response_format']['type'],'json_schema')
            self.assertEqual(json.loads(payload['messages'][1]['content']),{'original_post':post()['text']})
            self.assertNotIn(post()['url'],payload['messages'][1]['content'])
    def test_invalid_duplicates_near_duplicates_and_generic_output(self):
        bad=[{}, {'comments':OPTIONS['comments'][:2],'note':''},
             {'comments':[OPTIONS['comments'][0]]*3,'note':''},
             {'comments':[{'key':k,'text':OPTIONS['comments'][0]['text']+k} for k in 'ABC'],'note':''},
             {'comments':[{'key':k,'text':'Toller Beitrag! '+OPTIONS['comments'][i]['text']} for i,k in enumerate('ABC')],'note':''},
             {'comments':[{'key':42,'text':OPTIONS['comments'][0]['text']}]*3,'note':''}]
        for data in bad:
            with self.subTest(data=data),self.assertRaises(ProviderError):validate_options(data)
    def test_insufficient_context_and_invalid_provider_response(self):
        self.assertEqual(validate_options({'comments':[],'note':'Der Originaltext enthält zu wenig Kontext.'})['comments'],[])
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_PROCESSING_AUTHORIZED':'true'},clear=True):
            for response in ({}, {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}, {'choices':[{'finish_reason':'stop','message':{'content':'not json'}}]}):
                with patch('app.generators.request_json',return_value=response),self.assertRaises(ProviderError):OpenAICommentGenerator().generate(post())

class SearchTests(unittest.TestCase):
    def test_missing_credentials_and_permission(self):
        for env in ({},{'BRAVE_SEARCH_API_KEY':'test-only'}):
            with patch.dict(os.environ,env,clear=True),patch('app.providers.request_json') as request:
                with self.assertRaises(ProviderError):BraveSearchProvider().search('KI')
                request.assert_not_called()
    def test_url_only_candidates_duplicate_and_no_time_inference(self):
        raw={'web':{'results':[
            {'url':'https://www.linkedin.com/posts/test?tracking=1','title':'Titel','description':'Suchausschnitt','age':'2 hours ago'},
            {'url':'https://linkedin.com/posts/test/','title':'Duplikat','description':'D'},
            {'url':'https://www.linkedin.com/company/example','title':'Unternehmen','description':'D'},
            {'url':'https://evil.test/posts/foo','description':'D'},
        ]}}
        with patch.dict(os.environ,{'BRAVE_SEARCH_API_KEY':'test-only','SEARCH_USE_AUTHORIZED':'true'},clear=True),patch('app.providers.request_json',return_value=raw) as request:
            results=BraveSearchProvider().search('KI')
            self.assertEqual(len(results),1)
            self.assertIsNone(results[0]['published_at'])
            self.assertEqual(results[0]['author_type'],'unknown')
            self.assertNotIn('text',results[0])
            self.assertEqual(results[0]['status'],'candidate')
            self.assertTrue(request.call_args.args[0].startswith('https://api.search.brave.com/res/v1/web/search?'))
            self.assertNotIn('freshness',request.call_args.args[0])
    def test_invalid_search_response(self):
        with patch.dict(os.environ,{'BRAVE_SEARCH_API_KEY':'test-only','SEARCH_USE_AUTHORIZED':'true'},clear=True),patch('app.providers.request_json',return_value={'web':[]}):
            with self.assertRaises(ProviderError):BraveSearchProvider().search('Linux & Open Source')

class TransportTests(unittest.TestCase):
    def test_errors_are_safe_and_not_retried(self):
        for error,expected in [(HTTPError('https://api.test',401,'SECRET',{},None),503),
                               (HTTPError('https://api.test',429,'SECRET',{},None),429),
                               (HTTPError('https://api.test',500,'SECRET',{},None),502),
                               (TimeoutError('SECRET'),504),(URLError('SECRET'),503)]:
            opener=MagicMock();opener.open.side_effect=error
            with patch('app.transport.build_opener',return_value=opener):
                with self.assertRaises(ProviderError) as raised:request_json('https://api.test',{'Authorization':'SECRET'})
                self.assertEqual(raised.exception.status,expected)
                self.assertNotIn('SECRET',str(raised.exception))
                self.assertEqual(opener.open.call_count,1)
    def test_invalid_json_and_redirects(self):
        opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=b'bad JSON'
        with patch('app.transport.build_opener',return_value=opener),self.assertRaises(ProviderError):request_json('https://api.test',{})
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test'))
