# Fuel Route Optimizer API

## Overview

This project is a Django REST API that calculates optimal fuel stops between two US cities.

Given a start and end city, the API:

1. Fetches route distance and geometry
2. Simulates vehicle fuel consumption
3. Selects optimal fuel stops along the route
4. Calculates total fuel cost

The system uses a greedy optimization strategy and limits fuel stations to valid US states only.

---

## Features

- Route distance calculation using OSRM
- Fuel range simulation (500 miles per tank)
- Greedy fuel stop optimization
- US-only station filtering
- Total fuel cost calculation
- REST API endpoint
- PostgreSQL database

---

## Tech Stack

- Python 3.12+
- Django (latest stable)
- Django REST Framework
- PostgreSQL
- OSRM Routing API
- uv (dependency management)

---

## Assumptions

- Vehicle range: 500 miles per tank
- Fuel efficiency: 10 MPG
- Each refill: 50 gallons
- Only US fuel stations are considered

---

Setup Instructions
1. Clone the Repository
git clone https://github.com/YOUR_USERNAME/fuel-route-optimizer.git
cd fuel-route-optimizer
2. Create Virtual Environment

Using uv:

uv venv
source .venv/bin/activate   # Linux / Mac

On Windows:

.venv\Scripts\activate
3. Install Dependencies
uv sync
4. Setup PostgreSQL

Create a database:

CREATE DATABASE fuel_route;

Update your .env or settings.py with DB credentials.

5. Run Migrations
python manage.py migrate
6. Load Pre-Geocoded Fuel Stations
python manage.py loaddata fuel_stations.json

⚠️ This step is required before testing the API.

7. Run the Server
python manage.py runserver


Example API Call

Using curl:

curl -X POST http://127.0.0.1:8000/api/fuel-route/ \
  -H "Content-Type: application/json" \
  -d '{
        "start": "Los Angeles, CA",
        "end": "Houston, TX"
      }'
Example Response
{
  "distance_miles": 1546.04,
  "fuel_stops": [
    {
      "name": "QUIKTRIP #1499",
      "city": "Tucson",
      "state": "AZ",
      "price": 3.06,
      "gallons": 50.0,
      "cost": 153.12
    }
  ],
  "total_fuel_cost": 468.02
}

Optimization Strategy

The system uses a greedy algorithm:

The route is fetched from OSRM.

The vehicle starts with a full tank.

Stations within reachable range are filtered.

Among reachable stations, the cheapest option is selected.

The process repeats until the destination is reached.

This balances cost optimization and feasibility constraints without solving a full dynamic programming problem.


Error Handling

The API returns errors for:

Non-US cities

Unreachable routes

No fuel station within reachable range

Invalid request payload

Example:

{
  "error": "No reachable fuel station within range."
}

Project Structure: 
apps/
  routing/
    services/
      fuel_optimizer.py
      route_service.py
    views.py

route_service.py → fetches route from OSRM

fuel_optimizer.py → handles stop selection logic

views.py → API entry point


Notes

Fuel stations are pre-geocoded and included as a fixture.

Only US states are supported.

External routing is powered by OSRM public API.

Optimization assumes fixed tank size and MPG.

