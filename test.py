#!/usr/bin/env python
import unittest
import os, tempfile
from uuid import uuid4
from shutil import rmtree
from os.path import join, dirname, basename
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
        return self._test_remote_fragment(util.get_mapzen_navbar, 'new-navbar.html')
    
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

            if (url.netloc, url.path) == ('mapzen.com', '/site-fragments/new-navbar.html'):
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
    
    def test_metro(self):
        def response_content(url, request):
            '''
            '''
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}
            
            if (request.method, url.hostname) == ('HEAD', 's3.amazonaws.com'):
                if url.path.startswith('/metro-extracts.mapzen.com/new-york_new-york.'):
                    return response(200, '', headers={'Content-Length': '999999'})

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content):
            resp1 = self.client.get(self.prefixed('/metro/new-york_new-york/'))
            soup1 = BeautifulSoup(resp1.data, 'html.parser')
            head1 = soup1.find('h2').text

        self.assertEqual(resp1.status_code, 200)
        self.assertIn('New York', head1)
        
        formats = ('OSM2PGSQL SHP', 'OSM2PGSQL GEOJSON', 'IMPOSM SHP',
                   'IMPOSM GEOJSON', 'OSM PBF', 'OSM XML',
                   'WATER COASTLINE SHP', 'LAND COASTLINE SHP')
        
        self.assertEqual(len(soup1.find_all('a', class_='link', **{'data-format': compile(r'.*')})),
                         len(formats), 'Should have eight data format links')
        
        for format in formats:
            link = soup1.find('a', class_='link', **{'data-format': format})
            size = link.find('span', class_='size').text
            self.assertEqual(size, '977KB')
    
    def test_metro_missing(self):
        def response_content(url, request):
            '''
            '''
            response_headers = {'Content-Type': 'application/json; charset=utf-8'}
            
            if (request.method, url.hostname) == ('HEAD', 's3.amazonaws.com'):
                return response(404, '')

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content):
            resp1 = self.client.get(self.prefixed('/metro/new-york_new-york/'))
            soup1 = BeautifulSoup(resp1.data, 'html.parser')
            head1 = soup1.find('h2').text

        self.assertEqual(resp1.status_code, 200)
        self.assertIn('New York', head1)
        
        formats = ('OSM2PGSQL SHP', 'OSM2PGSQL GEOJSON', 'IMPOSM SHP',
                   'IMPOSM GEOJSON', 'OSM PBF', 'OSM XML',
                   'WATER COASTLINE SHP', 'LAND COASTLINE SHP')
        
        self.assertEqual(len(soup1.find_all('a', class_='link', **{'data-format': compile(r'.*')})),
                         len(formats), 'Should have eight data format links')
        
        for format in formats:
            link = soup1.find('a', class_='link', **{'data-format': format})
            size = link.find('span', class_='size').text
            self.assertEqual(size, 'Missing')
    
    def test_cities_responses(self):
        with mock.patch('App.data') as data:
            data.cities = [
                    {
                        "id": "abidjan_ivory-coast",
                        "name": "Abidjan",
                        "region": "africa",
                        "country": "Ivory Coast",
                        "bbox": {"top": "5.523", "left": "-4.183", "bottom": "5.220", "right": "-3.849"}
                    },
                    {
                        "id": "abuja_nigeria",
                        "status": "published",
                        "name": "Abuja",
                        "region": "africa",
                        "country": "Nigeria",
                        "bbox": {"top": "9.246", "left": "7.248", "bottom": "8.835", "right": "7.717"}
                    },
                    {
                        "id": "algiers_algeria:deprecated",
                        "status": "deprecated",
                        "name": "Algiers",
                        "region": "africa",
                        "country": "Algeria",
                        "bbox": {"top": "36.762", "left": "3.026", "bottom": "36.744", "right": "3.058"}
                    },
                    {
                        "id": "algiers_algeria:pre-published",
                        "status": "pre-published",
                        "name": "Algiers",
                        "region": "africa",
                        "country": "Algeria",
                        "bbox": {"top": "36.847", "left": "2.828", "bottom": "36.567", "right": "3.392"}
                    }
                ]
            resp1 = self.client.get(self.prefixed('/cities.geojson'))
            geojson = json.loads(resp1.data.decode('utf8'))

            resp2 = self.client.get(self.prefixed('/cities-extractor.json'))
            cities = json.loads(resp2.data.decode('utf8'))
            
            def response_content(url, request):
                '''
                '''
                MH = request.method, url.hostname
                response_headers = {'Content-Length': '0'}

                if MH == ('HEAD', 's3.amazonaws.com'):
                    return response(200, data.encode('utf8'), headers=response_headers)

                raise Exception(request.method, url, request.headers, request.body)
        
            with HTTMock(response_content):
                resp3 = self.client.get(self.prefixed('/'))
                index_html = resp3.data.decode('utf8')
            
                resp4 = self.client.get(self.prefixed('/metro/abidjan_ivory-coast/'))
                resp5 = self.client.get(self.prefixed('/metro/abuja_nigeria/'))
                resp6 = self.client.get(self.prefixed('/metro/algiers_algeria:deprecated/'))
                resp7 = self.client.get(self.prefixed('/metro/algiers_algeria:pre-published/'))
        
        self.assertEqual(geojson['type'], 'FeatureCollection')
        self.assertEqual(len(geojson['features']), 3, 'Should see three published or deprecated cities')
        
        self.assertEqual(geojson['features'][0]['type'], 'Feature')
        self.assertEqual(geojson['features'][0]['id'], 'abidjan_ivory-coast')
        self.assertEqual(geojson['features'][1]['type'], 'Feature')
        self.assertEqual(geojson['features'][1]['id'], 'abuja_nigeria')
        self.assertEqual(geojson['features'][2]['type'], 'Feature')
        self.assertEqual(geojson['features'][2]['id'], 'algiers_algeria:deprecated')
        
        self.assertEqual(len(cities), 3, 'Should see three published or pre-published cities')
        
        self.assertEqual(cities[0]['id'], 'abidjan_ivory-coast')
        self.assertEqual(cities[0]['bbox']['top'], '5.523')
        self.assertEqual(cities[0]['bbox']['left'], '-4.183')
        self.assertEqual(cities[0]['bbox']['bottom'], '5.220')
        self.assertEqual(cities[0]['bbox']['right'], '-3.849')
        self.assertEqual(cities[1]['id'], 'abuja_nigeria')
        self.assertEqual(cities[2]['id'], 'algiers_algeria:pre-published')
        
        self.assertIn('abidjan_ivory-coast', index_html)
        self.assertIn('abuja_nigeria', index_html)
        self.assertIn('algiers_algeria:deprecated', index_html)
        self.assertNotIn('algiers_algeria:pre-published', index_html)
        
        self.assertEqual(resp4.status_code, 200)
        self.assertEqual(resp5.status_code, 200)
        self.assertEqual(resp6.status_code, 200)
        self.assertEqual(resp7.status_code, 404)
        
    def test_oauth_index(self):
        resp = self.client.get(self.prefixed('/oauth/hello'))
        self.assertIn(resp.status_code, (301, 302, 303))
        
        action_url = urlparse(resp.headers.get('Location'))
        query = dict(parse_qsl(action_url.query))
        redirect_url = urlparse(query['redirect_uri'])

        self.assertEqual(redirect_url.path, self.prefixed('/oauth/callback'))
        self.assertEqual(action_url.netloc, 'mapzen.com')
        self.assertEqual(action_url.path, '/oauth/authorize')
    
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
            self.assertIn(resp1.status_code, (301, 302, 303))
            
            action_url = urlparse(resp1.headers.get('Location'))
            query1 = dict(parse_qsl(action_url.query))
            redirect_url = urlparse(query1['redirect_uri'])

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
            self.assertIsNotNone(soup3.find('button', text=compile('Logout')))
    
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
            self.assertTrue(redirect2.path.startswith(self.prefixed('/your-extracts/')))
            
            # Follow the redirect to the new extract
            resp3 = self.client.get(redirect2.path)
            soup3 = BeautifulSoup(resp3.data, 'html.parser')
            
            self.assertEqual(resp3.status_code, 200)
            self.assertIsNotNone(soup3.find(text=compile(r'\b37.8123')))
            self.assertIsNotNone(soup3.find(text=compile(r'\bwoof woof\b')))
            
            # Verify that the extract is in the big list
            resp4 = self.client.get(self.prefixed('/your-extracts/'))
            soup4 = BeautifulSoup(resp4.data, 'html.parser')
            
            self.assertEqual(resp4.status_code, 200)
            self.assertIsNotNone(soup4.find(text=compile(r'\b999\b')))
            self.assertIsNotNone(soup4.find(text=compile(r'\bwoof woof\b')))
            
            # See if an out-of-date link to the extract still works
            resp5 = self.client.get(self.prefixed(join('/odes/extracts/', basename(redirect2.path))))
            self.assertEqual(resp5.status_code, 200)
            self.assertEqual(resp5.data, resp3.data)
        
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
    
    def test_odes_your_extracts(self):
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

            if MHP == ('GET', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    data = u'''[\r{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "2016-06-02T04:20:11.000Z",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content):
            resp1 = self.client.get(self.prefixed('/odes/extracts/'))
            resp2 = self.client.get(self.prefixed('/your-extracts/'))

            self.assertEqual(resp1.status_code, resp2.status_code)
            self.assertEqual(resp1.data, resp2.data)
    
    def test_odes_request_empty_wof_id(self):
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

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content):
            # POST a new envelope request
            data1 = dict(bbox_n=37.81230, bbox_w=-122.26447, bbox_s=37.79724, bbox_e=-122.24825, display_name='woof woof', wof_id='')
            resp1 = self.client.post(self.prefixed('/odes/envelopes/'), data=data1)
            redirect1 = urlparse(resp1.headers.get('Location'))
            
            self.assertEqual(resp1.status_code, 303)
            self.assertTrue(redirect1.path.startswith(self.prefixed('/odes/envelopes/')))
    
    def test_odes_request_null_processed_time(self):
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

            if MHP == ('GET', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    data = u'''[\r{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": null,\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content1):
            resp1 = self.client.get(self.prefixed('/your-extracts/'))
            self.assertEqual(resp1.status_code, 200)
        
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

            if MHP == ('GET', 'odes.mapzen.com', '/extracts'):
                if url.query == 'api_key=odes-xxxxxxx':
                    data = u'''[\r{\r  "id": 999,\r  "status": "created",\r  "created_at": "2016-06-02T03:29:25.233Z",\r  "processed_at": "",\r  "bbox": {\r    "e": -122.24825,\r    "n": 37.81230,\r    "s": 37.79724,\r    "w": -122.26447\r  }\r}\r]'''
                    return response(200, data.encode('utf8'), headers=response_headers)

            raise Exception(request.method, url, request.headers, request.body)
        
        with HTTMock(response_content2):
            resp1 = self.client.get(self.prefixed('/your-extracts/'))
            self.assertEqual(resp1.status_code, 200)
    
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
        resp1 = self.client.get('/data/metro-extracts-alt')
        self.assertEqual(resp1.status_code, 301)
        self.assertTrue(resp1.headers.get('Location').endswith('/data/metro-extracts'))

        resp2 = self.client.get('/data/metro-extracts-alt/')
        self.assertEqual(resp2.status_code, 301)
        self.assertTrue(resp2.headers.get('Location').endswith('/data/metro-extracts/'))

        resp3 = self.client.get('/data/metro-extracts-alt/odes/extracts')
        self.assertEqual(resp3.status_code, 301)
        self.assertTrue(resp3.headers.get('Location').endswith('/data/metro-extracts/odes/extracts'))

        resp4 = self.client.get('/data/metro-extracts-alt/oauth/hello')
        self.assertEqual(resp4.status_code, 301)
        self.assertTrue(resp4.headers.get('Location').endswith('/data/metro-extracts/oauth/hello'))

        resp5 = self.client.get('/data/metro-extracts-alt/your-extracts')
        self.assertEqual(resp5.status_code, 301)
        self.assertTrue(resp5.headers.get('Location').endswith('/data/metro-extracts/your-extracts'))

class TestAppPrefix (TestApp):
    _url_prefix = '/{}'.format(uuid4())

class TestAppDoublePrefix (TestApp):
    _url_prefix = '/{}/{}'.format(uuid4(), uuid4())

class TestData (unittest.TestCase):

    def test_cities_json_content(self):
        values = (None, 'published', 'pre-published', 'deprecated')
        for city in data.cities:
            self.assertIn(city.get('status'), values, 'Bad status in city {id}'.format(**city))

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
