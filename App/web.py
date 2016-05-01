from os import environ
from . import apply_blueprint
from flask import Flask

app = Flask(__name__)
apply_blueprint(app)
