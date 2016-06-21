from flask import Blueprint, jsonify, Response
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
    return jsonify({rk: list(sorted(region['cities'].keys()))
                    for (rk, region) in cities['regions'].items()})

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
