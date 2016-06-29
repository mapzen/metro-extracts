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
        self.client = app.test_client()

    def test_index(self):
        resp = self.client.get(self.prefixed('/'))
        self.assertEqual(resp.status_code, 200)

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

if __name__ == '__main__':
    unittest.main()
