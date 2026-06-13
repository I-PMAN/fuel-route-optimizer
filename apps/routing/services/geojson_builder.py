"""
Build a GeoJSON FeatureCollection for a route and its fuel stops.

The result can be pasted directly into a viewer like https://geojson.io to
visualise the route line and each refuel point on a map. This keeps the
"return a map of the route" requirement satisfied without an extra call to the
routing API: we reuse the geometry we already decoded from the single ORS call.

GeoJSON coordinate order is [longitude, latitude] (note: the opposite of the
(lat, lon) tuples produced by polyline.decode), so we flip on the way out.
"""


def build_route_geojson(route_points, fuel_stops):
    """
    route_points : list of (lat, lon) tuples for the full route (decoded polyline)
    fuel_stops   : list of stop dicts, each with latitude/longitude and metadata

    Returns a GeoJSON FeatureCollection dict:
      * one LineString feature for the route
      * one Point feature per fuel stop, carrying its details as properties
    """
    features = []

    # Route as a single LineString.
    line_coordinates = [[lon, lat] for lat, lon in route_points]
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": line_coordinates,
        },
        "properties": {
            "name": "route",
        },
    })

    # One marker per fuel stop.
    for index, stop in enumerate(fuel_stops, start=1):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [stop["longitude"], stop["latitude"]],
            },
            "properties": {
                "stop_number": index,
                "name": stop["name"],
                "city": stop["city"],
                "state": stop["state"],
                "price": stop["price"],
                "gallons": stop["gallons"],
                "cost": stop["cost"],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }