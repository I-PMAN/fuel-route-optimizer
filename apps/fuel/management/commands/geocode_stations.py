import requests
import time
import random
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.fuel.models import FuelStation


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class Command(BaseCommand):
    help = "Geocode fuel stations using Nominatim"

    def handle(self, *args, **kwargs):

        stations = FuelStation.objects.filter(
            Q(latitude__isnull=True) | Q(longitude__isnull=True)
        )

        total = stations.count()
        self.stdout.write(f"Geocoding {total} stations")

        headers = {
            "User-Agent": "fuel-route-planner-assessment"
        }

        for i, station in enumerate(stations, start=1):

            queries = [
                f"{station.address}, {station.city}, {station.state}, USA",
                f"{station.city}, {station.state}, USA"
            ]

            success = False

            for query in queries:
                try:
                    response = requests.get(
                        NOMINATIM_URL,
                        headers=headers,
                        params={
                            "q": query,
                            "format": "json",
                            "limit": 1
                        },
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            station.latitude = float(data[0]["lat"])
                            station.longitude = float(data[0]["lon"])
                            station.save(update_fields=["latitude", "longitude"])
                            success = True
                            break

                except Exception:
                    continue

            if success:
                self.stdout.write(f"[{i}/{total}] ✓ {station.name}")
            else:
                self.stdout.write(f"[{i}/{total}] ✗ {station.name}")

            # Respect Nominatim rate limit
            time.sleep(random.uniform(0.8, 1.2))

        self.stdout.write(self.style.SUCCESS("Geocoding complete"))