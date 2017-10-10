import logging
import json
from requests import get

def session_info(session):
    ''' Return user ID, user nickname, user avatar, user keys URL, and OAuth access token.
    '''
    logger = logging.getLogger()

    resp = get('http://haproxy/api/developer.json')

    logger.error(resp.status_code)
    a = json.loads(resp.text)
    logger.error(json.loads(resp.text))
    return 1, 'bob', None, None, None
    if 'id' not in session or 'token' not in session:
        return None, None, None, None, None

    return (session['id']['id'], session['id']['nickname'],
            session['id'].get('avatar', DEFAULT_AVATAR),
            session['id']['keys_url'], session['token']['access_token'])
