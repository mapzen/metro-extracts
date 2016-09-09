from sys import stderr
from traceback import print_exc
from functools import wraps
from hashlib import sha1
from os.path import exists, join, splitext
from urllib.parse import urlunparse
from time import time
import os, tempfile

from flask import Response, render_template
import requests

class KnownUnknown (Exception): pass

class Download:

    def __init__(self, format, url):
        self.format = format
        self.url = url
        
        resp = requests.head(url, timeout=2)
        
        self.size = nice_size(int(resp.headers['Content-Length'])) \
            if ('Content-Length' in resp.headers) else 'Missing'

def nice_size(size):
    KB = 1024.
    MB = 1024. * KB
    GB = 1024. * MB
    TB = 1024. * GB

    if size < KB:
        size, suffix = size, 'B'
    elif size < MB:
        size, suffix = size/KB, 'KB'
    elif size < GB:
        size, suffix = size/MB, 'MB'
    elif size < TB:
        size, suffix = size/GB, 'GB'
    else:
        size, suffix = size/TB, 'TB'

    if size < 10:
        return '{:.1f}{}'.format(size, suffix)
    else:
        return '{:.0f}{}'.format(size, suffix)

def errors_logged(route_function):
    '''
    '''
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        try:
            result = route_function(*args, **kwargs)
        except KnownUnknown as e:
            html = render_template('known-unknown.html', error=str(e), util=globals())
            return Response(html, status=400)
        except Exception as e:
            print_exc(file=stderr)
            html = render_template('unknown-unknown.html', util=globals())
            return Response(html, status=500)
        else:
            return result
    
    return wrapper

def _get_remote_fragment(url):
    sha = sha1(url.encode('utf8')).hexdigest()
    _, ext = splitext(url)
    path = join(tempfile.gettempdir(), sha+ext)
    
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

def get_base_url(request):
    scheme = request.headers.get('CloudFront-Forwarded-Proto') \
          or request.headers.get('X-Forwarded-Proto') \
          or 'http'
    
    netloc = request.headers.get('Host') or request.host
    
    return urlunparse((scheme, netloc, '/', None, None, None))
