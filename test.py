#!/usr/bin/env python
import unittest
import os, tempfile
from uuid import uuid4
from shutil import rmtree
from os.path import join, dirname
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
from datetime import datetime
from re import compile
import json

from App import web, util, data, odes, oauth
from bs4 import BeautifulSoup
from httmock import HTTMock, response
from flask import Flask
from mock import Mock
import requests, mock

os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgres:///metro_extracts_testing')

class TestUtil (unittest.TestCase):

    def setUp(self):
        tempfile.tempdir, self._old_tempdir = tempfile.mkdtemp(prefix='util-'), tempfile.gettempdir()
    
    def tearDown(self):
        rmtree(tempfile.tempdir)
        tempfile.tempdir = self._old_tempdir
    
    def _test_remote_fragment(self, function, filename):
        content = '{} {}'.format(uuid4(), filename)
    
        def response_content1(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path

            if MHP == ('GET', 'mapzen.com', '/site-fragments/{}'.format(filename)):
                return response(200, content, headers={'Content-Type': 'text/html; charset=utf-8'})

            raise Exception(request.method, url, request.headers, request.body)
        
        def response_content2(url, request):
            '''
            '''
            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content1):
            # Request it once to get into cache.
            self.assertIn(content, function())

        with HTTMock(response_content2):
            # Request it again and expect to get it from cache.
            self.assertIn(content, function())
    
    def test_navbar(self):
        return self._test_remote_fragment(util.get_mapzen_navbar, 'navbar.html')
    
    def test_footer(self):
        return self._test_remote_fragment(util.get_mapzen_footer, 'footer.html')

class TestApp (unittest.TestCase):

    _url_prefix = None
    
    def prefixed(self, path):
        return ''.join((self._url_prefix or '', path))
    
    def setUp(self):
        tempfile.tempdir, self._old_tempdir = tempfile.mkdtemp(prefix='util-'), tempfile.gettempdir()

        # pre-request some fake headers and footers
        def response_content(url, request):
            response_headers = {'Content-Type': 'text/html; charset=utf-8'}

            if (url.netloc, url.path) == ('mapzen.com', '/site-fragments/navbar.html'):
                return response(200, '<div>fake navbar HTML</div>', headers=response_headers)

            if (url.netloc, url.path) == ('mapzen.com', '/site-fragments/footer.html'):
                return response(200, '<div>fake footer HTML</div>', headers=response_headers)

            raise Exception(url)
        
        with HTTMock(response_content):
            util.get_mapzen_navbar()
            util.get_mapzen_footer()

        app = web.make_app(self._url_prefix)
        app.config['MAPZEN_APP_ID'] = '123'
        app.config['MAPZEN_APP_SECRET'] = '456'
        app.secret_key = '789'
        
        # set up the testing database.
        with data.connect(app.config['DB_DSN']) as db:
            with open(join(dirname(__file__), 'create.pgsql')) as file:
                db.execute(file.read())

        self.client = app.test_client()
    
    def tearDown(self):
        rmtree(tempfile.tempdir)
        tempfile.tempdir = self._old_tempdir

    def test_index(self):
        resp1 = self.client.get(self.prefixed('/'))
        soup1 = BeautifulSoup(resp1.data, 'html.parser')
        head1 = soup1.find('h1').text

        self.assertEqual(resp1.status_code, 200)
        self.assertIn('metro extracts', head1)
        
        link1 = soup1.find_all(text='San Francisco')[0].find_parent('a')
        resp2 = self.client.get(link1['href'])
        soup2 = BeautifulSoup(resp2.data, 'html.parser')
        head2 = soup2.find('h2').text

        self.assertEqual(resp2.status_code, 200)
        self.assertIn('San Francisco', head2)
    
    def test_cities_geojson(self):
        resp = self.client.get(self.prefixed('/cities.geojson'))
        data = json.loads(resp.data.decode('utf8'))
        
        self.assertEqual(data['type'], 'FeatureCollection')
        for feature in data['features']:
            self.assertEqual(feature['type'], 'Feature')
        
    def test_cities_extractor_json(self):
        resp = self.client.get(self.prefixed('/cities-extractor.json'))
        data = json.loads(resp.data.decode('utf8'))
        
        for city in data:
            self.assertIn('id', city)
            self.assertIn('top', city['bbox'])
            self.assertIn('left', city['bbox'])
            self.assertIn('bottom', city['bbox'])
            self.assertIn('right', city['bbox'])
        
    def test_oauth_index(self):
        resp = self.client.get(self.prefixed('/oauth/hello'))
        soup = BeautifulSoup(resp.data, 'html.parser')
        button = soup.find('button').text

        self.assertEqual(resp.status_code, 401)
        self.assertIn('CONTINUE', button)
    
    def _do_login(self, codes):
        '''
        '''
        starting_path = self.prefixed('/oauth/hello')
        
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
    
    def _do_logout(self, codes):
        '''
        '''
        starting_path = self.prefixed('/oauth/hello')
        
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
            # Verify that we are logged in.
            resp3 = self.client.get(starting_path)
            soup3 = BeautifulSoup(resp3.data, 'html.parser')

            self.assertEqual(resp3.status_code, 200)
            self.assertIsNotNone(soup3.find(text=compile(r'\buser_github_handle\b')))

            # Log out.
            resp4 = self.client.post(self.prefixed('/oauth/logout'))
            
            # Verify that we are logged out.
            resp5 = self.client.get(starting_path)
            soup5 = BeautifulSoup(resp5.data, 'html.parser')

            self.assertTrue(resp5.headers['Location'].startswith(oauth.mapzen_authorize_url))
            self.assertEqual(resp5.status_code, 302)
    
    def test_login(self):
        '''
        '''
        codes = ['let-me-in']
        
        self._do_login(codes)
        self._do_logout(codes)

    def test_odes_request(self):
        codes = ['let-me-in']
        
        self._do_login(codes)
        
        def response_content1(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''{\r  "id": 631,\r  "email": "email@company.com",\r  "nickname": "user_github_handle",\r  "admin": false,\r  "keys": "https://mapzen.com/developers/oauth_api/current_developer/keys"\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer/keys'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''[\r  {\r    "service": "odes",\r    "key": "odes-xxxxxxx",\r    "created_at": "2015-12-15T15:24:57.236Z",\r    "nickname": "Untitled",\r    "status": "created"\r  },\r  {\r    "service": "odes",\r    "key": "odes-yyyyyyy",\r    "created_at": "2015-12-15T15:24:59.320Z",\r    "nickname": "Untitled",\r    "status": "disabled"\r  }\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('POST', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    bbox = dict(parse_qsl(request.body))
                    data = u'''{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "2016-06-02T04:20:11.000Z",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'odes.mapzen.com', '/extracts/999'):
                if url.query == 'api_key=odes-xxxxxxx':
                    bbox = dict(parse_qsl(request.body))
                    data = u'''{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "2016-06-02T04:20:11.000Z",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    data = u'''[\r{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "2016-06-02T04:20:11.000Z",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if (request.method, url.hostname) == ('GET', 'odes.mapzen.com') and url.path.startswith('/extracts/'):
                if url.query == 'api_key=odes-xxxxxxx':
                    data = u'''{"error":"extract not found"}'''
                    return response(404, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content1):
            # POST a new envelope request
            data1 = dict(bbox_n=37.81230, bbox_w=-122.26447, bbox_s=37.79724, bbox_e=-122.24825, display_name='woof woof')
            resp1 = self.client.post(self.prefixed('/odes/envelopes/'), data=data1)
            redirect1 = urlparse(resp1.headers.get('Location'))
            
            self.assertEqual(resp1.status_code, 303)
            self.assertTrue(redirect1.path.startswith(self.prefixed('/odes/envelopes/')))
            
            # Follow the redirect to the new envelope
            resp2 = self.client.get(redirect1.path)
            redirect2 = urlparse(resp2.headers.get('Location'))
            
            self.assertEqual(resp2.status_code, 301)
            self.assertTrue(redirect2.path.startswith(self.prefixed('/odes/extracts/')))
            
            # Follow the redirect to the new extract
            resp3 = self.client.get(redirect2.path)
            soup3 = BeautifulSoup(resp3.data, 'html.parser')
            
            self.assertEqual(resp3.status_code, 200)
            self.assertIsNotNone(soup3.find(text=compile(r'\b37.8123')))
            self.assertIsNotNone(soup3.find(text=compile(r'\bwoof woof\b')))
            
            # Verify that the extract is in the big list
            resp4 = self.client.get(self.prefixed('/odes/extracts/'))
            soup4 = BeautifulSoup(resp4.data, 'html.parser')
            
            self.assertEqual(resp4.status_code, 200)
            self.assertIsNotNone(soup4.find(text=compile(r'\b999\b')))
            self.assertIsNotNone(soup4.find(text=compile(r'\bwoof woof\b')))
        
        def response_content2(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''{\r  "id": 631,\r  "email": "email@company.com",\r  "nickname": "user_github_handle",\r  "admin": false,\r  "keys": "https://mapzen.com/developers/oauth_api/current_developer/keys"\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer/keys'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''[\r  {\r    "service": "odes",\r    "key": "odes-xxxxxxx",\r    "created_at": "2015-12-15T15:24:57.236Z",\r    "nickname": "Untitled",\r    "status": "created"\r  },\r  {\r    "service": "odes",\r    "key": "odes-yyyyyyy",\r    "created_at": "2015-12-15T15:24:59.320Z",\r    "nickname": "Untitled",\r    "status": "disabled"\r  }\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers)
        
        with HTTMock(response_content2):
            # Look at the envelope again, ensuring that it does not attempt to re-create an extract
            resp5 = self.client.get(redirect1.path)
            redirect5 = urlparse(resp5.headers.get('Location'))
            
            self.assertEqual(resp5.status_code, 301)
            self.assertEqual(redirect5.path, redirect2.path)
    
    def test_odes_request_errored(self):
        codes = ['let-me-in']
        
        self._do_login(codes)
        
        def response_content(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''{\r  "id": 631,\r  "email": "email@company.com",\r  "nickname": "user_github_handle",\r  "admin": false,\r  "keys": "https://mapzen.com/developers/oauth_api/current_developer/keys"\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('GET', 'mapzen.com', '/developers/oauth_api/current_developer/keys'):
                if request.headers['Authorization'] == 'Bearer working-access-token':
                    data = u'''[\r  {\r    "service": "odes",\r    "key": "odes-xxxxxxx",\r    "created_at": "2015-12-15T15:24:57.236Z",\r    "nickname": "Untitled",\r    "status": "created"\r  },\r  {\r    "service": "odes",\r    "key": "odes-yyyyyyy",\r    "created_at": "2015-12-15T15:24:59.320Z",\r    "nickname": "Untitled",\r    "status": "disabled"\r  }\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            if MHP == ('POST', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    bbox = dict(parse_qsl(request.body))
                    data = u'''{\r  "error": "can't have more than 5 extracts currently processing"\r}'''
                    return response(403, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content):
            # POST a new envelope request
            data1 = dict(bbox_n=37.81230, bbox_w=-122.26447, bbox_s=37.79724, bbox_e=-122.24825)
            resp1 = self.client.post(self.prefixed('/odes/envelopes/'), data=data1)
            redirect1 = urlparse(resp1.headers.get('Location'))
            
            self.assertEqual(resp1.status_code, 303)
            self.assertTrue(redirect1.path.startswith(self.prefixed('/odes/envelopes/')))
            
            # Follow the redirect to the new envelope
            resp2 = self.client.get(redirect1.path)
            redirect2 = urlparse(resp2.headers.get('Location'))
            
            self.assertEqual(resp2.status_code, 400)
            self.assertIn(b"can&#39;t have more than 5 extracts currently processing", resp2.data)
    
    def test_request_odes_extract(self):
    
        extract_id = str(uuid4())
        extract_name = str(uuid4())
        wof_name = str(uuid4())
        created = datetime.now()
        extract_path = '/path/to/extracts/' + extract_id

        def response_content(url, request):
            '''
            '''
            MHP = request.method, url.hostname, url.path
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}

            if MHP == ('POST', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    body = dict(parse_qsl(request.body))
                    self.assertIn('ready', body['email_subject'])
                    self.assertIn(extract_name, body['email_body_text'])
                    self.assertIn(created.strftime('%b %d, %Y'), body['email_body_text'])
                    self.assertIn(extract_path, body['email_body_text'])
                    self.assertIn(extract_name, body['email_body_html'])
                    self.assertIn(created.strftime('%b %d, %Y'), body['email_body_html'])
                    self.assertIn(extract_path, body['email_body_html'])
                    
                    data = u'''{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "2016-06-02T04:20:11.000Z",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
            
        url_for, request = Mock(), Mock()
        url_for.return_value = '/path/to/extracts/' + extract_id
        request.headers.get.return_value = 'nothing'
        
        with HTTMock(response_content):
            bbox = (-122.26447, 37.79724, -122.24825, 37.81230)
            envelope = data.Envelope(None, bbox)
            wof = data.WoF(None, wof_name)
            extract = data.Extract(extract_id, extract_name, envelope, None, None, created, wof)
            o = odes.request_odes_extract(extract, request, url_for, 'odes-xxxxxxx')
        
        self.assertEqual(o.id, str(999))
        self.assertEqual(url_for.mock_calls[0], mock.call('ODES.get_extract', extract_id=extract_id))
        self.assertEqual(url_for.mock_calls[1], mock.call('ODES.get_extracts'))
    
    def test_redirect(self):
        resp = self.client.get('/data/metro-extracts-alt')
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.headers.get('Location').endswith('/data/metro-extracts'))

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

class TestAppDoublePrefix (TestApp):
    _url_prefix = '/{}/{}'.format(uuid4(), uuid4())

class TestData (unittest.TestCase):

    def test_add_extract_envelope(self):
        db, name = Mock(), str(uuid4())
        envelope = data.Envelope('xyz', [-122.26447, 37.79724, -122.24825, 37.81230])
        wof = data.WoF(85921881, 'Oakland')
        extract_id = data.add_extract_envelope(db, name, envelope, wof)
        
        self.assertEqual(db.mock_calls[0][0], 'execute')
        self.assertEqual(db.mock_calls[0][1][1], (extract_id, name, envelope.id, envelope.bbox, wof.name, wof.id))
        self.assertEqual(db.mock_calls[0][1][0], '''
        INSERT INTO extracts
        (id, name, envelope_id, envelope_bbox, wof_name, wof_id, created)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''')
    
    def test_get_extract_by_id(self):
        db = Mock()
        db.fetchone.return_value = ('123', 'XYZ', '456', [1,2,3,4], '7', 8, 'Oakland', 85921881, None)

        extract = data.get_extract(db, extract_id='123')
        
        self.assertEqual(db.mock_calls[0][0], 'execute')
        self.assertEqual(db.mock_calls[0][1][1], ('123', ))
        self.assertEqual(db.mock_calls[0][1][0], '''
        SELECT id, name, envelope_id, envelope_bbox, odes_id, user_id, wof_name, wof_id, created
        FROM extracts WHERE id = %s
        ''')
        
        self.assertEqual(extract.id, '123')
        self.assertEqual(extract.name, 'XYZ')
        self.assertEqual(extract.odes.id, '7')
        self.assertEqual(extract.user_id, 8)
        self.assertEqual(extract.envelope.id, '456')
        self.assertEqual(extract.envelope.bbox, [1,2,3,4])
        self.assertEqual(extract.wof.id, 85921881)
        self.assertEqual(extract.wof.name, 'Oakland')

    def test_get_extract_by_envelope(self):
        db = Mock()
        db.fetchone.return_value = ('123', 'XYZ', '456', [1,2,3,4], '7', 8, 'Oakland', 85921881, None)

        extract = data.get_extract(db, envelope_id='456')
        
        self.assertEqual(db.mock_calls[0][0], 'execute')
        self.assertEqual(db.mock_calls[0][1][1], ('456', ))
        self.assertEqual(db.mock_calls[0][1][0], '''
        SELECT id, name, envelope_id, envelope_bbox, odes_id, user_id, wof_name, wof_id, created
        FROM extracts WHERE envelope_id = %s
        ''')
        
        self.assertEqual(extract.id, '123')
        self.assertEqual(extract.name, 'XYZ')
        self.assertEqual(extract.odes.id, '7')
        self.assertEqual(extract.user_id, 8)
        self.assertEqual(extract.envelope.id, '456')
        self.assertEqual(extract.envelope.bbox, [1,2,3,4])
        self.assertEqual(extract.wof.id, 85921881)
        self.assertEqual(extract.wof.name, 'Oakland')

    def test_get_extract_by_odes(self):
        db = Mock()
        db.fetchone.return_value = ('123', 'XYZ', '456', [1,2,3,4], '7', 8, 'Oakland', 85921881, None)
        
        odes = data.ODES('7')
        extract = data.get_extract(db, odes=odes)
        
        self.assertEqual(db.mock_calls[0][0], 'execute')
        self.assertEqual(db.mock_calls[0][1][1], ('7', ))
        self.assertEqual(db.mock_calls[0][1][0], '''
        SELECT id, name, envelope_id, envelope_bbox, odes_id, user_id, wof_name, wof_id, created
        FROM extracts WHERE odes_id = %s
        ''')
        
        self.assertEqual(extract.id, '123')
        self.assertEqual(extract.name, 'XYZ')
        self.assertEqual(id(extract.odes), id(odes))
        self.assertEqual(extract.user_id, 8)
        self.assertEqual(extract.envelope.id, '456')
        self.assertEqual(extract.envelope.bbox, [1,2,3,4])
        self.assertEqual(extract.wof.id, 85921881)
        self.assertEqual(extract.wof.name, 'Oakland')
        
        with self.assertRaises(AssertionError) as bad_id:
            odes2 = data.ODES(7)

    def test_set_extract(self):
        db, name = Mock(), str(uuid4())
        envelope = data.Envelope('xyz', [-122.26447, 37.79724, -122.24825, 37.81230])
        wof = data.WoF(85921881, 'Oakland')
        odes = data.ODES('4')
        extract = data.Extract('123', name, envelope, odes, 5, None, wof)
        data.set_extract(db, extract)
        
        self.assertEqual(db.mock_calls[0][0], 'execute')
        self.assertEqual(db.mock_calls[0][1][1], (name, 'xyz', [-122.26447, 37.79724, -122.24825, 37.8123], '4', 5, 'Oakland', 85921881, '123'))
        self.assertEqual(db.mock_calls[0][1][0], '''
        UPDATE extracts
        SET name = %s, envelope_id = %s, envelope_bbox = %s, odes_id = %s,
            user_id = %s, wof_name = %s, wof_id = %s
        WHERE id = %s
        ''')

if __name__ == '__main__':
    unittest.main()
