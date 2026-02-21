from django.core.management.base import BaseCommand
from apps.fuel.models import FuelStation, CityCoordinate

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        cities = FuelStation.objects.values("city", "state").distinct()

        created = 0

        for c in cities:
            obj, was_created = CityCoordinate.objects.get_or_create(
                city=c["city"],
                state=c["state"]
            )
            if was_created:
                created += 1

    
        self.stdout.write(self.style.SUCCESS(f"Created {created} unique cities"))