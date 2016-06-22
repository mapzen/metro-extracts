from flask import Blueprint, jsonify, Response, render_template
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
    
    return render_template('index.html', cities=cities)

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
