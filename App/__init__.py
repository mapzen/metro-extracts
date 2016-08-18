from itertools import groupby
from operator import itemgetter
from os.path import join, dirname
from threading import Thread
import json, os

import requests
import uritemplate
import psycopg2

from flask import (
    Blueprint, jsonify, Response, render_template, url_for, request, session
    )

from . import util, data
from .oauth import session_info

blueprint = Blueprint('Metro-Extracts', __name__)

def apply_blueprint(app, url_prefix):
    '''
    '''
    app.register_blueprint(blueprint, url_prefix=url_prefix)

def populate_metro_urls(metro_id):
    '''
    '''
    downloads = []
    template = 'https://s3.amazonaws.com/metro-extracts.mapzen.com/{id}.{ext}'
    
    def _download(format, ext):
        url = uritemplate.expand(template, dict(id=metro_id, ext=ext))
        downloads.append(util.Download(format, url))
    
    threads = [
        Thread(target=_download, args=('OSM2PGSQL SHP', 'osm2pgsql-shapefiles.zip')),
        Thread(target=_download, args=('OSM2PGSQL GEOJSON', 'osm2pgsql-geojson.zip')),
        Thread(target=_download, args=('IMPOSM SHP', 'imposm-shapefiles.zip')),
        Thread(target=_download, args=('IMPOSM GEOJSON', 'imposm-geojson.zip')),
        Thread(target=_download, args=('OSM PBF', 'osm.pbf')),
        Thread(target=_download, args=('OSM XML', 'osm.bz2')),
        Thread(target=_download, args=('WATER COASTLINE SHP', 'water.coastline.zip')),
        Thread(target=_download, args=('LAND COASTLINE SHP', 'land.coastline.zip')),
        ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    return downloads

@blueprint.route('/')
@util.errors_logged
def index():
    id, nick, avatar, _, _ = session_info(session)
    
    # Include only cities that have been published.
    cities = [city for city in data.cities
              if city.get('status') != 'pre-published']

    ordered_cities = sorted(cities, key=itemgetter('country'))
    metros_tree = list()
    
    for (country, sub_cities) in groupby(ordered_cities, itemgetter('country')):
        sub_metros = list()
        
        for sub_city in sorted(sub_cities, key=itemgetter('name')):
            sub_city['href'] = url_for('Metro-Extracts.get_metro', metro_id=sub_city['id'])
            sub_metros.append(sub_city)
        
        metros_tree.append({'country': country, 'metros': sub_metros})
    
    return render_template('index.html', metros_tree=metros_tree, util=util,
                           user_id=id, user_nickname=nick, avatar=avatar)

@blueprint.route('/cities.geojson')
@util.errors_logged
def get_cities_geojson():
    features = list()
    
    for city in data.cities:
        if city.get('status') == 'pre-published':
            # Skip any city that is not yet fully published.
            continue
    
        x1, y1, x2, y2 = [float(city['bbox'][k])
                          for k in ('left', 'bottom', 'right', 'top')]

        feature = dict(type='Feature', id=city['id'])
        #feature['bbox'] = [x1, y1, x2, y2]
        feature['geometry'] = dict(type='Polygon')
        feature['geometry']['coordinates'] = [[[x1, y1], [x1, y2], [x2, y2], [x2, y1], [x1, y1]]]
        feature['properties'] = dict(name=city['id'], display_name=city['name'])
        feature['properties']['href'] = url_for('Metro-Extracts.get_metro', metro_id=city['id'])
        features.append(feature)

    return jsonify(dict(type='FeatureCollection', features=features))

@blueprint.route('/cities-extractor.json')
@util.errors_logged
def get_cities_extractor_json():
    # Include only cities that have not been deprecated.
    cities = [city for city in data.cities
              if city.get('status') != 'deprecated']

    return Response(json.dumps(cities, indent=2),
                    headers={'Content-Type': 'application/json'})

@blueprint.route('/metro/<metro_id>/')
@blueprint.route('/metro/<metro_id>/<wof_id>/<wof_name>/')
@util.errors_logged
def get_metro(metro_id, wof_id=None, wof_name=None):
    cities = {c['id']: c for c in data.cities if c.get('status') != 'pre-published'}
    
    if metro_id not in cities:
        return Response('', status=404)
    
    metro = cities[metro_id]
    downloads = {d.format: d for d in populate_metro_urls(metro_id)}
    
    return render_template('metro.html', metro=metro, downloads=downloads,
                           wof_id=wof_id, wof_name=wof_name, util=util)

@blueprint.route('/wof/<id>.geojson')
@util.errors_logged
def wof_geojson(id):
    ''' Proxy requests to http://whosonfirst.mapzen.com/spelunker/id/{id}.geojson
    '''
    template = 'http://whosonfirst.mapzen.com/spelunker/id/{id}.geojson'
    url = uritemplate.expand(template, dict(id=id))
    wof_resp = requests.get(url)

    headers = {key: val for (key, val) in wof_resp.headers.items()
               if key in ('Content-Type', 'Content-Length')}
    
    return Response(wof_resp.content, headers=headers)
