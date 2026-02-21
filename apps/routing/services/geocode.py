import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_location(location_string):
    headers = {
        "User-Agent": "fuel-route-planner-assessment"
    }

    response = requests.get(
        NOMINATIM_URL,
        headers=headers,
        params={
            "q": f"{location_string}, USA",
            "format": "json",
            "limit": 1
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        raise Exception(f"Location not found: {location_string}")

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    # OSRM expects [lon, lat]
    return [lon, lat]