#Python3
import json
import os, sys
import itertools
import networkx as nx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from geopy.distance import great_circle

from NwalaTextUtils.textutils import derefURI

def dumpJsonToFile(outfilename, dictToWrite, indentFlag=True, extraParams=None):

	if( extraParams is None ):
		extraParams = {}

	extraParams.setdefault('verbose', True)

	try:
		outfile = open(outfilename, 'w')
		
		if( indentFlag ):
			json.dump(dictToWrite, outfile, ensure_ascii=False, indent=4)#by default, ensure_ascii=True, and this will cause  all non-ASCII characters in the output are escaped with \uXXXX sequences, and the result is a str instance consisting of ASCII characters only. Since in python 3 all strings are unicode by default, forcing ascii is unecessary
		else:
			json.dump(dictToWrite, outfile, ensure_ascii=False)

		outfile.close()

		if( extraParams['verbose'] ):
			print('\twriteTextToFile(), wrote:', outfilename)
	except:
		if( extraParams['verbose'] ):
			print('\terror: outfilename:', outfilename)
		genericErrorInfo()


def getDictFromJson(jsonStr):

	try:
		return json.loads(jsonStr)
	except:
		genericErrorInfo()

	return {}


def genericErrorInfo(slug=''):
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	
	errMsg = fname + ', ' + str(exc_tb.tb_lineno)  + ', ' + str(sys.exc_info())
	print(errMsg + slug)

	return errMsg


def writeTextToFile(outfilename, text, extraParams=None):
	
	if( extraParams is None ):
		extraParams = {}

	if( 'verbose' not in extraParams ):
		extraParams['verbose'] = True

	try:
		with open(outfilename, 'w') as outfile:
			outfile.write(text)
		
		if( extraParams['verbose'] ):
			print('\twriteTextToFile(), wrote:', outfilename)
	except:
		genericErrorInfo()

def search_geonames(location, src_prefix='', merging_proximity_radius_miles=None, **kwargs):

    '''
        Scrapes searches geonames for location and scrapes SERP latitude/longitude information.
        Merges locations within merging_proximity_radius_miles (e.g., 15 miles) radius
    '''
    def get_table_header(rows):
    
        for i in range(len(rows)):
            
            header = rows[i].findAll('th')
            if( len(header) == 0 ):
                continue

            #expected header when location found: [<th></th>, <th>Name</th>, <th>Country</th>, <th>Feature class</th>, <th>Latitude</th>, <th>Longitude</th>]
            header = [h.text.strip() for h in header]
            header = [h.lower().replace(' ', '_') for h in header if h != '']
            return header

        return []

    def get_col_details(cols, src_prefix):
    
        #SITE A
        adm_levels = ''
        location_dets = {'toponym': '', 'link': '', 'src': '', 'latitude': None, 'longitude': None, 'country': '', 'adm_levels': ''}
        for i in range(len(cols)):
            
            potential_toponym = cols[i].find('a')
            if( location_dets['toponym'] == '' and potential_toponym is not None ):
                location_dets['link'] = potential_toponym.get('href', '').strip()
                location_dets['link'] = 'https://www.geonames.org' + location_dets['link'] if location_dets['link'].startswith('/') else location_dets['link']
                location_dets['toponym'] = potential_toponym.text.strip()

            if( location_dets['country'] == '' and potential_toponym is not None ):
                country_link = potential_toponym.get('href', '').strip()
                country = potential_toponym.text if country_link.startswith('/countries') else ''
                location_dets['country'] = country
                if( country != '' ):
                    
                    line_break_tag = cols[i].find('br')
                    if( line_break_tag is not None ):
                        line_break_tag.replace_with(', ')
                    
                    location_dets['adm_levels'] = cols[i].text.strip().replace('>', ',')
            
            potential_geo = cols[i].find('span', 'geo')
            if( potential_geo is None ):
                continue
                
            for geo in ['latitude', 'longitude']:
                latlong = potential_geo.find('span', {'class': geo})
            
                if( latlong is None ):
                    continue
                    
                try:
                    #SITE B
                    #CAUTION: TIGHT-COUPLING (SITES: A, B, C)
                    location_dets[geo] = float(latlong.text.strip())
                    location_dets['src'] = f'{src_prefix}geonames'
                except:
                    genericErrorInfo()


        lat_long_ky = 'https://www.geonames.org/maps/wikipedia_'
        #https://www.geonames.org/maps/wikipedia_56.1231_-3.9467.html         
        if( location_dets['link'].startswith(lat_long_ky) and location_dets['latitude'] is None and location_dets['longitude'] is None ):
            
            latlong = location_dets['link'].replace(lat_long_ky, '').replace('.html', '').split('_')
            if( len(latlong) == 2 ):
                try:
                    #SITE C
                    #CAUTION: TIGHT-COUPLING (SITES: A, B, C)
                    location_dets['latitude'] = float(latlong[0])
                    location_dets['longitude'] = float(latlong[1])
                    location_dets['src'] = f'{src_prefix}wikipedia'
                except:
                    genericErrorInfo()


        return location_dets
    
    def get_next_pg_link(soup):
        
        links = soup.findAll('a')

        for i in range(len(links)-1, -1, -1):
            if( links[i].get('href', '').strip().startswith('/search.html?') ):
                return 'https://www.geonames.org' + links[i]['href'].strip()

        return ''

    query_params = kwargs.get('query_params', '')
    location = location.strip()
    if( location.startswith('https://') ):
        uri = location
        report = kwargs.get('report', {'toponyms': [], 'self': []})
    else:
        uri = f'https://www.geonames.org/search.html?q={quote_plus(location)}{query_params}'
        #&featureClass=A: country, state, region,
        report = {'toponyms': [], 'self': []}

    report['self'].append(uri)
    if( location == '' ):
        return report
    html = derefURI(uri, 0)

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except:
        genericErrorInfo()
        return report

    locations = soup.find('table', {'class': 'restable'})
    if( locations is None ):
        return report

    max_pages = kwargs.get('max_pages', 1)
    cur_page = kwargs.get('cur_page', 1)
    next_pg_link = get_next_pg_link(soup)
    
    rows = locations.findAll('tr')
    header = get_table_header(rows)
    for i in range(len(rows)):
        
        r = rows[i]
        cols = r.findAll('td')
        col_len = len(cols)

        if( col_len < 2 ):
            continue
        
        report['toponyms'].append( get_col_details(cols, src_prefix) )

    
    if( merging_proximity_radius_miles is not None ):
        '''
        print('Before merge:', len(report['toponyms']))
        for t in report['toponyms']:
            print('\t', t)
        print()
        '''
        report['toponyms'] = merge_nearby_locations(report['toponyms'], proximity_radius_miles=merging_proximity_radius_miles)

        '''
        print('After merge:', len(report['toponyms']))
        for t in report['toponyms']:
            print('\t', t)
        '''

    if( next_pg_link != '' and cur_page < max_pages ):
        kwargs['cur_page'] = cur_page + 1
        kwargs['report'] = report
        return search_geonames(next_pg_link, src_prefix=src_prefix, merging_proximity_radius_miles=merging_proximity_radius_miles, **kwargs)

    report['toponyms'] = add_rr_score(report['toponyms'])

    return report


def merge_nearby_locations(geo_locs, proximity_radius_miles=5):
    
    if( proximity_radius_miles <= 0 ):
        return geo_locs

    G = nx.Graph()
    
    new_geo_locs = []
    all_gazetteer_srcs = set()
    
    indices = list( range(len(geo_locs)) )        
    pairs = list(itertools.combinations(indices, 2))

    for fst_indx, sec_indx in pairs:

        fst_geo = (geo_locs[fst_indx]['latitude'], geo_locs[fst_indx]['longitude'])
        sec_geo = (geo_locs[sec_indx]['latitude'], geo_locs[sec_indx]['longitude'])
        dist_miles = great_circle(fst_geo, sec_geo).miles

        if( dist_miles <= proximity_radius_miles ):
            G.add_edge(fst_indx, sec_indx)

        all_gazetteer_srcs.add(geo_locs[fst_indx]['src'])
        all_gazetteer_srcs.add(geo_locs[sec_indx]['src'])

    '''
    print('proximity_radius_miles:', proximity_radius_miles)
    print('all_gazetteer_srcs:')
    print(all_gazetteer_srcs)
    print()
    '''
    for cc in nx.connected_components(G):
        
        gazetteer_df_score = set()
        for indx in cc:
            geo_locs[indx]['skip'] = True
            gazetteer_df_score.add(geo_locs[indx]['src'])
            #print(geo_locs[indx]['toponym'], gazetteer_df_score, geo_locs[indx]['latitude'], geo_locs[indx]['longitude'])
        
        fst_memb_indx = min(cc)
        new_geo_locs.append(geo_locs[fst_memb_indx])
        new_geo_locs[-1]['gazetteer_df_score'] = len(gazetteer_df_score)/len(all_gazetteer_srcs)
        #print(geo_locs[fst_memb_indx]['toponym'], new_geo_locs[-1]['gazetteer_df_score'])
        #print()
    
    for l in geo_locs:
        l.setdefault('gazetteer_df_score', 0)
        if( l.pop('skip', False) is False ):
            new_geo_locs.append(l)

    return new_geo_locs

def add_rr_score(geo_locs):

    for i in range(len(geo_locs)):
        geo_locs[i]['rk_score'] = 1/(i+1)
    
    return geo_locs