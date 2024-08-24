import os
import pandas as pd
import folium
import polyline
from scipy.spatial import KDTree
from shapely.geometry import LineString, Polygon, Point
import numpy as np

color_intensity = ['#110746', '#410956', '#6e055f', '#990861', '#bf215d', '#df4152', '#f76544', '#ff8d30', '#ffb716', '#ffe100']

def get_cached_dataframe():
    rows = []
    for file in os.listdir("cache"):
        if file.startswith("map-"):
            fname = file.split('-')[1].split('.')[0]
            with open(f"cache/{file}", "r") as f:
                line = polyline.decode(f.read())
                for i in range(1, len(line)):
                    rows.append({
                        "vector-in": line[i-1],
                        "vector-out": line[i],
                        "file": fname,
                        "id": i,
                        "weight": 1,
                        "length": ((line[i][0] - line[i-1][0])**2 + (line[i][1] - line[i-1][1])**2)**0.5
                    })
    return pd.DataFrame(rows)


def generate_map_weighted(dataframe, activities_map, debug=False):
    file_max_id = {}
    vect_dict = dataframe
    for file in vect_dict["file"].unique():
        file_max_id[file] = vect_dict[vect_dict["file"] == file]["id"].max()
    vect_dict = vect_dict.sort_values(by="length", ascending=False)

    def build_kdtree(vect_dict):
        points = np.concatenate([vect_dict["vector-in"].tolist(), vect_dict["vector-out"].tolist()])
        return KDTree(points)

    def get_potential_matches(row, kdtree, vect_dict, distance_threshold=0.0004):
        vector_coords = np.array([row["vector-in"][0], row["vector-in"][1], row["vector-out"][0], row["vector-out"][1]])
        
        # Query the KDTree for nearby points for each coordinate of the vector (1 and 2)
        first_point_indices = kdtree.query_ball_point(vector_coords[:2], distance_threshold)
        second_point_indices = kdtree.query_ball_point(vector_coords[2:], distance_threshold)

        first_point_indices = np.unique(np.nonzero(first_point_indices))
        second_point_indices = np.unique(np.nonzero(second_point_indices))

        # Divide the indices by 2 to get the actual indices of the vectors
        first_point_indices = first_point_indices // 2
        second_point_indices = second_point_indices // 2

        potential_matches = vect_dict.iloc[np.unique(np.concatenate([first_point_indices, second_point_indices]))]
        if debug:
            return vect_dict
        return potential_matches
    
    def get_rectangle(row):
        # Calculate the difference in coordinates
        dx = row["vector-out"][0] - row["vector-in"][0]
        dy = row["vector-out"][1] - row["vector-in"][1]
        
        # Handle the vertical line case (when dx is 0)
        if dx == 0:
            x_offset = 0.00001
            y_offset = 0
        else:
            # Calculate the angle of the vector
            angle = np.arctan2(dy, dx)
            
            # Calculate the offsets based on the angle
            x_offset = 0.00001 * np.sin(angle)
            y_offset = 0.00001 * np.cos(angle)

        rectangle = Polygon([
            (row["vector-in"][0] - x_offset, row["vector-in"][1] + y_offset),
            (row["vector-in"][0] + x_offset, row["vector-in"][1] - y_offset),
            (row["vector-out"][0] + x_offset, row["vector-out"][1] - y_offset),
            (row["vector-out"][0] - x_offset, row["vector-out"][1] + y_offset)
        ])
        if not rectangle.is_valid:
            print("Invalid rectangle for vector {0}".format(row))
            print("Coordinates:")
            print([(row["vector-in"][0] - x_offset, row["vector-in"][1] - y_offset), (row["vector-in"][0] + x_offset, row["vector-in"][1] + y_offset), (row["vector-out"][0] + x_offset, row["vector-out"][1] + y_offset), (row["vector-out"][0] - x_offset, row["vector-out"][1] - y_offset)])
        return rectangle

    def process_vector(row, kdtree, vect_dict):
        if row["vector-in"] == row["vector-out"]:
            return [], [], 0
        created_vectors = []
        weight_to_add = 0
        rows_to_delete = []
        potential_matches = get_potential_matches(row, kdtree, vect_dict)
        for j, row2 in potential_matches.iterrows():
            # check if the id is close (same file, id difference is 2 or less)
            if row2["file"] == row["file"] and (abs(row2["id"] - row["id"]) <= 2 and debug == False):
                continue
            rectangle = get_rectangle(row)
            vector2 = LineString([row2["vector-in"], row2["vector-out"]])
            # check if the other vector is in the rectangle
            if vector2.intersects(rectangle) or rectangle.contains(vector2):
                weight_to_add += row2["weight"]

                intersection = vector2.intersection(rectangle)
                if not intersection.is_empty:
                    if isinstance(intersection, Point):
                        # If the intersection is a single point
                        point = (intersection.x, intersection.y)
                        new_vector_1 = {"vector-in": row2["vector-in"], "vector-out": point, "file": row2["file"], "id": file_max_id[row2["file"]] + 1, "weight": 1, "length": ((point[0] - row2["vector-in"][0])**2 + (point[1] - row2["vector-in"][1])**2)**0.5}
                        new_vector_2 = {"vector-in": point, "vector-out": row2["vector-out"], "file": row2["file"], "id": file_max_id[row2["file"]] + 2, "weight": 1, "length": ((row2["vector-out"][0] - point[0])**2 + (row2["vector-out"][1] - point[1])**2)**0.5}
                        file_max_id[row2["file"]] += 2
                    elif isinstance(intersection, LineString):
                        # If the intersection is a line (which means the vector intersects with the rectangle at two points, we only want the external vectors)
                        coords = list(intersection.coords)
                        new_vector_1 = {"vector-in": row2["vector-in"], "vector-out": coords[0], "file": row2["file"], "id": file_max_id[row2["file"]] + 1, "weight": 1, "length": ((coords[0][0] - row2["vector-in"][0])**2 + (coords[0][1] - row2["vector-in"][1])**2)**0.5}
                        new_vector_2 = {"vector-in": coords[1], "vector-out": row2["vector-out"], "file": row2["file"], "id": file_max_id[row2["file"]] + 2, "weight": 1, "length": ((row2["vector-out"][0] - coords[1][0])**2 + (row2["vector-out"][1] - coords[1][1])**2)**0.5}
                        file_max_id[row2["file"]] += 2
                    else:
                        raise ValueError("Unexpected intersection result.")

                    rows_to_delete.append(j)
                    created_vectors.extend([new_vector_1, new_vector_2])

                    break
                else:
                    rows_to_delete.append(j)

        return created_vectors, rows_to_delete, weight_to_add

    kdtree = build_kdtree(vect_dict)

    new_vectors = []
    vect_to_delete = []
    progress = 0
    for index, row in vect_dict.iterrows():
        # check if any other vector is in the rectangle
        new_vects, to_delete, tmp_weight = process_vector(row, kdtree, vect_dict)
        progress += 1
        if progress % 100 == 0:
            print("Processed {0} vectors out of {1}".format(progress, len(vect_dict)))
        vect_dict.at[index, "weight"] += tmp_weight
        if new_vects:
            new_vectors.extend(new_vects)
        if to_delete:
            vect_to_delete.extend(to_delete)

    # Delete the vectors that were split
    vect_dict = vect_dict.drop(vect_to_delete)

    print("Generated {0} new vectors without processing them".format(len(new_vectors)))

    
    sorted = vect_dict.sort_values(by="weight", ascending=False)

    # Add the vectors to the map
    for i, row in sorted.iterrows():
        color = color_intensity[min(int(row["weight"]), len(color_intensity) - 1)]
        popup = folium.Popup("Passé {0} fois".format(row["weight"]))
        folium.PolyLine([row["vector-in"], row["vector-out"]], color=color, weight=5, popup=popup).add_to(activities_map)

    # Add the new vectors to the map
    for row in new_vectors:
        # set color to blue for the new vectors
        folium.PolyLine([row["vector-in"], row["vector-out"]], color="blue", weight=5).add_to(activities_map)




# Experimental : Higher radius but only one circle gets overlapped per polyline
# def old_generate_map_weighted(activities_map, experimental=False):
    # list_of_poly = []
    # for file in os.listdir("cache"):
    #     if file.startswith("map-"):
    #         with open("cache/{0}".format(file), "r") as f:
    #             line = polyline.decode(f.read())
    #             list_of_poly.append(line)

    
    # coords = [(tuple(coord), i) for i, poly in enumerate(list_of_poly) for coord in poly]

    # # Extract just the coordinates for KDTree
    # points = np.array([coord for coord, _ in coords])
    
    # tree = KDTree(points)
    
    # coord_dict = {}
    
    # for coord, i in coords:
    #     # Query the KDTree for nearby points within the specified distance
    #     distance = experimental and 0.00025 or 0.00015
    #     indices = tree.query_ball_point(coord, distance, return_sorted=True)

    #     value = 1
    #     keys_to_delete = []
    #     treated_polys = []

    #     # Check the nearby points
    #     for idx in indices:
    #         nearby_coord, poly_index = coords[idx]
    #         if poly_index != i and poly_index not in treated_polys:
    #             value += coord_dict.get(nearby_coord, (1, poly_index))[0]
    #             treated_polys.append(poly_index)
    #             keys_to_delete.append(nearby_coord)
    #         elif not experimental:
    #             keys_to_delete.append(nearby_coord)
        
    #     # Delete the keys that are too close
    #     for key in keys_to_delete:
    #         if key in coord_dict:
    #             del coord_dict[key]

    #     coord_dict[coord] = (value, i)

    # for coord, (value, _) in coord_dict.items():
    #     color = color_intensity[min(value, len(color_intensity) - 1)]
    #     popup = folium.Popup("Passé {0} fois".format(value))
    #     folium.CircleMarker(coord, radius=5, color=color, fill_color=color, popup=popup).add_to(activities_map)

# This function generates a single map with all the activities polylines
def generate_full_map(activities_map):
    # iterate over the cache folder and add the polylines to the map
    for file in os.listdir("cache"):
        if file.startswith("map-"):
            with open("cache/{0}".format(file), "r") as f:
                line = polyline.decode(f.read())
                folium.PolyLine(line, color="black", weight=2).add_to(activities_map)

# This function creates the cache for the user activities
def create_map_cache(client):
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

def generate_maps(client, weighted=False):
    create_map_cache(client)

    activities_map = folium.Map(location=[48.8566, 2.3522], zoom_start=5)

    generate_map_weighted(get_cached_dataframe(), activities_map)

    activities_map.save("out/activities_map.html")

    # open the map in the browser
    import webbrowser
    webbrowser.open(os.path.abspath("out/activities_map.html"))

# Debug with small sample data
if __name__ == "__main__":
    data = [
        {"vector-in": (0, 0), "vector-out": (-0.00001, 0.00001), "file": "1", "id": 1, "weight": 1, "length": 1},
        {"vector-in": (1, 0), "vector-out": (-0.00002, 0.00001), "file": "1", "id": 2, "weight": 1, "length": 1},
        {"vector-in": (2, -1), "vector-out": (0.00003, 0.00002), "file": "1", "id": 3, "weight": 1, "length": 1},
    ]
    activities_map = folium.Map(location=[48.8566, 2.3522], zoom_start=5)

    generate_map_weighted(pd.DataFrame(data), activities_map, debug=True)

    activities_map.save("out/activities_map.html")
    import webbrowser
    webbrowser.open(os.path.abspath("out/activities_map.html"))