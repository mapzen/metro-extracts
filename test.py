#!/usr/bin/env python
import unittest
from uuid import uuid4
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
from re import compile

from App.web import make_app
from bs4 import BeautifulSoup
from httmock import HTTMock, response
from flask import Flask
import requests

app = Flask(__name__)

class TestApp (unittest.TestCase):

    _url_prefix = None
    
    def prefixed(self, path):
        return ''.join((self._url_prefix or '', path))
    
    def setUp(self):
        app = make_app(self._url_prefix)
        app.config['MAPZEN_APP_ID'] = '123'
        app.config['MAPZEN_APP_SECRET'] = '456'
        app.secret_key = '789'

        self.client = app.test_client()

    def test_index(self):
        resp1 = self.client.get(self.prefixed('/'))
        soup1 = BeautifulSoup(resp1.data, 'html.parser')
        head1 = soup1.find('h1').text

        self.assertEqual(resp1.status_code, 200)
        self.assertIn('metro extracts', head1)
        
        link1 = soup1.find_all(text='San Francisco')[0].find_parent('a')
        resp2 = self.client.get(link1['href'])
        soup2 = BeautifulSoup(resp2.data, 'html.parser')
        head2 = soup2.find('h1').text

        self.assertEqual(resp2.status_code, 200)
        self.assertIn('San Francisco', head2)
        
    def test_oauth_index(self):
        resp = self.client.get(self.prefixed('/oauth/hello'))
        soup = BeautifulSoup(resp.data, 'html.parser')
        head = soup.find('h2').text

        self.assertEqual(resp.status_code, 401)
        self.assertIn('Authenticate With Mapzen', head)
    
    def test_login(self):
        '''
        '''
        starting_path, codes = self.prefixed('/oauth/hello'), ['let-me-in']
        
        def response_content1(url, request):
            '''
            '''
            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content1):
            # Request the fake front OAuth page.
            resp1 = self.client.get(starting_path)
            soup1 = BeautifulSoup(resp1.data, 'html.parser')
            form1 = soup1.find('form')
            query1 = dict([(i['name'], i['value']) for i in form1.find_all('input')])
            action_url = urlparse(form1['action'])
            redirect_url = urlparse(query1['redirect_uri'])
            
            self.assertEqual(resp1.status_code, 401)
            self.assertEqual(form1['method'], 'get')
            self.assertEqual(redirect_url.path, self.prefixed('/oauth/callback'))
            self.assertEqual(action_url.netloc, 'mapzen.com')
            self.assertEqual(action_url.path, '/oauth/authorize')
            
        def response_content2(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}

            if MHP == ('POST', 'mapzen.com', '/oauth/token'):
                form = dict(parse_qsl(request.body))
                if form['code'] == codes.pop(0):
                    data = u'''{"access_token":"working-access-token", "expires_in":7200, "token_type":"bearer"}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''{\r  "id": 631,\r  "email": "email@company.com",\r  "nickname": "user_github_handle",\r  "admin": false,\r  "keys": "https://mapzen.com/developers/oauth_api/current_developer/keys"\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content2):
            # Go back to redirect_uri, pretending that Mapzen.com has let us in.
            query2 = dict(code=codes[0], state=query1['state'])
            resp2 = self.client.get('?'.join((redirect_url.path, urlencode(query2))))
            redirect2 = urlparse(resp2.headers.get('Location'))

            self.assertEqual(resp2.status_code, 302)
            self.assertEqual(redirect2.hostname, 'localhost')
            self.assertEqual(redirect2.path, starting_path)
            
            # Verify that we are logged in.
            resp3 = self.client.get(redirect2.path)
            soup3 = BeautifulSoup(resp3.data, 'html.parser')

            self.assertEqual(resp3.status_code, 200)
            self.assertIsNotNone(soup3.find(text=compile(r'\buser_github_handle\b')))
            
            # Log out.
            resp4 = self.client.post(self.prefixed('/oauth/logout'))
            
            # Verify that we are logged out.
            resp5 = self.client.get(redirect2.path)
            soup5 = BeautifulSoup(resp5.data, 'html.parser')

            self.assertEqual(resp5.status_code, 401)

    def test_odes_index(self):
        resp = self.client.get(self.prefixed('/odes/'))
        self.assertEqual(resp.status_code, 200)

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

class TestAppDoublePrefix (TestApp):
    _url_prefix = '/{}/{}'.format(uuid4(), uuid4())

if __name__ == '__main__':
    unittest.main()
