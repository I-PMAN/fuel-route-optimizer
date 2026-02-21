import csv
from django.core.management.base import BaseCommand
from apps.fuel.models import FuelStation
from django.db import transaction

class Command(BaseCommand):
    help = "Import fuel prices from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    @transaction.atomic
    def handle(self, *args, **kwargs):
        csv_path = kwargs["csv_path"]

        self.stdout.write("Clearing existing fuel stations...")
        FuelStation.objects.all().delete()

        stations = []
        seen = set()

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                opis_id = row["OPIS Truckstop ID"].strip()
                name = row["Truckstop Name"].strip()
                address = row["Address"].strip()
                city = row["City"].strip()
                state = row["State"].strip()
                price = float(row["Retail Price"])

                #Deduplication key
                unique_key = (opis_id, price, city, state)

                if unique_key in seen:
                    continue

                seen.add(unique_key)

                stations.append(
                    FuelStation(
                        opis_id=opis_id,
                        name=name,
                        address=address,
                        city=city,
                        state=state,
                        price=price,
                    )
                )

        FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(stations)} fuel stations.")
        )

