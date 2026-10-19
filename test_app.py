import os
import unittest
from unittest.mock import patch, Mock
import requests
import app as module

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.client = module.app.test_client()
        module.recent.clear(); module.global_recent.clear()
        module.PUBLIC_ORIGIN = 'http://localhost'
        module.SITE_ACCESS_TOKEN = ''
        self.env = patch.dict(os.environ, {'TINYFISH_API_KEY':'test-secret-not-real'}); self.env.start()
    def tearDown(self): self.env.stop()
    def post(self, **kwargs):
        return self.client.post('/api/research', headers={'Origin':'http://localhost'}, **kwargs)
    def test_design_served(self):
        with self.client.get('/') as r:
            self.assertEqual(r.status_code, 200); self.assertIn(b'Zero blind trust', r.data)
    def test_secrets_not_served(self):
        self.assertEqual(self.client.get('/.env').status_code,404)
        self.assertEqual(self.client.get('/app.py').status_code,404)
    def test_wrong_origin(self):
        self.assertEqual(self.client.post('/api/research', json={'company':'Acme'},headers={'Origin':'https://evil.example'}).status_code,403)
    def test_email_body_rejected(self):
        self.assertEqual(self.post(json={'company':'Acme','email':'private'}).status_code,400)
    def test_query_injection_rejected(self):
        self.assertEqual(self.post(json={'company':'Acme site:evil.example'}).status_code,400)
    def test_empty_rejected(self): self.assertEqual(self.post(json={}).status_code,400)
    def test_missing_key(self):
        with patch.dict(os.environ, {'TINYFISH_API_KEY':''}):
            self.assertEqual(self.post(json={'company':'Acme'}).status_code,503)
    def test_optional_site_password(self):
        module.SITE_ACCESS_TOKEN='private-password'
        self.assertEqual(self.post(json={'company':'Acme'}).status_code,401)
    @patch('app.requests.get')
    def test_provider_contract_and_url_filter(self, get):
        get.return_value=Mock(status_code=200)
        get.return_value.json.return_value={'results':[{'title':'Careers','url':'https://example.com/careers','snippet':'A source'},{'title':'bad','url':'javascript:alert(1)'}]}
        r=self.post(json={'company':'Acme','domain':'example.com'})
        self.assertEqual(r.status_code,200); self.assertEqual(len(r.json['results']),1)
        args,kw=get.call_args
        self.assertEqual(args[0],'https://api.search.tinyfish.ai')
        self.assertEqual(kw['headers']['X-API-Key'],'test-secret-not-real')
        self.assertNotIn('email',kw['params']); self.assertNotIn('test-secret',r.get_data(as_text=True))
    @patch('app.requests.get')
    def test_timeout(self,get):
        get.side_effect=requests.Timeout()
        self.assertEqual(self.post(json={'company':'Acme'}).status_code,504)
    @patch('app.requests.get')
    def test_provider_errors(self,get):
        for status in (401,402,403,429,500,503):
            module.recent.clear(); module.global_recent.clear()
            get.return_value=Mock(status_code=status)
            r=self.post(json={'company':'Acme'})
            self.assertEqual(r.status_code,429 if status==429 else 502)
    @patch('app.requests.get')
    def test_rate_limit(self,get):
        get.return_value=Mock(status_code=200); get.return_value.json.return_value={'results':[]}
        for _ in range(5): self.assertEqual(self.post(json={'company':'Acme'}).status_code,200)
        self.assertEqual(self.post(json={'company':'Acme'}).status_code,429)
    def test_security_headers(self):
        with self.client.get('/') as r:
            self.assertEqual(r.headers['X-Frame-Options'],'DENY')
            self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy'])
    def test_size_limit(self):
        self.assertEqual(self.post(json={'company':'A'*3000}).status_code,413)

    def test_health_exposes_no_secrets(self):
        r = self.client.get('/health')
        self.assertEqual(r.json, {'status': 'ok'})

    @patch('app.requests.get')
    def test_connection_failure(self, get):
        get.side_effect = requests.ConnectionError('private provider diagnostics')
        r = self.post(json={'company': 'Acme'})
        self.assertEqual(r.status_code, 502)
        self.assertNotIn('private provider diagnostics', r.get_data(as_text=True))

    @patch('app.requests.get')
    def test_invalid_provider_json(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.side_effect = ValueError('private provider diagnostics')
        self.assertEqual(self.post(json={'company':'Acme'}).status_code, 502)

    @patch('app.requests.get')
    def test_invalid_provider_contract(self, get):
        get.return_value = Mock(status_code=200)
        for payload in ([], {}, {'results': 'unexpected'}):
            get.return_value.json.return_value = payload
            self.assertEqual(self.post(json={'company':'Acme'}).status_code, 502)

    @patch('app.requests.get')
    def test_provider_body_never_exposed(self, get):
        get.return_value = Mock(status_code=401, text='test-secret-not-real')
        r = self.post(json={'company': 'Acme'})
        self.assertIn('authentication failed', r.json['error'])
        self.assertNotIn('test-secret-not-real', r.get_data(as_text=True))

    def test_non_ascii_access_token_fails_cleanly(self):
        module.SITE_ACCESS_TOKEN = 'private-password'
        r = self.client.post('/api/research', json={'company':'Acme'},
            headers={'Origin':'http://localhost','Authorization':'Bearer café'})
        self.assertEqual(r.status_code, 401)

if __name__=='__main__': unittest.main()
