# 🚚 Route Management System

This Django web app manages delivery route planning using workforce data, city distributions, and a VRP (Vehicle Routing Problem) solver powered by Mapbox and PyVRP.

## 🧩 Features

- Upload cities and regions via CSV
- Define workforce and depot information
- Assign distribution packages to cities
- View and generate optimized delivery routes
- Visualize routes on an interactive Mapbox map

## ⚙️ Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following:

```env
MAPBOX_API_KEY=your_mapbox_key
OPENWEATHERMAP_API_KEY=your_openweather_key
```

4. Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

## 📁 Folder Structure

- `management/` — Django app with models, views, forms, and route logic
- `templates/` — HTML templates for frontend
- `static/` — CSS and JS assets
- `vrp_solver.py` — Custom integration with PyVRP and Mapbox

## 📦 Dependencies

- Django
- python-dotenv
- requests
- pyvrp
- numpy

## 🗺️ Mapbox & OpenWeatherMap

This project uses Mapbox for routing and OpenWeatherMap's API to geo-locate cities.

---

Happy Routing!
