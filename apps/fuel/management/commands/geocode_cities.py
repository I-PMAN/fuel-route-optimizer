import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from apps.fuel.models import CityCoordinate
from geopy.geocoders import Nominatim

class Command(BaseCommand):
    help = "Geocode unique cities"

    def handle(self, *args, **kwargs):
        geolocator = Nominatim(user_agent="fuel_route_planner")

        cities = CityCoordinate.objects.filter(
            latitude__isnull=True,
            longitude__isnull=True
        )

        total = cities.count()
        self.stdout.write(f"Geocoding {total} cities")

        def geocode_city(city_obj):
            query = f"{city_obj.city}, {city_obj.state}, USA"

            try:
                location = geolocator.geocode(query, timeout=10)

                if location:
                    city_obj.latitude = location.latitude
                    city_obj.longitude = location.longitude
                    city_obj.save(update_fields=["latitude", "longitude"])
                    return f"✓ {city_obj.city}, {city_obj.state}"
                else:
                    return f"✗ {city_obj.city}, {city_obj.state}"
            except (GeocoderTimedOut, GeocoderUnavailable):
                time.sleep(random.uniform(1, 3))
                return f"Retry later: {city_obj.city}, {city_obj.state}"

        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(geocode_city, c) for c in cities]

            for i, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                self.stdout.write(f"[{i}/{total}] {result}")
                time.sleep(0.5)
        
        self.stdout.write(self.style.SUCCESS("City geocoding complete"))