"""
Tests for the fuel-route optimizer and API endpoints.

Run against SQLite (no network, no managed-DB privileges needed):

    DATABASE_URL=sqlite:///db.sqlite3 ORS_API_KEY=x python manage.py test apps.routing

The optimizer tests build a deterministic straight-line route and place
stations directly on it, so the chosen stops and costs are fully predictable.
The view tests stub the network calls (geocoding / routing) so they exercise
request validation and error handling without hitting external APIs.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.fuel.models import FuelStation
from apps.routing.services.route_processing import compute_cumulative_distances
from apps.routing.services.fuel_optimizer import select_fuel_stops, MAX_RANGE, MPG


def straight_route(lat_max, step=0.05, lon=-100.0):
    """A dense north-south line starting at lat 30.0 (≈69 miles per degree)."""
    points, lat = [], 30.0
    while lat <= lat_max + 1e-9:
        points.append((round(lat, 4), lon))
        lat += step
    return compute_cumulative_distances(points)


def place_stations(route, specs):
    """specs: list of (target_mile, price). Snaps each station onto the
    sampled route the optimizer actually uses (route[::10])."""
    FuelStation.objects.all().delete()
    sampled = route[::10]
    for i, (target_mile, price) in enumerate(specs):
        p = min(sampled, key=lambda pt: abs(pt[2] - target_mile))
        FuelStation.objects.create(
            opis_id=str(i), name=f"S{i}", address="x",
            city="T", state="KS",
            latitude=p[0], longitude=p[1], price=price,
        )


class OptimizerTests(TestCase):

    def test_uniform_price_buys_minimal_fuel(self):
        """With one flat price everywhere, cost depends only on gallons bought.
        A full starting tank is free, so only (total - MAX_RANGE) miles of
        range need to be purchased."""
        route = straight_route(43.2)  # ~912 miles
        total = route[-1][2]
        place_stations(route, [(m, 3.00) for m in range(95, 920, 95)])

        stops, cost = select_fuel_stops(route)

        expected = (total - MAX_RANGE) / MPG * 3.00
        self.assertAlmostEqual(cost, expected, delta=1.0)
        self.assertGreaterEqual(len(stops), 2)  # 912 mi cannot be done in one tank

    def test_tank_capacity_is_never_exceeded(self):
        """No single fill may purchase more than a full tank of fuel."""
        route = straight_route(43.2)
        place_stations(route, [(m, 3.00) for m in range(95, 920, 95)])

        stops, _ = select_fuel_stops(route)

        for s in stops:
            self.assertLessEqual(s["gallons"], MAX_RANGE / MPG + 1e-6)

    def test_per_stop_cost_is_consistent(self):
        route = straight_route(43.2)
        place_stations(route, [(m, 3.00) for m in range(95, 920, 95)])

        stops, total_cost = select_fuel_stops(route)

        running = 0.0
        for s in stops:
            # cost is derived from full-precision gallons, so reconstructing it
            # from the rounded gallons field may differ by a cent.
            self.assertAlmostEqual(s["cost"], s["gallons"] * s["price"], delta=0.02)
            running += s["cost"]
        self.assertAlmostEqual(round(running, 2), total_cost, places=2)

    def test_prefers_cheaper_station(self):
        """A cheap station early and an expensive one later: buy as much as
        possible at the cheap one, only a top-up at the expensive one."""
        route = straight_route(40.15)  # ~700 miles
        place_stations(route, [(150, 2.50), (520, 4.00)])

        stops, cost = select_fuel_stops(route)

        self.assertEqual(len(stops), 2)
        cheap, pricey = stops[0], stops[1]
        self.assertLess(cheap["price"], pricey["price"])
        self.assertGreater(cheap["gallons"], pricey["gallons"])
        # Cheaper than naively buying everything at the expensive station.
        total = route[-1][2]
        naive = (total - MAX_RANGE) / MPG * 4.00
        self.assertLess(cost, naive)

    def test_final_leg_is_charged(self):
        """Fuel for the last segment to the destination must be paid for."""
        route = straight_route(40.15)
        place_stations(route, [(150, 2.50), (520, 4.00)])

        stops, cost = select_fuel_stops(route)
        total = route[-1][2]
        purchased_miles = sum(s["gallons"] for s in stops) * MPG
        # Starting tank (free) + purchased range must cover the whole trip.
        self.assertGreaterEqual(MAX_RANGE + purchased_miles + 1.0, total)
        self.assertGreater(cost, 0)

    def test_unreachable_gap_raises(self):
        """A trip that cannot be completed on a single tank from the only
        station must raise, not invent a one-stop solution."""
        route = straight_route(39.6)  # ~660 miles
        place_stations(route, [(100, 3.00)])  # one station far from the end

        with self.assertRaises(Exception):
            select_fuel_stops(route)

    def test_no_stations_near_route_raises(self):
        route = straight_route(43.2)
        FuelStation.objects.all().delete()

        with self.assertRaises(Exception):
            select_fuel_stops(route)


class ViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_missing_field_returns_400(self):
        res = self.client.post(reverse("fuel-route"), {"start": "Dallas, TX"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_geocode_failure_returns_400(self):
        """A geocoding failure should surface as a clean 400, not a 500."""
        with patch("apps.routing.views.geocode_location",
                   side_effect=Exception("Location not found: zzzz")):
            res = self.client.post(
                reverse("fuel-route"),
                {"start": "zzzz", "end": "Houston, TX"}, format="json",
            )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())

    def test_geojson_endpoint_returns_feature_collection(self):
        canned = (
            {"distance_miles": 123.4, "geometry": "_p~iF~ps|U_ulLnnqC"},
            [(34.05, -118.24), (29.76, -95.36)],            # route points (lat, lon)
            [{                                               # one fuel stop
                "name": "S", "city": "T", "state": "TX",
                "latitude": 31.0, "longitude": -100.0,
                "price": 3.0, "gallons": 50.0, "cost": 150.0,
            }],
            150.0,
        )
        with patch("apps.routing.views.compute_fuel_route", return_value=canned):
            res = self.client.post(
                reverse("fuel-route-geojson"),
                {"start": "Los Angeles, CA", "end": "Houston, TX"}, format="json",
            )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["type"], "FeatureCollection")
        self.assertTrue(len(body["features"]) >= 2)  # route line + at least one stop

    def test_main_endpoint_includes_geojson(self):
        canned = (
            {"distance_miles": 123.4, "geometry": "_p~iF~ps|U_ulLnnqC"},
            [(34.05, -118.24), (29.76, -95.36)],
            [{
                "name": "S", "city": "T", "state": "TX",
                "latitude": 31.0, "longitude": -100.0,
                "price": 3.0, "gallons": 50.0, "cost": 150.0,
            }],
            150.0,
        )
        with patch("apps.routing.views.compute_fuel_route", return_value=canned):
            res = self.client.post(
                reverse("fuel-route"),
                {"start": "Los Angeles, CA", "end": "Houston, TX"}, format="json",
            )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("route_geojson", body)
        self.assertIn("total_fuel_cost", body)


class MapViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_map_returns_html(self):
        res = self.client.get(reverse("route-map"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res["Content-Type"])

    def test_map_accepts_query_params(self):
        res = self.client.get(reverse("route-map"), {"start": "Los Angeles, CA", "end": "Houston, TX"})
        self.assertEqual(res.status_code, 200)