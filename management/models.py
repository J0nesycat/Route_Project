from django.db import models
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class Depot(models.Model):
    name = models.TextField(unique=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)

    def __str__(self):
        return self.name


class Summary(models.Model):
    date = models.DateField(unique=True)
    number_of_drivers = models.PositiveIntegerField()
    total_packages = models.PositiveIntegerField()
    avg_packages_per_driver = models.FloatField()
    std_dev_min = models.FloatField()
    std_dev_max = models.FloatField()
    package_distribution = models.TextField()  # ✅ Store formatted package list as text
    depot = models.ForeignKey(Depot, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"Summary for {self.date}"


class RouteSolution(models.Model):
    summary = models.ForeignKey(Summary, on_delete=models.CASCADE, related_name="solutions")
    driver_id = models.IntegerField()
    route = models.TextField()

    def __str__(self):
        return f"Driver {self.driver_id} - {self.summary.date}"


class DailyWorkForce(models.Model):
    date = models.DateField(unique=True)
    number_of_drivers = models.PositiveIntegerField()
    depot = models.ForeignKey('Depot', on_delete=models.CASCADE, null=True)
    summary = models.ForeignKey('Summary', on_delete=models.CASCADE, related_name='workforces', null=True, blank=True)

    def __str__(self):
        return f"{self.date} - {self.number_of_drivers} נהגים"


class DailyDistribution(models.Model):
    session = models.ForeignKey(
        DailyWorkForce,
        on_delete=models.CASCADE,
        related_name="distributions",
        null=True,
    )
    city = models.ForeignKey('City', on_delete=models.CASCADE)
    number_of_packages = models.PositiveIntegerField()

    class Meta:
        # unique_together = ('session', 'city')  # ✅ Consider enforcing if applicable
        pass

    def __str__(self):
        return f"{self.session.date} - {self.city}"


class Polygon(models.Model):
    title = models.TextField(unique=True)
    cities = models.ManyToManyField("City", related_name='edit_city')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('polygon_detail', kwargs={'pk': self.pk})


class City(models.Model):
    name = models.TextField(unique=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    polygon = models.ForeignKey(Polygon, null=True, on_delete=models.CASCADE, related_name="all_cities")

    def __str__(self):
        return self.name