from flask import Blueprint, url_for, Response, current_app

blueprint = Blueprint('Alt-Redirects', __name__)

def apply_redirect_blueprint(app):
    '''
    '''
    app.register_blueprint(blueprint)

@blueprint.route('/data/metro-extracts-alt')
def index():
    return Response('', status=301, headers={'Location': '/data/metro-extracts'})
