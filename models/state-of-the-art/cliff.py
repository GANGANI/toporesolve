import json, time

from cliff.api import Cliff

from geopy.distance import great_circle
from shapely.geometry import shape, Point

from util import dumpJsonToFile, getDictFromJson, genericErrorInfo

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
            result = cliff_clavin(place['entity'], sentences, ref_coords, match_proximity_radius_miles, place['is_state'])
            
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

    expr_params = 'cc'

    eval_rep_file = '{}.eval.{}.json'.format(gold_file_path.replace('.jsonl', ''), expr_params)
    eval_rep_file = eval_rep_file.replace('/disambiguated/', '/disambiguated/eval-results/')
    
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

def load_geojson_boundary(is_state):
    try:
        with open(f'/mnt/c/Users/great/Desktop/news-deserts-nlp-greatness/rule-based/boundaries/{is_state}') as f:
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

def cliff_clavin(ambig_topo, doc, gold_ref_lat_long, match_proximity_radius_miles, is_state):
    
    cliff = Cliff('http://localhost:8080')
    matched_ref = None
    topo = []

    try:
        res = cliff.parse_text(doc)

        print('ambig_topo:', ambig_topo)
        print('sentence:')
        print(doc.strip())
        
        for i in range(len(res["results"]["places"]["mentions"])):
            g = res["results"]["places"]["mentions"][i]
            loc_coords = (g['lat'], g['lon'])

            dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
            sim_name = jaccard_sim(ambig_topo,g['name'])

            g['sim_name'] = sim_name
            print('\t', g['name'], sim_name, dist_miles)
            
        res["results"]["places"]["mentions"] = sorted(res["results"]["places"]["mentions"], key=lambda x: x['sim_name'], reverse=True)
        
        if( len(res["results"]["places"]["mentions"]) != 0 ):
            topo =res["results"]["places"]["mentions"][0]

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