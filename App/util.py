from sys import stderr
from traceback import print_exc
from functools import wraps
from hashlib import sha1
from os.path import exists, join, splitext
from time import time
import os, tempfile

from flask import Response
import requests

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

def _get_remote_fragment(url):
    sha = sha1(url.encode('utf8')).hexdigest()
    _, ext = splitext(url)
    path = join(tempfile.tempdir, sha+ext)
    
    def new_enough(filename):
        ctime, oldest = os.stat(filename).st_ctime, time() - 300
        return bool(ctime > oldest)
    
    if not (exists(path) and new_enough(path)):
        with open(path, 'w') as file:
            resp = requests.get(url)
            file.write(resp.text)
    
    with open(path, 'r') as file:
        return file.read()

def get_mapzen_navbar():
    return _get_remote_fragment('https://mapzen.com/site-fragments/navbar.html')

def get_mapzen_footer():
    return _get_remote_fragment('https://mapzen.com/site-fragments/footer.html')
