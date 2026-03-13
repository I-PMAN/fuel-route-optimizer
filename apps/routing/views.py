from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import FuelRouteRequestSerializer, FuelRouteResponseSerializer
from .services.geocode import geocode_location
from .services.routing import get_route
from .services.geospatial import decode_polyline
from .services.route_processing import compute_cumulative_distances
from .services.fuel_optimizer import select_fuel_stops
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiExample

import logging

logger = logging.getLogger(__name__)

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
        OpenApiExample(
            "Response Example",
            value={
                "distance_miles": 1546.04,
                "no_of_stops": 3,
                "fuel_stops": [
                    {
                    "name": "QUIKTRIP #1499",
                    "city": "Tucson",
                    "state": "AZ",
                    "price": 3.06233333,
                    "gallons": 48.48,
                    "cost": 148.46
                    },
                    {
                    "name": "PLATEAU TRUCK AND AUTO CENTER",
                    "city": "Van Horn",
                    "state": "TX",
                    "price": 3.099,
                    "gallons": 43.72,
                    "cost": 135.48
                    },
                    {
                    "name": "CIRCLE K #2741545",
                    "city": "Cuero",
                    "state": "TX",
                    "price": 3.099,
                    "gallons": 49.96,
                    "cost": 154.82
                    }
                ],
                "total_fuel_cost": 438.77
            },
            response_only=True,
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
            # 1️⃣ Geocode start/end (2 calls)
            start_coords = geocode_location(start_str)
            end_coords = geocode_location(end_str)

            # 2️⃣ Single routing API call
            route = get_route(start_coords, end_coords)
            logger.info(route)

            # 3️⃣ Decode route
            points = decode_polyline(route["geometry"])
            route_with_distance = compute_cumulative_distances(points)
            logger.info(f"Route with distance: {route_with_distance}")
            # 4️⃣ Fuel optimization
            fuel_stops, total_cost = select_fuel_stops(route_with_distance)
            logger.info(f"Fuel stops: {fuel_stops}, Total cost: {total_cost}")
            
            return Response({
                "distance_miles": route["distance_miles"],
                "no_of_stops": len(fuel_stops),
                "fuel_stops": fuel_stops,
                "total_fuel_cost": total_cost,
                # "route_geometry": route["geometry"]
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
