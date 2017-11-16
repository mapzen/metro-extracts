from os import environ
from os.path import basename
from urllib.parse import urlencode, urlunparse, urljoin
from functools import wraps
from uuid import uuid4
from time import time

from requests import get, post

from flask import (
    Blueprint, session, request, render_template, redirect, make_response,
    current_app, Response, url_for
    )

from . import util

blueprint = Blueprint('OAuth', __name__, template_folder='templates/oauth')
hardcoded_auth = ('mapzen', environ.get('TESTING_PASSWORD'))

mapzen_token_url = environ.get('OAUTH_TOKEN_URL')
mapzen_authorize_url = environ.get('OAUTH_AUTHORIZE_URL')
mapzen_currdev_url = environ.get('CURRENT_USER_URL')

DEFAULT_AVATAR = 'http://placekitten.com/99/99'

def apply_oauth_blueprint(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
    app.secret_key = environ.get('FLASK_SECRET_KEY')
    app.config['MAPZEN_APP_ID'] = environ.get('MAPZEN_APP_ID')
    app.config['MAPZEN_APP_SECRET'] = environ.get('MAPZEN_APP_SECRET')

def check_authentication(untouched_route):
    @wraps(untouched_route)
    def wrapper(*args, **kwargs):
        ''' Prompt user to authenticate with password or Mapzen if necessary.
        '''
        if current_app.config['MAPZEN_APP_ID'] is None:
            auth = request.authorization
            if not auth or (auth.username, auth.password) != hardcoded_auth:
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials',
                    401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
                    )

        else:
            envelope_path = url_for('ODES.get_envelope', envelope_id=basename(request.path))
            is_envelope = bool(envelope_path == request.path)
            is_returning = bool('been here before' in session)
            should_see_interstitial = is_envelope and not is_returning

            access_token = session.get('token', {}).get('access_token', None)
            user_id = session.get('id', {}).get('id', None)

            if access_token is None or user_id is None:
                return make_401_response(should_see_interstitial)

            resp = get(mapzen_currdev_url,
                       headers={'Authorization': 'Bearer {}'.format(access_token)})

            if resp.status_code in range(400, 499):
                return make_401_response(should_see_interstitial)

        return untouched_route(*args, **kwargs)

    return wrapper

def make_401_response(should_see_interstitial):
    ''' Create an HTTP 401 Not Authorized response to trigger Mapzen OAuth.

        Start by redirecting the user to Mapzen OAuth authorization page:
        https://github.com/mapzen/wiki/wiki/mapzen.com-OAuth#1-redirect-users-to-request-mapzen-access
    '''
    state_id = str(uuid4())
    states = session.get('states', {})
    try:
        states[state_id] = dict(redirect=request.url, created=time())
    except TypeError:
        # an older version of this code used a list for session.states.
        states = {state_id: dict(redirect=request.url, created=time())}
    session['states'] = states

    args = dict(redirect_uri=urljoin(request.url, url_for('OAuth.get_oauth_callback')))
    args.update(client_id=current_app.config['MAPZEN_APP_ID'], state=state_id)
    args.update(response_type='code')

    if should_see_interstitial:
        return make_response(render_template('error-authenticate.html', util=util,
                                             href=mapzen_authorize_url, **args), 401)

    return redirect(mapzen_authorize_url+'?'+urlencode(args), 302)

def absolute_url(request, location):
    if 'X-Forwarded-Proto' not in request.headers:
        return location

    scheme = request.headers.get('X-Forwarded-Proto')
    actual_url = urlunparse((scheme, request.host, request.path, None, None, None))
    return urljoin(actual_url, location)

def session_info(session):
    ''' Return user ID, user nickname, user avatar, user keys URL, and OAuth access token.
    '''
    if 'id' not in session or 'token' not in session:
        return None, None, None, None

    return (session['id']['id'], session['id']['nickname'],
            session['id'].get('avatar', DEFAULT_AVATAR), session['token']['access_token'])

@blueprint.route('/oauth/logout', methods=['POST'])
def post_logout():
    if 'id' in session:
        session.pop('id')

    if 'token' in session:
        session.pop('token')

    if 'extract' in session:
        session.pop('extract')

    return redirect(absolute_url(request, url_for('Metro-Extracts.index')), 302)

@blueprint.route('/oauth/hello')
@util.errors_logged
@check_authentication
def get_hello():
    id, nickname, avatar, _ = session_info(session)
    return render_template('oauth/hello.html', user_id=id, user_nickname=nickname, avatar=avatar)

@blueprint.route('/oauth/callback')
@util.errors_logged
def get_oauth_callback():
    ''' Handle Mapzen's OAuth callback after a user authorizes.

        https://github.com/mapzen/wiki/wiki/mapzen.com-OAuth#2-mapzen-redirects-back-to-your-site
    '''
    if 'error' in request.args:
        return render_template('error-oauth.html', util=util,
                               reason="you didn't authorize access to your account.")

    try:
        code, state_id = request.args['code'], request.args['state']
    except:
        return render_template('error-oauth.html', util=util,
                               reason='missing code or state in callback.')

    try:
        state = session['states'].pop(state_id)
    except:
        return render_template('error-oauth.html', util=util,
                               reason='state "{}" not found?'.format(state_id))

    #
    # Exchange the temporary code for an access token:
    # https://github.com/mapzen/wiki/wiki/mapzen.com-OAuth#2-mapzen-redirects-back-to-your-site
    #
    data = dict(client_id=current_app.config['MAPZEN_APP_ID'],
                client_secret=current_app.config['MAPZEN_APP_SECRET'],
                redirect_uri=urljoin(request.url, url_for('OAuth.get_oauth_callback')),
                code=code, grant_type='authorization_code')

    resp = post(mapzen_token_url, urlencode(data))
    auth = resp.json()

    if 'error' in auth:
        return render_template('error-oauth.html', util=util,
                               reason='Mapzen said "%(error)s".' % auth)

    elif 'access_token' not in auth:
        return render_template('error-oauth.html', util=util,
                               reason="missing `access_token`.")

    session['token'] = auth

    #
    # Figure out who's here.
    #
    head = {'Authorization': 'Bearer {}'.format(session['token']['access_token'])}

    d = get(mapzen_currdev_url, headers=head).json()
    id = dict(id=d['id'], email=d['email'], nickname=d['nickname'],
              avatar=d.get('avatar', DEFAULT_AVATAR))
    session['id'] = id

    other = redirect(absolute_url(request, state['redirect']), 302)
    other.headers['Cache-Control'] = 'no-store private'
    other.headers['Vary'] = 'Referer'

    session['been here before'] = 'Yes'
    return other
