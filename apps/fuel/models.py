from django.db import models


class FuelStation(models.Model):
    opis_id = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    price = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "state"]),
            models.Index(fields=["price"]),
        ]
        # unique_together = ("city", "state")

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"


class CityCoordinate(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("city", "state")

    def __str__(self):
        return f"{self.city}, {self.state}"