from rest_framework import serializers


class FuelRouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()