import os
import requests
import numpy as np
import logging
from dotenv import load_dotenv
from pyvrp import Model
from pyvrp.stop import MaxRuntime

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")


class VRPSolver:
    """
    Class to handle the VRP (Vehicle Routing Problem) processing using PyVRP.
    """
    def __init__(self, summary, locations):
        self.summary = summary
        self.LOCATIONS = locations
        self.START_LOCATION = (summary.depot.latitude, summary.depot.longitude)
        self.number_of_drivers = summary.number_of_drivers
        self.max_capacity = int(summary.std_dev_max)

    def _get_distance_matrix(self):
        """
        Fetches the driving distance matrix from Mapbox API.
        """
        logger.info("Fetching distance matrix from Mapbox API...")
        all_points = [self.START_LOCATION] + [(lat, lon) for _, lat, lon, _ in self.LOCATIONS]
        coords = ";".join([f"{lon},{lat}" for lat, lon in all_points])
        url = (
            f"https://api.mapbox.com/directions-matrix/v1/mapbox/driving/"
            f"{coords}?annotations=distance&access_token={MAPBOX_API_KEY}"
        )

        response = requests.get(url)
        data = response.json()

        if "distances" not in data:
            logger.error(f"Error fetching distance matrix: {data}")
            return None

        matrix = np.array(data["distances"], dtype=np.float64) / 1000
        logger.info("Distance matrix fetched and converted to kilometers.")
        return matrix.astype(np.int64)

    def solve_vrp(self):
        """
        Solves the VRP problem using PyVRP and returns city lists for each route.
        """
        logger.info("Running VRP Solver...")
        distance_matrix = self._get_distance_matrix()

        if distance_matrix is None:
            logger.warning("Distance matrix is None. Aborting VRP solution.")
            return []

        logger.info(f"Using vehicle capacity: {self.max_capacity}")

        m = Model()
        depot = m.add_depot(
            x=int(self.START_LOCATION[1] * 100000),
            y=int(self.START_LOCATION[0] * 100000)
        )

        m.add_vehicle_type(
            self.number_of_drivers,
            capacity=self.max_capacity,
            start_depot=depot,
            end_depot=None
        )

        clients = []
        city_map = {}

        for idx, (city, lat, lon, packages) in enumerate(self.LOCATIONS):
            client = m.add_client(
                x=int(lon * 100000),
                y=int(lat * 100000),
                delivery=packages
            )
            clients.append(client)
            city_map[idx + 1] = city

        locations = [depot] + clients
        for frm_idx, frm in enumerate(locations):
            for to_idx, to in enumerate(locations):
                if frm_idx != to_idx:
                    distance = distance_matrix[frm_idx, to_idx]
                    m.add_edge(frm, to, distance=int(distance))

        logger.info("Solving VRP with MaxRuntime(30)...")
        solution = m.solve(stop=MaxRuntime(30), display=True)

        if solution is None or not solution.best:
            logger.warning("No feasible solution found.")
            return []

        route_cities_list = []

        for route in solution.best.routes():
            route_nodes = [node for node in route]
            route_cities = [city_map.get(int(node), f"Unknown({node})") for node in route_nodes]
            route_cities_list.append(route_cities)

        logger.info(f"VRP solved. {len(route_cities_list)} routes generated.")
        return route_cities_list