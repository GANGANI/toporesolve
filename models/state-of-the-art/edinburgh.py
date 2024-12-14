import json
import networkx as nx
import subprocess
import time
import xmltodict
from random import randint

from geopy.distance import great_circle
from genericCommon import dumpJsonToFile
from genericCommon import getDictFromJson
from genericCommon import search_geonames
from genericCommon import writeTextToFile
from genericCommon import genericErrorInfo

def evaluate_place_resolver(gold_file_path, match_proximity_radius_miles=25):

    print('\nevaluate_place_resolver():')
    gazetteer_aliases = {
        'geonames': 'ge',
        'openstreetmap': 'op', 
        'google': 'gg',
        'google_localized': 'gl'
    }
    TP = 0
    FP = 0
    FN = 0
    place_counter = 0
    eval_report = {'experiments': []}
    
    start_time = time.time()
    with open(gold_file_path, encoding="utf-8") as infile:
        for place in infile:
            
            place_counter += 1
            place = getDictFromJson(place)
            if( len(place) == 0 ):
                continue
            
            ref_coords = (place['lat_long'][0], place['lat_long'][1])
            sentences = '.'.join([s['sent'] for s in place['context']['sents']])
            result = edin_geoparse(place['entity'], sentences, ref_coords, match_proximity_radius_miles, search_loc_city=place['media_dets']['location_name'], search_loc_state=place['media_dets']['state'])
            
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

            #if( place_counter == 1000 ):
            #    break

    params = {}
    params['search_loc_city'] = 'multiple'
    params['search_loc_state'] = 'multiple'
    params['ref_coords'] = ()

    eval_report['conf_mat'] = {'TP': TP, 'TN': None, 'FP': FP, 'FN': FN}
    print('result:', 'TP:', TP, 'FP:', FP, 'FN:', FN)
    
    eval_report['params'] = params
    eval_report['runtime_seconds'] = time.time() - start_time

    expr_params = 'ed'

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

def edin_geoparse(ambig_topo, doc, gold_ref_lat_long, match_proximity_radius_miles, search_loc_city='', search_loc_state=''):

    def merge_family_locations(placenames):

        G = nx.DiGraph()
        new_placenames = []
        placenames_dict = {}

        for place in placenames:

            if( 'place' not in place ):
                continue

            if(isinstance(place['place'], dict)):
                place['place'] = [place['place']]

            place['geo'] = place.pop('place')[0]
            placenames_dict[place['@id']] = place
            G.add_node(place['@id'])

            if( '@contained-by' in place ):
                G.add_edge(place['@id'], place['@contained-by'])

        for cc in nx.weakly_connected_components(G):
            cc = sorted(list(cc))
            
            if( len(cc) > 1 ):
                new_name = placenames_dict[cc[0]]['@name']
                for place in cc[1:]:  
                    new_name += ', ' + placenames_dict[place]['@name']
                placenames_dict[cc[0]]['@name'] = new_name
            
            new_placenames.append( placenames_dict[cc[0]] )
            
        return new_placenames

    print('ambig_topo:', ambig_topo)
    print('sentence:')
    print(doc.strip())

    matched_ref = None
    placenames = []

    search_loc_city_state = f'{search_loc_city} {search_loc_state}'
    media_loc = ()
    if( search_loc_city_state.strip() != '' ):
        media_loc = search_geonames(search_loc_city_state)
        media_loc = () if len(media_loc['toponyms']) == 0 else (media_loc['toponyms'][0]['latitude'], media_loc['toponyms'][0]['longitude'])

    media_loc = '' if len(media_loc) == 0 else f'-l {media_loc[0]} {media_loc[1]} 804 3'
    rand_slug = randint(0, 100000000000)

    doc_in_filename = f'/tmp/in-edin-parse-doc-{rand_slug}.txt'
    doc_out_filename = f'out-edin-parse-doc-{rand_slug}.txt'
    res_in_filename = f'/tmp/out-edin-parse-doc-{rand_slug}.txt.gaz.xml'

    parser_path = '/mnt/c/Users/great/Desktop/news-deserts-nlp-greatness/geoparser-1.3/geoparser-1.3/scripts/run'

    xmlstr = ''
    try:
        
        writeTextToFile(doc_in_filename, doc)
        cmd = f'cat {doc_in_filename} | {parser_path} -t plain -g geonames {media_loc} -o /tmp/ {doc_out_filename}; cat {res_in_filename}; rm /tmp/*{rand_slug}*'
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        placenames = ps.communicate()[0].decode('utf-8')
        xmlstr = placenames.split('Using OpenStreetMap tiles instead.')[-1]
        placenames = xmltodict.parse(xmlstr)

        if( 'placenames' in placenames ):
            placenames = placenames['placenames']['placename']
        elif( 'placename' in placenames ):
            placenames = placenames['placename']
        else:
            print('\nUnexpected format'*20)
            print(json.dumps(placenames))
            print()
            

        if( isinstance(placenames, list) is False ):
            placenames = [placenames]
    except:
        genericErrorInfo()
        print('xmlstr:')
        print(xmlstr)
        print()

    
    placenames = merge_family_locations(placenames)
    for i in range(len(placenames)):
        g = placenames[i]
        loc_coords = (g['geo']['@lat'], g['geo']['@long'])

        dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
        sim_name = jaccard_sim(ambig_topo,g['@name'])

        g['sim_name'] = sim_name
        print('\t', g['@name'], sim_name, dist_miles)

    
    placenames = sorted(placenames, key=lambda x: x['sim_name'], reverse=True)
    if( len(placenames) != 0 ):
        topo = placenames[0]
        loc_coords = (topo['geo']['@lat'], topo['geo']['@long'])
        dist_miles = great_circle(loc_coords, gold_ref_lat_long).miles
        matched_ref = True if dist_miles <= match_proximity_radius_miles else False
        out = '\t{}, dist. (miles) from ref: {:.2f}, matched ref: {}\n\t{}\n'.format(topo['@name'], dist_miles, matched_ref, '{} vs. {}'.format(loc_coords, gold_ref_lat_long) )
        print(out)
        topo = [topo]
    else:
        topo = placenames
        matched_ref = None
    
    return {
        'toponym': topo,
        'matched_ref': matched_ref
    }

    

gold_file_path = 'evaluation/merged/disambiguated/FAC_2023-06-07T160700Z.jsonl'
# gold_file_path = 'evaluation/merged/disambiguated/LOC_2023-06-07T160700Z.jsonl'
# gold_file_path = 'evaluation/merged/disambiguated/GPE_2023-06-07T160700Z.jsonl'
evaluate_place_resolver(gold_file_path)
