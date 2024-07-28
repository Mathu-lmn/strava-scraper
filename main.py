import os
import folium
import polyline
from scipy.spatial import KDTree
import numpy as np

from login import login

# Strava REST API wrapper
from stravalib.client import Client as StravaClient

color_intensity = ['#110746', '#410956', '#6e055f', '#990861', '#bf215d', '#df4152', '#f76544', '#ff8d30', '#ffb716', '#ffe100']


# Experimental : Higher radius but only one circle gets overlapped per polyline
def generate_map_weighted(activities_map, experimental=False):
    list_of_poly = []
    for file in os.listdir("cache"):
        if file.startswith("map-"):
            with open("cache/{0}".format(file), "r") as f:
                line = polyline.decode(f.read())
                list_of_poly.append(line)

    
    coords = [(tuple(coord), i) for i, poly in enumerate(list_of_poly) for coord in poly]

    # Extract just the coordinates for KDTree
    points = np.array([coord for coord, _ in coords])
    
    tree = KDTree(points)
    
    coord_dict = {}
    
    for coord, i in coords:
        # Query the KDTree for nearby points within the specified distance
        distance = experimental and 0.00025 or 0.00015
        indices = tree.query_ball_point(coord, distance, return_sorted=True)

        value = 1
        keys_to_delete = []
        treated_polys = []

        # Check the nearby points
        for idx in indices:
            nearby_coord, poly_index = coords[idx]
            if poly_index != i and poly_index not in treated_polys:
                value += coord_dict.get(nearby_coord, (1, poly_index))[0]
                treated_polys.append(poly_index)
                keys_to_delete.append(nearby_coord)
            elif not experimental:
                keys_to_delete.append(nearby_coord)
        
        # Delete the keys that are too close
        for key in keys_to_delete:
            if key in coord_dict:
                del coord_dict[key]

        coord_dict[coord] = (value, i)

    for coord, (value, _) in coord_dict.items():
        color = color_intensity[min(value, len(color_intensity) - 1)]
        folium.CircleMarker(coord, radius=5, color=color, fill_color=color).add_to(activities_map)


def generate_full_map(activities_map):
    # iterate over the cache folder and add the polylines to the map
    for file in os.listdir("cache"):
        if file.startswith("map-"):
            with open("cache/{0}".format(file), "r") as f:
                line = polyline.decode(f.read())
                folium.PolyLine(line).add_to(activities_map)

def global_map(weighted=False):
    create_map_cache()

    activities_map = folium.Map(location=[48.8566, 2.3522], zoom_start=5)

    if weighted:
        generate_map_weighted(activities_map, False) # This will REMOVE the polylines and generate circles with weights - HEAVY !!
    else:
        generate_full_map(activities_map) # This will ADD the polylines but no weights (overlapping lines)

    activities_map.save("out/activities_map.html")

    if weighted:
        generate_map_weighted(activities_map, True)
        activities_map.save("out/activities_map_experimental.html")

    # open the map in the browser
    import webbrowser
    webbrowser.open(os.path.abspath("out/activities_map.html"))
    if weighted:
        webbrowser.open(os.path.abspath("out/activities_map_experimental.html"))




def create_map_cache():
    activities = client.get_activities()
    print("Loading user's activities...")
    print("Found {0} activities".format(len(list(activities))))
    for activity in activities:
        if os.path.exists("cache/map-{0}.json".format(activity.id)):
            continue

        poly = client.get_activity(activity.id).map.polyline
        if poly:
            with open("cache/map-{0}.json".format(activity.id), "w") as f:
                f.write(poly)
        else:
            print("Activity {0} has no polyline data".format(activity.id))


if __name__ == "__main__":
    try :
        client = login()
    except Exception as e:
        print("Error: {0}".format(e))
        exit(1)

    global_map(True)

    
