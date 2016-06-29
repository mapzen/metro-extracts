#!/usr/bin/env python
import unittest
from uuid import uuid4

from App.web import make_app
from bs4 import BeautifulSoup
from flask import Flask

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

    def test_odes_index(self):
        resp = self.client.get(self.prefixed('/odes/'))
        self.assertEqual(resp.status_code, 200)

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

class TestAppDoublePrefix (TestApp):
    _url_prefix = '/{}/{}'.format(uuid4(), uuid4())

if __name__ == '__main__':
    unittest.main()
