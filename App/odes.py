from .oauth import check_authentication

from operator import itemgetter

from flask import Blueprint, url_for, session, render_template, jsonify

import requests
import uritemplate

blueprint = Blueprint('ODES', __name__, template_folder='templates/odes')

odes_extracts_url = 'https://odes.mapzen.com/extracts{/id}{?api_key}'

def apply_odes_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)

def get_odes_keys(keys_url, access_token):
    auth_header = 'Bearer {}'.format(access_token)

    resp = requests.get(keys_url, headers={'Authorization': auth_header})
    keys = sorted(resp.json(), key=itemgetter('created_at'), reverse=True)
    api_keys = [key['key'] for key in keys if key['service'] == 'odes']
    
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

@blueprint.route('/odes')
def get_odes():
    '''
    '''
    return '''
        <form action="{href}" method="post">
            Sudo Make Me A New Extract<br>
            <label><input   value="37.81230" name="bbox_n"> North</label><br>
            <label><input value="-122.26447" name="bbox_w"> West</label><br>
            <label><input   value="37.79724" name="bbox_s"> South</label><br>
            <label><input value="-122.24825" name="bbox_e"> East</label><br>
            <input type="submit">
        </form>
        '''.format(href=url_for('ODES.post_extracts'))

@blueprint.route('/odes/extracts', methods=['POST'])
def post_extracts():
    '''
    '''
    return str(session) # 'We will get right on that.'

@blueprint.route('/odes/extracts/', methods=['GET'])
@check_authentication
def get_extracts():
    '''
    '''
    api_keys = get_odes_keys(session['id']['keys_url'], session['token']['access_token'])
    extracts = load_extracts(api_keys)

    return render_template('extracts.html', extracts=extracts)

@blueprint.route('/odes/extracts/<extract_id>', methods=['GET'])
@check_authentication
def get_extract(extract_id):
    '''
    '''
    api_keys = get_odes_keys(session['id']['keys_url'], session['token']['access_token'])
    extract = load_extract(extract_id, api_keys)
    
    if extract is None:
        raise ValueError('No extract {}'.format(extract_id))

    return render_template('extract.html', extract=extract)
