import json
from shapely.geometry import shape, Point
from geopy.distance import great_circle

# Function to load JSON data from a file
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Load gold standard and disambiguated data
disambiguation_data = load_json('gpt4/disambiguated_facs_gpt.json')

# Function to compare coordinates
def compare_coordinates(lat_long_gs, lat_long_dis, match_proximity_radius_miles):
    dist_miles = great_circle(lat_long_dis, lat_long_gs).miles
    matched_ref = True if dist_miles <= match_proximity_radius_miles else False
    return matched_ref

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


# Initialize a list to store comparison results
comparison_results = []

# Iterate over each disambiguation entry and compare with gold standard
for disamb_entry in disambiguation_data:
    entity = disamb_entry["entity"]
    disamb_coords = (disamb_entry["disambiguated_info"]["latitude"], disamb_entry["disambiguated_info"]["longitude"])
    source = disamb_entry["source"]
    gs_coords = source["lat_long"]
    match = None
    if (disamb_coords[0] is not None):
        if source['is_state']:
            bounds = load_geojson_boundary(source['is_state'])
            match = is_within_boundary(disamb_coords, bounds)
        else:
            match = compare_coordinates(gs_coords, disamb_coords, match_proximity_radius_miles=25)

    comparison_results.append({
        "entity": entity,
        "gold_standard_coords": gs_coords,
        "disambiguated_coords": disamb_coords,
        "match": match,
        "source": source
    })



# Save the comparison results to a JSON file
with open('gpt4/fac_comparison_results_gpt4.json', 'w') as outfile:
    json.dump(comparison_results, outfile, indent=4)
