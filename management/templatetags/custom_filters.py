from django import template
from management.models import City 

register = template.Library()

@register.filter
def city_name(city_id):
    """Returns the city name for a given city ID."""
    try:
        return City.objects.get(id=city_id).name
    except City.DoesNotExist:
        return "Unknown City"