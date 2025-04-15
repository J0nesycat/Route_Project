import os
import requests
import logging

logger = logging.getLogger(__name__)
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

class Coordinates:

    @staticmethod
    def get_city_coordinates(city_name):
        """Fetch latitude and longitude of a city using OpenWeatherMap Geocoding API."""
        if not OPENWEATHERMAP_API_KEY:
            logger.error("API key is missing. Please insert it in .env")
            return None, None

        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OPENWEATHERMAP_API_KEY}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]["lat"], data[0]["lon"]

        logger.warning(f"No data returned for city: {city_name}")
        return None, None


class LocationSplitter:
    @staticmethod
    def split(locations, max_capacity):
        logger.debug(f"Splitting locations with max capacity: {max_capacity}")
        split = []
        for city, lat, lon, packages in locations:
            while packages > max_capacity:
                split.append((f"{city} (part)", lat, lon, max_capacity))
                packages -= max_capacity
            if packages > 0:
                split.append((city, lat, lon, packages))
        logger.debug(f"Total split locations: {len(split)}")
        return split