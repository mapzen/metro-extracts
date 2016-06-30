from .oauth import check_authentication
from . import util

from operator import itemgetter
from uuid import uuid4
from time import time

from flask import (
    Blueprint, url_for, session, render_template, jsonify, redirect, request
    )

import requests
import uritemplate

blueprint = Blueprint('ODES', __name__, template_folder='templates/odes')

odes_extracts_url = 'https://odes.mapzen.com/extracts{/id}{?api_key}'

def apply_odes_blueprint(app, url_prefix):
    '''
    '''
    app.register_blueprint(blueprint, url_prefix=url_prefix)

def get_odes_keys(keys_url, access_token):
    auth_header = {'Authorization': 'Bearer {}'.format(access_token)}

    resp1 = requests.get(keys_url, headers=auth_header)
    keys = sorted(resp1.json(), key=itemgetter('created_at'), reverse=True)
    api_keys = [key['key'] for key in keys
                if key['service'] == 'odes' and key['status'] != 'disabled']
    
    if len(api_keys) == 0:
        data = dict(service='odes', nickname='Metro Extracts key')
        resp2 = requests.post(keys_url, data=data, headers=auth_header)
        
        if resp2.status_code != 200:
            raise Exception('Error making a new ODES key')
        
        api_keys = [resp2.json().get('key')]
    
    return api_keys

def load_extracts(api_keys):
    '''
    '''
    extracts = list()
    
    for api_key in api_keys:
        vars = dict(api_key=api_key)
        extracts_url = uritemplate.expand(odes_extracts_url, vars)
        resp = requests.get(extracts_url)
    
        if resp.status_code in range(200, 299):
            extracts.extend(resp.json())

    return extracts

def load_extract(id, api_keys):
    '''
    '''
    for api_key in api_keys:
        vars = dict(id=id, api_key=api_key)
        extract_url = uritemplate.expand(odes_extracts_url, vars)
        resp = requests.get(extract_url)
    
        if resp.status_code in range(200, 299):
            # Return first matching extract
            return dict(resp.json())
    
    return None

@blueprint.route('/odes/')
@util.errors_logged
def get_odes():
    '''
    '''
    return render_template('odes/index.html', util=util)

@blueprint.route('/odes/envelopes/', methods=['POST'])
@util.errors_logged
def post_envelope():
    '''
    '''
    envelope_id = str(uuid4())
    envelopes = session.get('envelopes', {})
    envelopes[envelope_id] = dict(form=request.form, created=time())
    session['envelopes'] = envelopes
    
    return redirect(url_for('ODES.get_envelope', envelope_id=envelope_id), 303)

@blueprint.route('/odes/envelopes/<envelope_id>')
@util.errors_logged
@check_authentication
def get_envelope(envelope_id):
    '''
    '''
    api_keys = get_odes_keys(session['id']['keys_url'], session['token']['access_token'])
    envelope = session['envelopes'][envelope_id]
    fields = ('bbox_n', 'bbox_w', 'bbox_s', 'bbox_e')
    data = {field: envelope['form'][field] for field in fields}

    post_url = uritemplate.expand(odes_extracts_url, dict(api_key=api_keys[0]))
    resp = requests.post(post_url, data=data)
    extract = resp.json()
    
    if 'error' in extract:
        raise Exception("Uh oh: {}".format(extract['error']))
    elif resp.status_code != 200:
        raise Exception("Uh oh")
    
    session['envelopes'].pop(envelope_id)
    return redirect(url_for('ODES.get_extract', extract_id=extract['id']), 301)

@blueprint.route('/odes/extracts/', methods=['GET'])
@util.errors_logged
@check_authentication
def get_extracts():
    '''
    '''
    api_keys = get_odes_keys(session['id']['keys_url'], session['token']['access_token'])
    extracts = load_extracts(api_keys)

    return render_template('extracts.html', extracts=extracts, util=util)

@blueprint.route('/odes/extracts/<extract_id>', methods=['GET'])
@util.errors_logged
@check_authentication
def get_extract(extract_id):
    '''
    '''
    api_keys = get_odes_keys(session['id']['keys_url'], session['token']['access_token'])
    extract = load_extract(extract_id, api_keys)
    
    if extract is None:
        raise ValueError('No extract {}'.format(extract_id))

    return render_template('extract.html', extract=extract, util=util)
