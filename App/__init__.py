from flask import Blueprint, jsonify, Response, render_template
from itertools import groupby
from operator import itemgetter
import json

import requests
import uritemplate

blueprint = Blueprint('Metro-Extracts', __name__)

def apply_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)

@blueprint.route('/')
def index():
    with open('cities.json') as file:
        cities = json.load(file)
    
    ordered_cities = sorted(cities, key=itemgetter('whatever'))
    metros_tree = list()
    
    for (whatever, sub_cities) in groupby(ordered_cities, itemgetter('whatever')):
        metros_tree.append({
            'whatever': whatever,
            'metros': sorted(sub_cities, key=itemgetter('name'))
            })
    
    return render_template('index.html', metros_tree=metros_tree)

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
