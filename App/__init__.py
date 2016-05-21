from flask import Blueprint, jsonify
import json

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
