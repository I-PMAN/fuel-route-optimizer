from rest_framework import serializers


class FuelRouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(help_text="Starting location (address or city), e.g. 'Los Angeles, CA'")
    end = serializers.CharField(help_text="Destination location (address or city), e.g. 'Houston, TX'")


class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Fuel station name")
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    price = serializers.FloatField(help_text="Price per gallon (USD)")
    gallons = serializers.FloatField(help_text="Gallons purchased at this stop")
    cost = serializers.FloatField(help_text="Cost of fuel purchased at this stop (USD)")


class FuelRouteResponseSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    no_of_stops = serializers.IntegerField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField(help_text="Total fuel cost for the trip (USD)")
    route_geometry = serializers.CharField(help_text="Encoded polyline of the route")
    route_geojson = serializers.JSONField(help_text="GeoJSON FeatureCollection: route line + fuel stop markers")