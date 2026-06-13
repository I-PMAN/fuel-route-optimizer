from django.urls import path
from .views import FuelRouteAPIView, FuelRouteGeoJSONView, RouteMapView

urlpatterns = [
    path("fuel-route/", FuelRouteAPIView.as_view(), name="fuel-route"),
    path("fuel-route/geojson/", FuelRouteGeoJSONView.as_view(), name="fuel-route-geojson"),
    path("map/", RouteMapView.as_view(), name="route-map"),
]