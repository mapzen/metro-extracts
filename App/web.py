from os import environ
from . import apply_blueprint
from .oauth import apply_oauth_blueprint
from .odes import apply_odes_blueprint
from flask import Flask

def make_app():
    app = Flask(__name__)
    apply_blueprint(app)
    apply_oauth_blueprint(app)
    apply_odes_blueprint(app)

    return app

app = make_app()
