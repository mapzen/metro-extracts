from uuid import uuid4
from os.path import dirname, join
from contextlib import contextmanager
import psycopg2, psycopg2.extras
import json

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

@contextmanager
def connect(dsn):
    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as db:
            yield db

def add_extract_envelope(db, name, envelope, wof):
    '''
    '''
    extract_id = str(uuid4())[-12:]
    
    db.execute('''
        INSERT INTO extracts
        (id, name, envelope_id, envelope_bbox, wof_name, wof_id, created)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''',
        (extract_id, name, envelope.id, envelope.bbox, wof.name, wof.id))
    
    return extract_id

def get_extract(db, extract_id=None, envelope_id=None, odes=None):
    assert not (extract_id is None and envelope_id is None and odes is None)
    
    values, conditions = [], []
    
    if extract_id is not None:
        conditions.append('id = %s')
        values.append(str(extract_id))
    
    if envelope_id is not None:
        conditions.append('envelope_id = %s')
        values.append(str(envelope_id))
    
    if odes is not None:
        conditions.append('odes_id = %s')
        values.append(odes.id)
    
    db.execute('''
        SELECT id, name, envelope_id, envelope_bbox, odes_id, user_id, wof_name, wof_id, created
        FROM extracts WHERE {}
        '''.format(' AND '.join(conditions)),
        tuple(values))
    
    try:
        id, name, env_id, env_bbox, odes_id, user_id, wof_name, wof_id, created = db.fetchone()
    except TypeError:
        return None

    wof = WoF(wof_id, wof_name)
    envelope = Envelope(env_id, env_bbox)
    odes = odes or ODES(odes_id)

    return Extract(id, name, envelope, odes, user_id, created, wof)

def set_extract(db, extract):
    db.execute('''
        UPDATE extracts
        SET name = %s, envelope_id = %s, envelope_bbox = %s, odes_id = %s,
            user_id = %s, wof_name = %s, wof_id = %s
        WHERE id = %s
        ''',
        (extract.name, extract.envelope.id, extract.envelope.bbox, extract.odes.id,
        extract.user_id, extract.wof.name, extract.wof.id, extract.id))
