from rest_framework import serializers


class FuelRouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(help_text="Starting location (address or city)")
    end = serializers.CharField(help_text="Destination location (address or city)")


class FuelStopSerializer(serializers.Serializer):
    station_name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    gallons = serializers.FloatField()
    cost = serializers.FloatField()


class FuelRouteResponseSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()