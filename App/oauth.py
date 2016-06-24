from os import environ
from sys import stderr
from urllib.parse import urlencode, urlunparse, urljoin
from traceback import print_exc
from functools import wraps
from uuid import uuid4
from time import time

from requests import get, post
from requests_oauthlib import OAuth2Session

from flask import (
    Blueprint, session, request, render_template, redirect, make_response,
    current_app, Response
    )

blueprint = Blueprint('OAuth', __name__, template_folder='templates/oauth')
hardcoded_auth = ('mapzen', 'kMUjnU53')

def apply_oauth_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)
    app.secret_key = environ.get('FLASK_SECRET_KEY')
    app.config['GITHUB_CLIENT_ID'] = environ.get('GITHUB_CLIENT_ID')
    app.config['GITHUB_CLIENT_SECRET'] = environ.get('GITHUB_CLIENT_SECRET')

def errors_logged(route_function):
    '''
    '''
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        try:
            result = route_function(*args, **kwargs)
        except Exception as e:
            print_exc(file=stderr)
            raise
            return Response('Nope.', headers={'Content-Type': 'text/plain'}, status=500)
        else:
            return result
    
    return wrapper

def check_authentication(untouched_route):
    '''
    '''
    @wraps(untouched_route)
    def wrapper(*args, **kwargs):
        ''' Prompt user to authenticate with password or Github if necessary.
        '''
        if current_app.config['GITHUB_CLIENT_ID'] is None:
            auth = request.authorization
            if not auth or (auth.username, auth.password) != hardcoded_auth:
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials',
                    401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
                    )
        
        else:
            access_token = session.get('token', {}).get('access_token', None)
            user_id = session.get('id', {}).get('id', None)
        
            if access_token is None or user_id is None:
                return make_401_response()

            resp = get('https://mapzen.com/developers/oauth_api/current_developer',
                       headers={'Authorization': 'Bearer {}'.format(access_token)})
            
            if resp.status_code in range(400, 499):
                return make_401_response()
        
        return untouched_route(*args, **kwargs)
    
    return wrapper

def make_401_response():
    ''' Create an HTTP 401 Not Authorized response to trigger Github OAuth.
    
        Start by redirecting the user to Github OAuth authorization page:
        http://developer.github.com/v3/oauth/#redirect-users-to-request-github-access
    '''
    state_id = str(uuid4())
    session['states'] = [dict(redirect=request.url, created=time())]

    args = dict(href='https://mapzen.com/oauth/authorize')
    args.update(redirect_uri=urljoin(request.url, '/oauth/callback'))
    args.update(client_id=current_app.config['GITHUB_CLIENT_ID'])

    return make_response(render_template('error-authenticate.html', **args), 401)

def absolute_url(request, location):
    '''
    '''
    if 'X-Forwarded-Proto' not in request.headers:
        return location
    
    scheme = request.headers.get('X-Forwarded-Proto')
    actual_url = urlunparse((scheme, request.host, request.path, None, None, None))
    return urljoin(actual_url, location)

@blueprint.route('/oauth/logout', methods=['POST'])
def logout():
    '''
    '''
    if 'id' in session:
        session.pop('id')

    if 'token' in session:
        session.pop('token')
    
    return redirect(absolute_url(request, '/'), 302)

@blueprint.route('/oauth/hello')
@check_authentication
@errors_logged
def hello():
    return '''
        <form action="/oauth/logout" method="post">
        Hey there, {}.
        <button>log out</button>
        </form>
        '''.format(session['id']['nickname'])

@blueprint.route('/oauth/callback')
@errors_logged
def get_oauth_callback():
    ''' Handle Github's OAuth callback after a user authorizes.
    
        http://developer.github.com/v3/oauth/#github-redirects-back-to-your-site
    '''
    if 'error' in request.args:
        return render_template('error-oauth.html', reason="you didn't authorize access to your account.")
    
    try:
        code = request.args['code']
    except:
        return render_template('error-oauth.html', reason='missing code in callback.')
    
    try:
        state = session['states'].pop()
    except:
        return render_template('error-oauth.html', reason='session state was empty?')
    
    #
    # Exchange the temporary code for an access token:
    # http://developer.github.com/v3/oauth/#parameters-1
    #
    data = dict(client_id=current_app.config['GITHUB_CLIENT_ID'],
                client_secret=current_app.config['GITHUB_CLIENT_SECRET'],
                redirect_uri=urljoin(request.url, '/oauth/callback'),
                code=code, grant_type='authorization_code')

    resp = post('https://mapzen.com/oauth/token', urlencode(data))
    auth = resp.json()
    
    if 'error' in auth:
        return render_template('error-oauth.html', reason='Github said "%(error)s".' % auth)
    
    elif 'access_token' not in auth:
        return render_template('error-oauth.html', reason="missing `access_token`.")
    
    session['token'] = auth
    
    #
    # Figure out who's here.
    #
    url = 'https://mapzen.com/developers/oauth_api/current_developer'
    _ = OAuth2Session(current_app.config['GITHUB_CLIENT_ID'], token=session['token']).get(url).json()
    id = dict(id=_['id'], email=_['email'], nickname=_['nickname'], keys_url=_['keys'])
    session['id'] = id
    
    other = redirect(absolute_url(request, state['redirect']), 302)
    other.headers['Cache-Control'] = 'no-store private'
    other.headers['Vary'] = 'Referer'

    return other
