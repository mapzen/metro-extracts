from uuid import uuid4
from os.path import dirname, join
from contextlib import contextmanager
import json

from dateutil.parser import parse as parse_datetime

def load_cities(filename):
    '''
    '''
    with open(filename) as file:
        cities = json.load(file)
    
    return cities

cities = load_cities(join(dirname(__file__), '..', 'cities.json'))

class Envelope:
    def __init__(self, id, bbox):
        self.id = id
        self.bbox = bbox

class WoF:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class ODES:
    def __init__(self, id, status=None, created_at=None, processed_at=None, links=None, bbox=None):
        assert type(id) is not int
        assert hasattr(created_at, 'strftime') or (created_at is None)
        assert hasattr(processed_at, 'strftime') or (processed_at is None)
    
        self.id = id
        self.status = status
        self.created_at = created_at
        self.processed_at = processed_at
        self.links = links
        self.bbox = bbox

class Extract:
    def __init__(self, id, name, envelope, odes, user_id, created, wof):
        assert hasattr(created, 'strftime') or (created is None)

        self.id = id
        self.name = name
        self.envelope = envelope
        self.odes = odes
        self.user_id = user_id
        self.created = created
        self.wof = wof

def extractFromDict(d):
    odes = ODES(str(d['id']), status=d['status'], bbox=d['bbox'],
                     links=d.get('download_links', {}),
                     processed_at=(parse_datetime(d['processed_at']) if d['processed_at'] else None),
                     created_at=(parse_datetime(d['created_at']) if d['created_at'] else None))
    envelope = Envelope(d['envelope_id'], [d['bbox']['w'], d['bbox']['s'], d['bbox']['e'], d['bbox']['n']])
    wof = WoF(d['wof_id'], d['wof_name'])
    return Extract(d['ui_id'], d['name'], envelope, odes, d['user_id'], odes.created_at, wof)

