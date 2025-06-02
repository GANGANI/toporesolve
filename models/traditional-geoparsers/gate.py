import json
import time
import requests

from geopy.distance import great_circle
from shapely.geometry import shape, Point

from util import dumpJsonToFile, getDictFromJson
from NwalaTextUtils.textutils import derefURI, genericErrorInfo

def evaluate_place_resolver(gold_file_path, match_proximity_radius_miles=25):

    print('\nevaluate_place_resolver():')
    TP = 0
    FP = 0
    FN = 0
    place_counter = 0
    eval_report = {'experiments': []}
    
    start_time = time.time()
    with open(gold_file_path) as infile:
        for place in infile:
            
            place_counter += 1
            place = getDictFromJson(place)
            if( len(place) == 0 ):
                continue

            
            ref_coords = (place['lat_long'][0], place['lat_long'][1])
            sentences = '.'.join([s['sent'] for s in place['context']['sents']])
            result = gate_geoparse(place['entity'], sentences, ref_coords, match_proximity_radius_miles, place['is_state'])
            
            eval_report['experiments'].append({
                'reference_place': place,
                'resolved_places': result
            })

            if( result['matched_ref'] is True ):
                TP += 1
            elif( result['matched_ref'] is False ):
                FP += 1
            else:
                FN += 1


    params = {}
    params['search_loc_city'] = 'multiple'
    params['search_loc_state'] = 'multiple'
    params['ref_coords'] = ()

    eval_report['conf_mat'] = {'TP': TP, 'TN': None, 'FP': FP, 'FN': FN}
    print('result:', 'TP:', TP, 'FP:', FP, 'FN:', FN)
    
    eval_report['params'] = params
    eval_report['runtime_seconds'] = time.time() - start_time

    expr_params = 'gy'

    eval_rep_file = '{}.eval.{}.json'.format(gold_file_path.replace('.jsonl', ''), expr_params)
    eval_rep_file = eval_rep_file.replace('/disambiguated/', '/disambiguated/eval-results/')
    
    dumpJsonToFile(eval_rep_file, eval_report)


def send_request(text):
    url = "https://cloud-api.gate.ac.uk/process/yodie-en"
    headers = {
        "Authorization": "Basic Z2NkbHFxbDhldzRyOm45YjVmNWh2aDBiZDJ0OXhwdHdp",
        "Content-Type": "text/plain",
        "Accept": "application/json"
    }

    response = requests.post(url, headers=headers, data=text, timeout=60)

    if response.status_code == 200:
        output = response.json()
    else:
        print(f"Request failed with status code {response.status_code}")
        output = None
    return output


def get_val_for_key(payload, keys):
        
    for opt in keys:
        if( opt in payload ):
            return payload[opt]

    return None

def fmt_geocord(coords, link, src, toponym, rank, src_attribute):

        if( coords is None ):
            return []
        
        locs = []
        for g in coords:
            
            if( g.get('type', '') != 'literal' ):
                continue

            lat_long = g.get('value', '').split(' ')
            if( len(lat_long) != 2 ):
                continue

            try:
                locs.append({ 
                    'latitude': float(lat_long[0]), 
                    'longitude': float(lat_long[1]),
                    'link': link,
                    'src': src,
                    'rk_score': rank,
                    'toponym': toponym
                })
            except:
                genericErrorInfo()

        return locs

def get_dbpedia_coords(data):
    
    wikipedia_title = data["inst"].split('://dbpedia.org/resource/')[-1]
    wikipedia_title = wikipedia_title.strip()
    uri = f'https://dbpedia.org/data/{wikipedia_title}.json'
    final_coords = {}
    if( wikipedia_title == '' ):
        return final_coords

    dbpedia_json = derefURI(uri, 0)

    try:
        dbpedia_json = json.loads(dbpedia_json)
    except:
        genericErrorInfo()
        return final_coords
    
    resource = dbpedia_json.get(f'http://dbpedia.org/resource/{wikipedia_title}', {})
    resource = dbpedia_json.get(f'https://dbpedia.org/resource/{wikipedia_title}', {}) if len(resource) == 0 else resource

    if( len(resource) == 0 ):
        return final_coords

    geo_cord = get_val_for_key(resource, ['http://www.georss.org/georss/point', 'https://www.georss.org/georss/point'])
    final_coords = fmt_geocord(geo_cord, link=uri, src='dbpedia', toponym=wikipedia_title, rank=1, src_attribute='http://www.georss.org/georss/point')
    
    if( len(final_coords) != 0 ):
        return final_coords[0]


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

def load_geojson_boundary(is_state):
    try:
        with open(f'rule-based/boundaries/{is_state}') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"No boundary file found for {is_state}.")
        return None
    
def is_within_boundary(coords, geojson_boundary):
    if geojson_boundary is None:
        return False
    safe_loc_coords = (coords[0] if coords[0] is not None else 0,
                   coords[1] if coords[1] is not None else 0)

    point = Point(safe_loc_coords[1], safe_loc_coords[0])  # Note: Point(longitude, latitude)
    polygon = shape(geojson_boundary['features'][0]['geometry'])
    return polygon.contains(point)

def gate_geoparse(ambig_topo, doc, gold_ref_lat_long, match_proximity_radius_miles, is_state):
    
    matched_ref = None
    topo = []

    try:
        res = send_request(doc)

        print('ambig_topo:', ambig_topo)
        print('sentence:')
        print(doc.strip())
        
        for i in range(len(res["entities"]["Mention"])):
            g = res["entities"]["Mention"][i]
            # print(g)
            result = get_dbpedia_coords(g)
            # print(result)
            if result != None:
                g['lat'], g['lon'], g['name'] = result['latitude'], result['longitude'], result['toponym']
    
            else:
                g['lat'], g['lon'], g['name'] = 0, 0, 'None'
            loc_coords = (g['lat'], g['lon'])
            dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
            sim_name = jaccard_sim(ambig_topo,g['name'])

            g['sim_name'] = sim_name
            print('\t', g['name'], sim_name, dist_miles)
            
        res["entities"]["Mention"] = sorted(res["entities"]["Mention"], key=lambda x: x['sim_name'], reverse=True)
        
        if( len(res["entities"]["Mention"]) != 0 ):
            topo = res["entities"]["Mention"][0]

            loc_coords = (topo['lat'], topo['lon'])
            dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
            if is_state:
                bounds = load_geojson_boundary(is_state)
                matched_ref = is_within_boundary(loc_coords, bounds)
            else:
                matched_ref = True if dist_miles <= match_proximity_radius_miles else False
            out = '\t{}, dist. (miles) from ref: {:.2f}, matched ref: {}\n\t{}\n'.format(topo['name'], dist_miles, matched_ref, '{} vs. {}'.format(loc_coords, gold_ref_lat_long) )
            print(out)
            topo = [topo]

        print()
            
    except:
        genericErrorInfo()

    return {
        'toponym': topo,
        'matched_ref': matched_ref
    }

gold_file_path = 'evaluation/merged/disambiguated/GPE_2024_05_21T134100Z.jsonl'
# gold_file_path = 'evaluation/merged/disambiguated/LOC_2024_05_21T134100Z.jsonl'
# gold_file_path = 'evaluation/merged/disambiguated/FAC_2024_05_21T134100Z.jsonl'
evaluate_place_resolver(gold_file_path)
