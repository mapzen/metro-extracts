#!/usr/bin/env python
import unittest

from App.web import make_app
from flask import Flask

app = Flask(__name__)

class TestApp (unittest.TestCase):
    
    def setUp(self):
        app = make_app()
        self.client = app.test_client()

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

if __name__ == '__main__':
    unittest.main()
