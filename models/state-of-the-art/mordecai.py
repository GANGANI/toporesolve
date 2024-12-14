import json
import sys
import time
import os

from mordecai3 import Geoparser

from util import dumpJsonToFile
from util import getDictFromJson
from util import genericErrorInfo
from shapely.geometry import shape, Point

def evaluate_place_resolver(gold_file_path):

    print('\nevaluate_place_resolver():')
    trues = 0
    falses = 0
    nones = 0

    place_counter = 0
    eval_report = {'experiments': []}
    
    with open(gold_file_path) as infile:
        for place in infile:
            
            place_counter += 1
            place = getDictFromJson(place)
            if( len(place) == 0 ):
                continue

            state = place['media_dets']['state_abbrev']
            sentences = '.'.join([s['sent'] for s in place['context']['sents']])
            result = mordecai3_geoparse(place['entity'], sentences, state)
            
            eval_report['experiments'].append({
                'reference_place': place,
                'resolved_places': result
            })

            if( result['within_state'] is True ):
                trues += 1
            elif( result['within_state'] is False ):
                falses += 1
            else:
                nones += 1

    eval_report['conf_mat'] = {'true': trues, 'false': falses, 'none': nones}

    eval_rep_file = '{}.eval.json'.format(gold_file_path.replace('.jsonl', ''))
    eval_rep_file = eval_rep_file.replace('/{state}/', '/{state}/eval-results/')
    
    dumpJsonToFile(eval_rep_file, eval_report)

def jaccard_sim(str0, str1):

    def jaccardFor2Sets(firstSet, secondSet):

        intersection = float(len(firstSet & secondSet))
        union = len(firstSet | secondSet)

        if( union != 0 ):
            return  round(intersection/union, 4)
        else:
            return 0
    
    firstSet = set()
    secondSet = set()

    for token in str0:
        firstSet.add(token)

    for token in str1:
        secondSet.add(token)

    return jaccardFor2Sets(firstSet, secondSet)

def load_geojson_boundary(state):
    try:
        with open(f'/mnt/c/Users/great/Desktop/news-deserts-nlp-greatness/mordecai3/boundaries/adm1/{state}.geojson') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"No boundary file found for {state}.")
        return None
    
def is_within_boundary(coords, geojson_boundary):
    if geojson_boundary is None:
        return False
    point = Point(coords[1], coords[0])  # Note: Point(longitude, latitude)
    polygon = shape(geojson_boundary['features'][0]['geometry'])
    return polygon.contains(point)

def mordecai3_geoparse(ambig_topo, doc, state):
    
    geo = Geoparser()
    within_state = None
    topo = []

    try:
        res = geo.geoparse_doc(doc)

        print('ambig_topo:', ambig_topo)
        print('sentence:')
        print(doc.strip())
        
        for i in range(len(res['geolocated_ents'])):
            g = res['geolocated_ents'][i]
            loc_coords = (g['lat'], g['lon'])

            
            sim_name = jaccard_sim(ambig_topo,g['search_name'])

            g['sim_name'] = sim_name
            
        res['geolocated_ents'] = sorted(res['geolocated_ents'], key=lambda x: x['sim_name'], reverse=True)
        
        if( len(res['geolocated_ents']) != 0 ):
            topo = res['geolocated_ents'][0]
            bounds = load_geojson_boundary(state)
            loc_coords = (topo['lat'], topo['lon'])
            
            within_state = is_within_boundary(loc_coords, bounds)
            # out = '\t{}, dist. (miles) from ref: {:.2f}, matched ref: {}\n\t{}\n'.format(topo['search_name'], dist_miles, within_state, '{} vs. {}'.format(loc_coords, gold_ref_lat_long) )
            # print(out)
            topo = [topo]

        print()
            
    except:
        genericErrorInfo()

    return {
        'toponym': topo,
        'within_state': within_state
    }


base_path = 'evaluation/states'

for state_folder in os.listdir(base_path):
    state_folder_path = os.path.join(base_path, state_folder)
    if os.path.isdir(state_folder_path):
        gpe_file_path = os.path.join(state_folder_path, f"{state_folder}_GPE.jsonl")

        if os.path.exists(gpe_file_path):
            normalized_path = gpe_file_path.replace('\\', '/')
            evaluate_place_resolver(normalized_path)
        else:
            print(f"No GPE file found for {state_folder}")
    else:
        print(f"{state_folder} is not a directory")