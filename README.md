# Fuel Route Optimizer API

## Overview
This is a Django REST API that calculates optimal fuel stops between two US cities.

## Features
- Route distance calculation
- Fuel stop optimization
- US-only station filtering
- Cost calculation

## Tech Stack
- Django
- Django REST Framework
- PostgreSQL
- OSRM Routing API

## How It Works
1. User provides start and end cities.
2. Route distance and geometry are fetched.
3. Fuel stops are optimized using a greedy algorithm.
4. API returns distance, stops, and total cost.

## Run Locally
1. Clone repo
2. Create virtual environment
3. Install dependencies
4. Run migrations
5. Start server

## API Example

POST /api/fuel-route/

{
  "start": "Los Angeles, CA",
  "end": "Houston, TX"
}
