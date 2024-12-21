import time
import re
import json
import requests
from geopy.distance import great_circle
import soton_corenlppy, geoparsepy, pickle

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
    with open(gold_file_path, 'r', encoding='utf-8') as infile:
        for place in infile:
            
            place_counter += 1
            place = getDictFromJson(place)
            if( len(place) == 0 ):
                continue

            
            ref_coords = (place['lat_long'][0], place['lat_long'][1])
            sentences = '.'.join([s['sent'] for s in place['context']['sents']])
            result = geoparsepy_func(place['entity'], sentences, ref_coords, match_proximity_radius_miles, place['is_state'])
            
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

    expr_params = 'gp'

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

def get_coords(id, type):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    {type}({id});
    out geom;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    if type == 'relation' or type == 'way':
        bounds = data['elements'][0]['bounds']
        lat = (bounds['minlat'] + bounds['maxlat']) / 2
        lon = (bounds['minlon'] + bounds['maxlon']) / 2
    elif type == 'node':
        bounds = data['elements'][0]
        lat = (bounds['lat'])
        lon = (bounds['lon'])

    return (lat, lon)

def get_node_name(id):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    node({id});
    out geom;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    name = data['elements'][0]['tags'].get('name')

    return [name]

def load_geojson_boundary(is_state):
    try:
        with open(f'C:/Users/great/Desktop/news-deserts-nlp-greatness/rule-based/boundaries/{is_state}') as f:
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

def geoparsepy_func(ambig_topo, doc, gold_ref_lat_long, match_proximity_radius_miles, is_state):
    
    dictGeospatialConfig = geoparsepy.geo_parse_lib.get_geoparse_config( 
	lang_codes = ['en'],
	whitespace = u'"\u201a\u201b\u201c\u201d()',
	sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
	punctuation = """,;\/:+-#~&*=!?""",
	)

    with open('cached_locations.pkl', 'rb') as f:
        cached_locations = pickle.load(f)

    with open('indexed_locations.pkl', 'rb') as f:
        indexed_locations = pickle.load(f)

    osmid_lookup = geoparsepy.geo_parse_lib.calc_osmid_lookup( cached_locations )

    dictGeomResultsCache = {}
    matched_ref = None
    topo = []

    try:
        listTokenSets = []
        listTokenSets.append(soton_corenlppy.common_parse_lib.unigram_tokenize_text(text = doc, dict_common_config = dictGeospatialConfig))
        listMatchSet = geoparsepy.geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )
        strGeom = 'POINT(-1.4052268 50.9369033)'
        listMatch = listMatchSet[0]
        listLocMatches = geoparsepy.geo_parse_lib.create_matched_location_list( listMatch, cached_locations, osmid_lookup )
        geoparsepy.geo_parse_lib.filter_matches_by_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache )
        geoparsepy.geo_parse_lib.filter_matches_by_geom_area( listLocMatches, dictGeospatialConfig )
	
        setOSMID = set([])
        geolocated_ents = []
        
        for nMatchIndex in range(len(listLocMatches)) :
            x = {}
            strGeom = listLocMatches[nMatchIndex][4]
            x['strGeom'] = strGeom
            tupleOSMID = listLocMatches[nMatchIndex][5]
            x['tupleOSMID'] = tupleOSMID
            dictOSMTags = listLocMatches[nMatchIndex][6]
            if not tupleOSMID in setOSMID :
                setOSMID.add( tupleOSMID )
                listNameMultilingual = geoparsepy.geo_parse_lib.calc_multilingual_osm_name_set( dictOSMTags, dictGeospatialConfig )
                if not listNameMultilingual:
                    listNameMultilingual = get_node_name(tupleOSMID[0])
                # print(listNameMultilingual)
                strName = listNameMultilingual[0]
                x['strName'] = strName
                strOSMURI = geoparsepy.geo_parse_lib.calc_OSM_uri( tupleOSMID, strGeom )
                x['strOSMURI'] = strOSMURI
                geolocated_ents.append(x)


        print('ambig_topo:', ambig_topo)
        print('sentence:')
        print(doc.strip())

        pattern = r'http[s]?://www\.openstreetmap\.org/(node|way|relation)/(\d+)'

        for i in range(len(geolocated_ents)):
            g = geolocated_ents[i]
            match = re.search(pattern, g['strOSMURI'])
            osm_type = match.group(1)
            osm_id = match.group(2)

            loc_coords = get_coords(osm_id, osm_type)
            g['lat'] = loc_coords[0]
            g['lon'] = loc_coords[1]
            dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
            sim_name = jaccard_sim(ambig_topo, g['strName'])
            g['sim_name'] = sim_name
            print('\t', g['strName'], sim_name, dist_miles)
        geolocated_ents = sorted(geolocated_ents, key=lambda x: x['sim_name'], reverse=True)

        if( len(geolocated_ents) != 0 ):
            topo = geolocated_ents[0]

            loc_coords = (topo['lat'], topo['lon'])
            dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
            if is_state:
                bounds = load_geojson_boundary(is_state)
                matched_ref = is_within_boundary(loc_coords, bounds)
            else:
                matched_ref = True if dist_miles <= match_proximity_radius_miles else False
            out = '\t{}, dist. (miles) from ref: {:.2f}, matched ref: {}\n\t{}\n'.format(topo['strName'], dist_miles, matched_ref, '{} vs. {}'.format(loc_coords, gold_ref_lat_long) )
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