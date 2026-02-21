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

## API Endpoint

### POST `/api/fuel-route/`

### Request Body

```json
{
  "start": "Los Angeles, CA",
  "end": "Houston, TX"
}
