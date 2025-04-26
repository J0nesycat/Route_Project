from django.test import TestCase, Client
from django.urls import reverse
from .models import  Depot,  DailyWorkForce

from django.core.files.uploadedfile import SimpleUploadedFile
import os
import django
from unittest.mock import patch, MagicMock
from management.vrp_solver import VRPSolver
from types import SimpleNamespace
import pytest
from unittest.mock import patch
from management.utils import Coordinates, LocationSplitter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_routes.settings")  # replace with your actual project name
django.setup()


class HomePageViewTest(TestCase):
    def test_homepage_view(self):
        client = Client()
        response = client.get(reverse('home'))  # Ensure 'home' is defined in your urls.py
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')


class WorkforceEntryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.depot = Depot.objects.create(name="מרלוג ראשי", latitude=32.0853, longitude=34.7818)

    def test_create_workforce(self):
        response = self.client.post(reverse('workforce_entry'), {
            'date': '2025-04-20',
            'number_of_drivers': 3,
            'depot': self.depot.id
        })
        self.assertEqual(response.status_code, 302)  # should redirect to 'add_distribution'
        self.assertTrue(DailyWorkForce.objects.filter(date='2025-04-20').exists())


class CSVUploadTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_csv_upload(self):
        test_file = SimpleUploadedFile(
            "cities.csv",
            b"Polygon1,Polygon2\nTel Aviv,Haifa",
            content_type="text/csv"
        )
        response = self.client.post(reverse('upload_csv'), {'file': test_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSV data uploaded successfully")

@pytest.fixture
def sample_summary():
    return SimpleNamespace(
        depot=SimpleNamespace(latitude=32.0853, longitude=34.7818, name="מרלוג"),
        number_of_drivers=2,
        std_dev_max=10
    )

@pytest.fixture
def sample_locations():
    return [
        ("CityA", 32.1, 34.8, 3),
        ("CityB", 32.2, 34.7, 4),
        ("CityC", 32.0, 34.9, 2),
    ]
@patch("management.vrp_solver.requests.get")
@patch("management.vrp_solver.Model")


def test_solve_vrp_returns_routes(mock_model, mock_get, sample_summary, sample_locations):
    # Mock Mapbox response
    mock_get.return_value.json.return_value = {
        "distances": [
            [0, 10, 20, 30],
            [10, 0, 15, 25],
            [20, 15, 0, 12],
            [30, 25, 12, 0],
        ]
    }

    # Mock VRP Model and solution
    mock_solution = MagicMock()
    mock_solution.best.routes.return_value = [
        [1, 2],  # indexes will map to city names
        [3]
    ]

    mock_model_instance = MagicMock()
    mock_model_instance.solve.return_value = mock_solution
    mock_model.return_value = mock_model_instance

    solver = VRPSolver(sample_summary, sample_locations)
    routes = solver.solve_vrp()

    assert len(routes) == 2
    assert "CityA" in routes[0] or "CityB" in routes[0]
    assert "CityC" in routes[1]


@patch("management.utils.requests.get")
def test_get_city_coordinates_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"lat": 32.0853, "lon": 34.7818}]

    lat, lon = Coordinates.get_city_coordinates("Tel Aviv")

    assert lat == 32.0853
    assert lon == 34.7818


@patch("management.utils.requests.get")
def test_get_city_coordinates_no_data(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []

    lat, lon = Coordinates.get_city_coordinates("InvalidCity")
    assert lat is None and lon is None


@patch("management.utils.requests.get")
def test_get_city_coordinates_api_error(mock_get):
    mock_get.return_value.status_code = 404

    lat, lon = Coordinates.get_city_coordinates("Paris")
    assert lat is None and lon is None


# -------------------------------
# ✅ Test LocationSplitter class
# -------------------------------

def test_location_splitter_basic_split():
    locations = [
        ("CityA", 32.1, 34.8, 7),  # requires splitting
        ("CityB", 32.2, 34.7, 3),  # no split needed
    ]
    result = LocationSplitter.split(locations, max_capacity=4)

    assert len(result) == 3
    assert result[0] == ("CityA (part)", 32.1, 34.8, 4)
    assert result[1] == ("CityA", 32.1, 34.8, 3)
    assert result[2] == ("CityB", 32.2, 34.7, 3)