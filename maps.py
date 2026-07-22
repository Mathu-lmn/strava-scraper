import os
import webbrowser

import folium
import numpy as np
import polyline as polyline_lib
from folium.plugins import HeatMap
from scipy.spatial import KDTree

from cache import iter_cached_activities

color_intensity = ['#110746', '#410956', '#6e055f', '#990861', '#bf215d', '#df4152', '#f76544', '#ff8d30', '#ffb716', '#ffe100']

OUT_DIR = "out"
DEFAULT_LOCATION = [48.8566, 2.3522]

# Lets sibling maps (each a separate Leaflet instance in its own dashboard
# iframe) share pan/zoom: on move, broadcast the view to window.parent (the
# dashboard), which relays it to the other map iframes. Deferred to
# window "load" since folium may emit this script before the map variable
# itself is declared - `var` declarations are only visible once their own
# <script> block has run, so we can't rely on tag order and instead wait
# for everything to finish loading and read the map off `window`.
_VIEW_SYNC_SCRIPT = """
<script>
window.addEventListener("load", function () {
  var mapObj = window["__MAP_NAME__"];
  if (!mapObj) return;
  var applyingRemote = false;

  function postView() {
    if (applyingRemote) return;
    try {
      window.parent.postMessage({
        source: "strava-map",
        type: "view",
        center: [mapObj.getCenter().lat, mapObj.getCenter().lng],
        zoom: mapObj.getZoom()
      }, "*");
    } catch (e) {}
  }

  mapObj.on("moveend", postView);

  window.addEventListener("message", function (e) {
    var data = e.data;
    if (!data || data.source !== "strava-dashboard") return;
    applyingRemote = true;
    mapObj.setView(data.center, data.zoom, { animate: false });
    applyingRemote = false;
  });

  try {
    window.parent.postMessage({ source: "strava-map", type: "ready" }, "*");
  } catch (e) {}
});
</script>
"""


def _load_polylines():
    lines = []
    for activity in iter_cached_activities():
        poly = activity.get("polyline")
        if poly:
            lines.append(polyline_lib.decode(poly))
    return lines


def _new_map():
    m = folium.Map(location=DEFAULT_LOCATION, zoom_start=5)
    m.get_root().html.add_child(folium.Element(_VIEW_SYNC_SCRIPT.replace("__MAP_NAME__", m.get_name())))
    return m


def _save_and_open(activities_map, filename, open_browser):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    activities_map.save(path)
    if open_browser:
        webbrowser.open(os.path.abspath(path))
    return path


# Experimental : Higher radius but only one circle gets overlapped per polyline
def generate_map_weighted(activities_map, list_of_poly, experimental=False, progress=None):
    coords = [(tuple(coord), i) for i, poly in enumerate(list_of_poly) for coord in poly]
    if not coords:
        return

    points = np.array([coord for coord, _ in coords])
    tree = KDTree(points)

    coord_dict = {}

    iterable = progress(coords, desc="Computing weighted map", unit="point") if progress else coords
    for coord, i in iterable:
        distance = experimental and 0.00025 or 0.00015
        indices = tree.query_ball_point(coord, distance, return_sorted=True)

        value = 1
        keys_to_delete = []
        treated_polys = []

        for idx in indices:
            nearby_coord, poly_index = coords[idx]
            if poly_index != i and poly_index not in treated_polys:
                value += coord_dict.get(nearby_coord, (1, poly_index))[0]
                treated_polys.append(poly_index)
                keys_to_delete.append(nearby_coord)
            elif not experimental:
                keys_to_delete.append(nearby_coord)

        for key in keys_to_delete:
            if key in coord_dict:
                del coord_dict[key]

        coord_dict[coord] = (value, i)

    for coord, (value, _) in coord_dict.items():
        color = color_intensity[min(value, len(color_intensity) - 1)]
        popup = folium.Popup("Passé {0} fois".format(value))
        folium.CircleMarker(coord, radius=5, color=color, fill_color=color, popup=popup).add_to(activities_map)


def generate_full_map(activities_map, list_of_poly):
    for line in list_of_poly:
        folium.PolyLine(line, color="black", weight=2).add_to(activities_map)


def generate_heatmap(activities_map, list_of_poly, radius=8):
    points = [coord for poly in list_of_poly for coord in poly]
    if points:
        HeatMap(points, radius=radius).add_to(activities_map)


def build_full_map(open_browser=True):
    list_of_poly = _load_polylines()
    if not list_of_poly:
        print("No cached activities with map data found, run without --no-fetch first.")
        return None

    m = _new_map()
    generate_full_map(m, list_of_poly)
    path = _save_and_open(m, "activities_map.html", open_browser)
    print("Full map saved to {0}".format(path))
    return path


def build_weighted_map(open_browser=True, experimental=False, progress=None):
    list_of_poly = _load_polylines()
    if not list_of_poly:
        print("No cached activities with map data found, run without --no-fetch first.")
        return None

    m = _new_map()
    generate_map_weighted(m, list_of_poly, experimental, progress=progress)
    filename = "activities_map_experimental.html" if experimental else "activities_map_weighted.html"
    path = _save_and_open(m, filename, open_browser)
    print("Weighted map saved to {0}".format(path))
    return path


def build_heatmap(open_browser=True):
    list_of_poly = _load_polylines()
    if not list_of_poly:
        print("No cached activities with map data found, run without --no-fetch first.")
        return None

    m = _new_map()
    generate_heatmap(m, list_of_poly)
    path = _save_and_open(m, "activities_heatmap.html", open_browser)
    print("Heatmap saved to {0}".format(path))
    return path
