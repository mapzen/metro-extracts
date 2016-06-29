#!/usr/bin/env python
import unittest
from uuid import uuid4

from App.web import make_app
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
        resp = self.client.get(self.prefixed('/'))
        self.assertEqual(resp.status_code, 200)

    def test_oauth_index(self):
        resp = self.client.get(self.prefixed('/oauth/hello'))
        self.assertEqual(resp.status_code, 401)
        self.assertIn(b'Authenticate With Mapzen', resp.data)

    def test_odes_index(self):
        resp = self.client.get(self.prefixed('/odes/'))
        self.assertEqual(resp.status_code, 200)

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

class TestAppDoublePrefix (TestApp):
    _url_prefix = '/{}/{}'.format(uuid4(), uuid4())

if __name__ == '__main__':
    unittest.main()
