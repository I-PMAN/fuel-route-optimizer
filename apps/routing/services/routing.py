import os
import requests
from django.conf import settings

ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

def get_route(start, end):
    """
    Calls OpenRouteService once and returns:
    - total distance in miles
    - route geometry (encoded polyline)
    """

    api_key = os.getenv("ORS_API_KEY")

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    body = {
        "coordinates": [
            start, 
            end
        ]
    }

    response = requests.post(
        ORS_BASE_URL,
        json=body,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    route = data["routes"][0]

    distance_meters = route["summary"]["distance"]
    distance_miles = distance_meters * 0.000621371

    geometry = route["geometry"]

    return {
        "distance_miles": round(distance_miles, 2),
        "geometry": geometry
    }


