from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import FuelRouteRequestSerializer
from .services.geocode import geocode_location
from .services.routing import get_route
from .services.geospatial import decode_polyline
from .services.route_processing import compute_cumulative_distances
from .services.fuel_optimizer import select_fuel_stops


class FuelRouteAPIView(APIView):

    def post(self, request):
        serializer = FuelRouteRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        start_str = serializer.validated_data["start"]
        end_str = serializer.validated_data["end"]

        try:
            # 1️⃣ Geocode start/end (2 calls)
            start_coords = geocode_location(start_str)
            end_coords = geocode_location(end_str)

            # 2️⃣ Single routing API call
            route = get_route(start_coords, end_coords)

            # 3️⃣ Decode route
            points = decode_polyline(route["geometry"])
            route_with_distance = compute_cumulative_distances(points)

            # 4️⃣ Fuel optimization
            fuel_stops, total_cost = select_fuel_stops(route_with_distance)

            return Response({
                "distance_miles": route["distance_miles"],
                "fuel_stops": fuel_stops,
                "total_fuel_cost": total_cost,
                # "route_geometry": route["geometry"]
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
