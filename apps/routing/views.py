from django.shortcuts import render
from django.views import View
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import FuelRouteRequestSerializer, FuelRouteResponseSerializer
from .services.geocode import geocode_location
from .services.routing import get_route
from .services.geospatial import decode_polyline
from .services.route_processing import compute_cumulative_distances
from .services.fuel_optimizer import select_fuel_stops
from .services.geojson_builder import build_route_geojson
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.types import OpenApiTypes

import logging

logger = logging.getLogger(__name__)


def compute_fuel_route(start_str, end_str):
    """
    Shared pipeline: geocode -> single routing call -> decode -> optimize.
    Returns (route, points, fuel_stops, total_cost) so callers can shape
    their own response. Used by both the full JSON endpoint and the
    GeoJSON-only endpoint, so the routing API is still only called once
    per request in either case.
    """
    # Geocode start/end (2 geocoder calls).
    start_coords = geocode_location(start_str)
    end_coords = geocode_location(end_str)

    # Single routing API call.
    route = get_route(start_coords, end_coords)

    # Decode geometry and compute cumulative distances.
    points = decode_polyline(route["geometry"])
    route_with_distance = compute_cumulative_distances(points)

    # Cost-minimizing fuel optimization.
    fuel_stops, total_cost = select_fuel_stops(route_with_distance)

    return route, points, fuel_stops, total_cost


class FuelRouteAPIView(APIView):

    @extend_schema(
        request=FuelRouteRequestSerializer,
        responses={200: FuelRouteResponseSerializer},
        description="Compute optimal fuel stops between two locations.",
        examples=[
            OpenApiExample(
                "Request Example",
                value={
                    "start": "Los Angeles, CA",
                    "end": "Houston, TX"
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = FuelRouteRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        start_str = serializer.validated_data["start"]
        end_str = serializer.validated_data["end"]

        try:
            route, points, fuel_stops, total_cost = compute_fuel_route(
                start_str, end_str
            )
            route_geojson = build_route_geojson(points, fuel_stops)

            return Response({
                "distance_miles": route["distance_miles"],
                "no_of_stops": len(fuel_stops),
                "fuel_stops": fuel_stops,
                "total_fuel_cost": total_cost,
                "route_geometry": route["geometry"],
                "route_geojson": route_geojson,
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FuelRouteGeoJSONView(APIView):
    """
    Returns ONLY a GeoJSON FeatureCollection as the entire response body.
    This means the whole Postman response can be copied as-is and pasted
    straight into geojson.io (or any GeoJSON viewer) with no trimming.
    """

    @extend_schema(
        request=FuelRouteRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
        description="Return the route and fuel stops as a GeoJSON FeatureCollection.",
    )
    def post(self, request):
        serializer = FuelRouteRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        start_str = serializer.validated_data["start"]
        end_str = serializer.validated_data["end"]

        try:
            route, points, fuel_stops, total_cost = compute_fuel_route(
                start_str, end_str
            )
            route_geojson = build_route_geojson(points, fuel_stops)

            # The FeatureCollection IS the whole body.
            return Response(route_geojson, content_type="application/geo+json")

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
MAP_PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Fuel Route Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; }
    #bar { padding: 10px; background: #f4f4f4; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    #bar input { padding: 6px 8px; }
    #bar button { padding: 6px 14px; cursor: pointer; }
    #map { height: calc(100vh - 110px); }
    #summary { padding: 8px 10px; font-size: 14px; background: #fafafa; }
    .err { color: #b00; }
  </style>
</head>
<body>
  <div id="bar">
    <input id="start" placeholder="Start (e.g. Los Angeles, CA)" size="28" />
    <input id="end" placeholder="End (e.g. Houston, TX)" size="28" />
    <button onclick="load()">Show route</button>
  </div>
  <div id="summary"></div>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([39.5, -98.35], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
    }).addTo(map);
    let layer = null;

    const q = new URLSearchParams(location.search);
    if (q.get('start')) document.getElementById('start').value = q.get('start');
    if (q.get('end')) document.getElementById('end').value = q.get('end');

    async function load() {
      const start = document.getElementById('start').value.trim();
      const end = document.getElementById('end').value.trim();
      const summary = document.getElementById('summary');
      if (!start || !end) { summary.innerHTML = '<span class="err">Enter both a start and an end.</span>'; return; }
      summary.textContent = 'Loading route...';
      try {
        const res = await fetch('/api/fuel-route/geojson/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ start, end })
        });
        const data = await res.json();
        if (!res.ok) { summary.innerHTML = '<span class="err">' + (data.error || 'Request failed') + '</span>'; return; }

        if (layer) map.removeLayer(layer);
        let stops = 0;
        layer = L.geoJSON(data, {
          style: { color: '#1d4ed8', weight: 4 },
          pointToLayer: (feat, latlng) => {
            stops++;
            const p = feat.properties;
            return L.circleMarker(latlng, { radius: 7, color: '#fff', weight: 2, fillColor: '#dc2626', fillOpacity: 1 })
              .bindPopup('<b>Stop ' + p.stop_number + ': ' + p.name + '</b><br>' +
                         p.city + ', ' + p.state + '<br>$' + p.price + '/gal &middot; ' +
                         p.gallons + ' gal &middot; $' + p.cost);
          }
        }).addTo(map);
        map.fitBounds(layer.getBounds(), { padding: [30, 30] });
        summary.textContent = stops + ' fuel stop(s). Click a pin for price details.';
      } catch (e) {
        summary.innerHTML = '<span class="err">Could not load route: ' + e + '</span>';
      }
    }
    if (q.get('start') && q.get('end')) load();
  </script>
</body>
</html>"""


class RouteMapView(View):
    def get(self, request):
        return HttpResponse(MAP_PAGE, content_type="text/html")