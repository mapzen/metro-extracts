from .oauth import check_authentication, session_info
from . import util, data

from os import environ
from urllib.parse import urljoin
from operator import itemgetter, attrgetter
from threading import Thread
from uuid import uuid4
from time import time

from dateutil.parser import parse as parse_datetime
from jinja2 import Environment, PackageLoader
from flask import (
    Blueprint, url_for, session, render_template, jsonify, redirect, request,
    current_app
    )

import requests
import uritemplate

blueprint = Blueprint('ODES', __name__, template_folder='templates/odes')

odes_extracts_url = environ.get('ODES_URL') + '{/id}{?api_key}'
keys_url = environ.get('KEYS_URL')

def apply_odes_blueprint(app, url_prefix):
    '''
    '''
    app.register_blueprint(blueprint, url_prefix=url_prefix)
    app.config['DB_DSN'] = environ.get('DATABASE_URL')

def get_odes_key(access_token):
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

    return api_keys[0]

def get_odes_extracts(db, api_key):
    '''
    '''
    odeses, extracts = list(), list()

    vars = dict(api_key=api_key)
    extracts_url = uritemplate.expand(odes_extracts_url, vars)
    resp = requests.get(extracts_url)

    if resp.status_code in range(200, 299):
        odeses.extend([data.ODES(str(oj['id']), status=oj['status'], bbox=oj['bbox'],
                                 links=oj.get('download_links', {}),
                                 processed_at=(parse_datetime(oj['processed_at']) if oj['processed_at'] else None),
                                 created_at=(parse_datetime(oj['created_at']) if oj['created_at'] else None))
                       for oj in resp.json()])

    for odes in sorted(odeses, key=attrgetter('created_at'), reverse=True):
        extract = data.get_extract(db, odes=odes)

        if extract is None:
            extract = data.Extract(None, None, None, odes, None, None, None)

        extracts.append(extract)

    return extracts

def get_odes_extract(db, id, api_key):
    '''
    '''
    extract, odes = data.get_extract(db, extract_id=id), None

    if extract is None:
        # Nothing by that name in the database, so ask the ODES API.
        vars = dict(id=id, api_key=api_key)
        extract_url = uritemplate.expand(odes_extracts_url, vars)
        resp = requests.get(extract_url)

        if resp.status_code in range(200, 299):
            oj = resp.json()
            odes = data.ODES(str(oj['id']), status=oj['status'], bbox=oj['bbox'],
                             links=oj.get('download_links', {}),
                             processed_at=(parse_datetime(oj['processed_at']) if oj['processed_at'] else None),
                             created_at=(parse_datetime(oj['created_at']) if oj['created_at'] else None))

        if odes is None:
            # Nothing at all for this ID anywhere.
            return None

    if odes is None:
        # A DB extract was found, but nothing in ODES - very weird!
        return get_odes_extract(db, extract.odes.id, api_key)

    # We have a known ODES, so look for it in the database.
    extract = data.get_extract(db, odes=odes)

    if extract is None:
        # Known ODES, but nothing in the DB so make one up.
        return data.Extract(None, None, None, odes, None, None, None)

    return extract

def request_odes_extract(extract, request, url_for, api_key):
    '''
    '''
    env = Environment(loader=PackageLoader(__name__, 'templates'))
    args = dict(
        name = extract.name or extract.wof.name or 'an unnamed place',
        link = urljoin(util.get_base_url(request), url_for('ODES.get_extract', extract_id=extract.id)),
        extracts_link = urljoin(util.get_base_url(request), url_for('ODES.get_extracts')),
        created = extract.created
        )

    email = dict(
        email_subject=env.get_template('email-subject.txt').render(**args),
        email_body_text=env.get_template('email-body.txt').render(**args),
        email_body_html=env.get_template('email-body.html').render(**args)
        )

    params = {key: extract.envelope.bbox[i] for (i, key) in enumerate(('bbox_w', 'bbox_s', 'bbox_e', 'bbox_n'))}
    params.update(email)

    params['ui_id'] = extract.id
    params['envelope_id'] = extract.envelope.id
    params['wof_name'] = extract.wof.name
    params['wof_id'] = extract.wof.id
    params['name'] = extract.name

    post_url = uritemplate.expand(odes_extracts_url, dict(api_key=api_key))
    resp = requests.post(post_url, data=params)
    oj = resp.json()

    if 'error' in oj:
        raise util.KnownUnknown("Error: {}".format(oj['error']))
    elif resp.status_code != 200:
        raise Exception("Bad ODES status code: {}".format(resp.status_code))

    return data.ODES(str(oj['id']), status=oj['status'], bbox=oj['bbox'],
                     links=oj.get('download_links', {}),
                     processed_at=(parse_datetime(oj['processed_at']) if oj['processed_at'] else None),
                     created_at=(parse_datetime(oj['created_at']) if oj['created_at'] else None))

def populate_link_downloads(odes_links):
    '''
    '''
    downloads = []

    def _download(format, url):
        downloads.append(util.Download(format, url))

    threads = [Thread(target=_download, args=(format, url))
               for (format, url) in odes_links.items()]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return downloads

@blueprint.route('/odes/envelopes/', methods=['POST'])
@util.errors_logged
def post_envelope():
    '''
    '''
    form = request.form
    name = form.get('display_name')
    bbox = [float(form[k]) for k in ('bbox_w', 'bbox_s', 'bbox_e', 'bbox_n')]
    wof_name, wof_id = form.get('wof_name'), form.get('wof_id') and int(form['wof_id'])
    envelope = data.Envelope(str(uuid4())[-12:], bbox)

    with data.connect(current_app.config['DB_DSN']) as db:
        data.add_extract_envelope(db, name, envelope, data.WoF(wof_id or None, wof_name))

    return redirect(url_for('ODES.get_envelope', envelope_id=envelope.id), 303)

@blueprint.route('/odes/envelopes/<envelope_id>')
@util.errors_logged
@check_authentication
def get_envelope(envelope_id):
    '''
    '''
    with data.connect(current_app.config['DB_DSN']) as db:
        extract = data.get_extract(db, envelope_id=envelope_id)

    if extract.odes.id is not None:
        # this envelope has already been posted to ODES.
        return redirect(url_for('ODES.get_extract', extract_id=extract.id), 301)

    user_id, _, _, _, access_token = session_info(session)
    api_key = get_odes_key(access_token)
    odes = request_odes_extract(extract, request, url_for, api_key)

    with data.connect(current_app.config['DB_DSN']) as db:
        extract.user_id = user_id
        extract.odes.id = odes.id
        data.set_extract(db, extract)

    return redirect(url_for('ODES.get_extract', extract_id=extract.id), 301)

@blueprint.route('/odes/extracts/', methods=['GET'])
@blueprint.route('/your-extracts/', methods=['GET'])
@util.errors_logged
@check_authentication
def get_extracts():
    '''
    '''
    id, nickname, avatar, _, access_token = session_info(session)
    api_key = get_odes_key(access_token)

    with data.connect(current_app.config['DB_DSN']) as db:
        extracts = get_odes_extracts(db, api_key)

    return render_template('extracts.html', extracts=extracts, util=util,
                           user_id=id, user_nickname=nickname, avatar=avatar)

@blueprint.route('/odes/extracts/<extract_id>', methods=['GET'])
@blueprint.route('/your-extracts/<extract_id>', methods=['GET'])
@util.errors_logged
@check_authentication
def get_extract(extract_id):
    '''
    '''
    id, nickname, avatar, _, access_token = session_info(session)
    api_key = get_odes_key(access_token)

    with data.connect(current_app.config['DB_DSN']) as db:
        extract = get_odes_extract(db, extract_id, api_key)

    if extract is None:
        raise ValueError('No extract {}'.format(extract_id))

    if extract.odes.links:
        downloads = {d.format: d for d in populate_link_downloads(extract.odes.links)}
    else:
        downloads = None

    return render_template('extract.html', extract=extract, downloads=downloads,
                           util=util, user_id=id, user_nickname=nickname, avatar=avatar)
