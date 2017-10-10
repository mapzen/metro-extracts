from flask import Blueprint, url_for, Response, current_app

blueprint = Blueprint('Alt-Redirects', __name__)

def apply_redirect_blueprint(app):
    '''
    '''
    app.logger.debug('redirect blue')
    app.register_blueprint(blueprint)

@blueprint.route('/data/metro-extracts-alt')
def index():
    return Response('', status=301, headers={'Location': '/data/metro-extracts'})

@blueprint.route('/data/metro-extracts-alt/')
def trailing_slash():
    return Response('', status=301, headers={'Location': '/data/metro-extracts/'})

@blueprint.route('/data/metro-extracts-alt/<path:path>')
def trailing_path(path=''):
    location = '/data/metro-extracts/' + path
    return Response('', status=301, headers={'Location': location})
