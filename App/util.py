from sys import stderr
from traceback import print_exc
from functools import wraps

from flask import Response

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
