import configparser
import os
import folium
import polyline
from scipy.spatial import KDTree
import time
import numpy as np

from login import login

# Strava REST API wrapper
from stravalib.client import Client as StravaClient

color_intensity = [
    "#FF0000", # red
    "#FF4500", # orange red
    "#FFA500", # orange
    "#FFD700", # gold
    "#FFFF00", # yellow
    "#ADFF2F", # green yellow
    "#008000", # green
    "#006400", # dark green
    "#0000FF", # blue
    "#00008B", # dark blue
    "#8A2BE2", # blue violet
]


def generate_map_weighted(activities_map):
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
        indices = tree.query_ball_point(coord, np.sqrt(0.2))
        
        value = 1
        keys_to_delete = []
        
        # Check the nearby points
        for idx in indices:
            nearby_coord, poly_index = coords[idx]
            if poly_index != i:
                value += coord_dict.get(nearby_coord, (0, poly_index))[0]
                keys_to_delete.append(nearby_coord)
        
        # Delete the keys that are too close
        for key in keys_to_delete:
            if key in coord_dict:
                del coord_dict[key]
        
        coord_dict[coord] = (value, i)

    for coord, (value, _) in coord_dict.items():
        # The higher the value, the darker the color
        color = color_intensity[min(value, len(color_intensity) - 1)]
        folium.CircleMarker(coord, radius=5, color=color, fill_color=color).add_to(activities_map)


def generate_full_map(activities_map):
    # iterate over the cache folder and add the polylines to the map
    for file in os.listdir("cache"):
        if file.startswith("map-"):
            with open("cache/{0}".format(file), "r") as f:
                line = polyline.decode(f.read())
                folium.PolyLine(line).add_to(activities_map)

def global_map():
    create_map_cache()

    activities_map = folium.Map(location=[48.8566, 2.3522], zoom_start=5)

    # generate_map_weighted(activities_map) # This will REMOVE the polylines and generate circles with weights - HEAVY !!
    generate_full_map(activities_map) # This will ADD the polylines but no weights (overlapping lines)

    activities_map.save("out/activities_map.html")

    # open the map in the browser
    import webbrowser
    webbrowser.open(os.path.abspath("out/activities_map.html"))




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
    client = login()

    global_map()

    
