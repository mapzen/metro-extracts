from flask import Blueprint, jsonify, Response, render_template
from itertools import groupby
from operator import itemgetter
from os.path import join, dirname
import json

import requests
import uritemplate

blueprint = Blueprint('Metro-Extracts', __name__)

def load_cities(filename):
    '''
    '''
    with open(filename) as file:
        cities = json.load(file)
    
    return cities

cities = load_cities(join(dirname(__file__), '..', 'cities.json'))

def apply_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)

@blueprint.route('/')
def index():
    ordered_cities = sorted(cities, key=itemgetter('country'))
    metros_tree = list()
    
    for (country, sub_cities) in groupby(ordered_cities, itemgetter('country')):
        metros_tree.append({
            'country': country,
            'metros': sorted(sub_cities, key=itemgetter('name'))
            })
    
    return render_template('index.html', metros_tree=metros_tree)

@blueprint.route('/cities.geojson')
def get_cities_geojson():
    features = list()
    
    for city in cities:
        x1, y1, x2, y2 = [float(city['bbox'][k])
                          for k in ('left', 'bottom', 'right', 'top')]

        feature = dict(type='Feature', id=city['name'])
        #feature['bbox'] = [x1, y1, x2, y2]
        feature['geometry'] = dict(type='Polygon')
        feature['geometry']['coordinates'] = [[[x1, y1], [x1, y2], [x2, y2], [x2, y1], [x1, y1]]]
        feature['properties'] = dict(name=city['name'])
        features.append(feature)

    return jsonify(dict(features=features))

@blueprint.route('/metro/<name>')
def metro(name):
    with open('cities.json') as file:
        cities = json.load(file)
        metro = {c['name']: c for c in cities}[name]
    
    return render_template('metro.html', metro=metro)

@blueprint.route('/wof/<id>.geojson')
def wof_geojson(id):
    ''' Proxy requests to http://whosonfirst.mapzen.com/spelunker/id/{id}.geojson
    '''
    template = 'http://whosonfirst.mapzen.com/spelunker/id/{id}.geojson'
    url = uritemplate.expand(template, dict(id=id))
    wof_resp = requests.get(url)

    headers = {key: val for (key, val) in wof_resp.headers.items()
               if key in ('Content-Type', 'Content-Length')}
    
    return Response(wof_resp.content, headers=headers)
