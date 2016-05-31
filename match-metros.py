from Levenshtein import distance
from collections import OrderedDict
from operator import itemgetter
from itertools import chain
from csv import DictReader
import re, json

def ordered(d):
    if 'top' in d and 'left' in d and 'bottom' in d and 'right' in d:
        return OrderedDict([(k, d[k]) for k in ('top', 'left', 'bottom', 'right')])
    return OrderedDict([(k, d[k]) for k in sorted(d.keys())])

with open('extracts-2015-05.csv') as file:
    counts = {}
    for row in DictReader(file):
        city_name = row['City'].lower()
        if city_name:
            counts[city_name] = counts.get(city_name, 0) + int(row['Total Events'])
    
    traffic = [n for (n, c) in sorted(list(counts.items()), key=itemgetter(1), reverse=True)]

with open('cities-6f65dd6.json') as file:
    cities_json = file.read()
    cities_data = json.loads(cities_json, object_hook=ordered)

cities_lists = [[(rkey, ckey, city) for (ckey, city) in region['cities'].items()]
                for (rkey, region) in cities_data['regions'].items()]

cities_list = list(chain(*cities_lists))

to_keep = set()
s = lambda string: re.sub(r'[^a-zA-Z0-9]', '', string).lower()

for city_name in traffic:
    distances = [(region_key, city_key, distance(s(city_name), s(city_key)))
                 for (region_key, city_key, _) in cities_list]
    
    region_key, city_key, dist = sorted(distances, key=itemgetter(2))[0]
    
    if dist > 2:
        continue
    
    if len(to_keep) < 200:
        print(city_name)
        to_keep.add((region_key, city_key))

for (region_key, city_key, _) in cities_list:
    if (region_key, city_key) not in to_keep:
        print('remove', region_key, city_key)
        cities_data['regions'][region_key]['cities'].pop(city_key)

with open('cities.json', 'w') as file:
    json.dump(cities_data, file, indent=4)