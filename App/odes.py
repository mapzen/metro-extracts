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

def get_odes_key(keys_url, access_token):
    auth_header = 'Bearer {}'.format(access_token)

    resp = requests.get(keys_url, headers={'Authorization': auth_header})
    keys = sorted(resp.json(), key=itemgetter('created_at'), reverse=True)
    api_key = [key['key'] for key in keys if key['service'] == 'odes'][0]
    
    return api_key

def load_extracts(api_key):
    '''
    '''
    extracts_url = uritemplate.expand(odes_extracts_url, dict(api_key=api_key))
    return list(requests.get(extracts_url).json())

def load_extract(api_key, id):
    '''
    '''
    extract_url = uritemplate.expand(odes_extracts_url, dict(id=id, api_key=api_key))
    return dict(requests.get(extract_url).json())

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

@blueprint.route('/odes/extracts', methods=['GET'])
@check_authentication
def get_extracts():
    '''
    '''
    api_key = get_odes_key(session['id']['keys_url'], session['token']['access_token'])
    extracts = load_extracts(api_key)

    return render_template('extracts.html', extracts=extracts)

@blueprint.route('/odes/extracts/<extract_id>', methods=['GET'])
@check_authentication
def get_extract(extract_id):
    '''
    '''
    api_key = get_odes_key(session['id']['keys_url'], session['token']['access_token'])
    extract = load_extract(api_key, extract_id)

    return render_template('extract.html', extract=extract)
