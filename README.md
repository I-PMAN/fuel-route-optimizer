# Fuel Route Optimizer API

## Overview

A Django REST API that calculates the most cost-effective fuel stops along a
driving route between two US locations.

Given a start and end location, the API:

1. Geocodes both locations and fetches the route geometry and distance.
2. Simulates fuel consumption for a vehicle with a fixed range and efficiency.
3. Selects the cheapest feasible sequence of fuel stops along the route.
4. Calculates the total fuel cost for the trip.
5. Returns the route and stops as GeoJSON so they can be plotted on a map.

The optimizer uses a cost-minimizing greedy strategy and only considers fuel
stations in US states.

---

## Features

- Geocoding via the Nominatim (OpenStreetMap) API
- Route geometry and distance via the OpenRouteService (ORS) API
- Cost-minimizing fuel stop selection (greedy "gas station" algorithm)
- 500-mile range simulation with multiple fill-ups as needed
- US-only station filtering
- Total fuel cost calculation at 10 MPG
- GeoJSON output for map visualization
- Swagger / OpenAPI documentation
- PostgreSQL (or SQLite for local development)

---

## Tech Stack

- Python 3.13
- Django (latest stable, 6.x)
- Django REST Framework
- drf-spectacular (OpenAPI / Swagger)
- PostgreSQL (SQLite supported for local dev)
- OpenRouteService (routing) + Nominatim (geocoding)
- uv (dependency management)
- Vercel (serverless deployment)

---

## Assumptions

- Vehicle range: 500 miles per tank
- Fuel efficiency: 10 MPG (so a full tank ≈ 50 gallons)
- The vehicle starts with a full tank, which is treated as already paid for —
  cost only accrues for fuel purchased at stops along the route. A trip shorter
  than one tank (≤ 500 miles) therefore needs no stops and reports a fuel cost
  of $0.00.
- Only US fuel stations are considered
- Fuel prices come from the provided dataset (pre-geocoded fixture)

---

## External APIs and Call Budget

To keep the API fast and within the "don't call the routing API too much"
requirement, each request makes:

- **1 routing call** to OpenRouteService.
- **2 geocoding calls** to Nominatim (one each for start and end).

The route geometry from the single routing call is reused to build both the
fuel-stop analysis and the GeoJSON map output — no additional routing calls.

---

## Setup Instructions

### 1. Clone the repository

```
git clone https://github.com/I-PMAN/fuel-route-optimizer.git
cd fuel-route-optimizer
```

### 2. Create a virtual environment and install dependencies

Using uv (recommended; matches the project's lockfile):

```
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv sync
```

Or using pip:

```
python3.13 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```
DATABASE_URL=postgres://user:password@localhost:5432/fuel_route
ORS_API_KEY=your_openrouteservice_api_key
```

- Get a free `ORS_API_KEY` at https://openrouteservice.org/.
- To skip installing PostgreSQL locally, use SQLite instead:
  `DATABASE_URL=sqlite:///db.sqlite3`

### 4. Create the logs directory

```
mkdir -p logs
```

This directory is required — the logging configuration writes to `logs/django.log`.

### 5. Run migrations

```
python manage.py migrate
```

### 6. Load the pre-geocoded fuel stations

```
python manage.py loaddata fuel_stations.json
```

Required before testing the API. (If your database is already populated, e.g.
a shared/hosted database, you can skip this.)

### 7. Run the server

```
python manage.py runserver
```

---

## API Endpoints

Swagger UI is available at `/api/docs/`.

### `POST /api/fuel-route/`

Returns the full result: distance, fuel stops with cost breakdown, total cost,
the encoded route polyline, and a GeoJSON FeatureCollection.

Request:

```
curl -X POST http://127.0.0.1:8000/api/fuel-route/ \
  -H "Content-Type: application/json" \
  -d '{ "start": "Los Angeles, CA", "end": "Houston, TX" }'
```

Example response (illustrative — exact stops, gallons and totals depend on the
current dataset prices and the live route; `route_geometry` and `route_geojson`
abbreviated for brevity). Note that gallons per stop vary: the optimizer buys
only what's needed and never more than a full tank.

```
{
  "distance_miles": 1546.04,
  "no_of_stops": 3,
  "fuel_stops": [
    {
      "name": "TCI PHOENIX",
      "city": "Phoenix",
      "state": "AZ",
      "latitude": 33.4484367,
      "longitude": -112.074141,
      "price": 2.9223,
      "gallons": 39.64,
      "cost": 115.84
    }
  ],
  "total_fuel_cost": 305.71,
  "route_geometry": "...",
  "route_geojson": { "type": "FeatureCollection", "features": [ ... ] }
}
```

### `POST /api/fuel-route/geojson/`

Returns **only** a GeoJSON FeatureCollection (route line + fuel stop markers)
as the entire response body. This makes it easy to visualize the route.

### `GET /api/map/`

Returns an interactive HTML map (Leaflet + OpenStreetMap) of the route with a
clickable marker at each fuel stop. Open it in a browser; add query parameters
to auto-load a route:

```
http://127.0.0.1:8000/api/map/?start=Los Angeles, CA&end=Houston, TX
```

---

## Viewing the Route on a Map

The easiest option is the built-in viewer — open `GET /api/map/` in a browser
(optionally with `?start=...&end=...`) and the route plus fuel-stop markers
render automatically. Click a marker to see its price, gallons, and cost.

Alternatively, to inspect the raw GeoJSON:

1. Call `POST /api/fuel-route/geojson/` (e.g. from Swagger UI).
2. Copy the entire response body, or use Swagger's **Download** button.
3. Paste it into https://geojson.io (or drag the downloaded file onto the map).

---

## Optimization Strategy

A cost-minimizing greedy algorithm (the classic "gas station" problem),
respecting the tank's physical capacity:

- The vehicle starts with a full tank (treated as already paid for).
- At each refuel point, all stations reachable on the current tank are
  considered.
- If a cheaper station is reachable within a full tank, the vehicle buys only
  enough fuel to reach it.
- Otherwise it tops up toward the destination at the cheapest reachable
  station — buying only the deficit, never more than the tank can hold.
- The fuel needed to cover the final leg to the destination is included in the
  total cost.

This minimizes total spend while respecting the 500-mile range and tank
capacity, without the overhead of full dynamic programming.

---

## Error Handling

The API returns a `400` with an `error` message for cases such as:

- A location that cannot be geocoded.
- No fuel station reachable within range on some segment of the route.

Example:

```
{ "error": "No reachable fuel station within range." }
```

---

## Running Tests

The test suite covers the optimizer (cost minimization, tank-capacity limits,
final-leg costing, preferring cheaper stations, and unreachable-route handling)
and the API endpoints (request validation, geocode-failure handling, and the
GeoJSON/map responses). The optimizer tests build a deterministic synthetic
route, so they need no real data or network access.

Run them against SQLite (avoids needing CREATE DATABASE privileges on a managed
Postgres, and keeps tests offline):

```
DATABASE_URL=sqlite:///db.sqlite3 ORS_API_KEY=x python manage.py test apps.routing
```

---

## Project Structure

```
apps/
  fuel/
    models.py                      # FuelStation, CityCoordinate
    management/commands/           # data import / geocoding commands
  routing/
    services/
      geocode.py                   # Nominatim geocoding
      routing.py                   # OpenRouteService routing (single call)
      geospatial.py                # polyline decoding
      route_processing.py          # cumulative distance along the route
      fuel_optimizer.py            # cost-minimizing stop selection
      geojson_builder.py           # builds the GeoJSON FeatureCollection
    serializers.py
    views.py                       # API endpoints + HTML map view
    urls.py
    test_fuel_route.py             # optimizer + endpoint tests
fuel_route_planner/                # Django project settings
fuel-prices-for-be-assessment.csv  # source fuel price dataset
fuel_stations.json                 # pre-geocoded station fixture
```

---

## Notes

- Fuel stations are pre-geocoded and loaded from a fixture.
- Only US states are supported.
- Routing is powered by the OpenRouteService API; geocoding by Nominatim.
- The optimizer assumes a fixed tank size and MPG.
