from os import environ
from . import apply_blueprint
from .oauth import apply_oauth_blueprint
from flask import Flask

app = Flask(__name__)
apply_blueprint(app)
apply_oauth_blueprint(app)