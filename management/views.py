import logging
import os
import csv
from datetime import datetime
from django.views.generic import TemplateView, FormView, View
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse

from .forms import CSVUploadForm, DistributionForm, WorkforceForm
from .models import (
    Polygon, Depot, DailyWorkForce, City,
    DailyDistribution, Summary, RouteSolution
)
from .utils import Coordinates, LocationSplitter
from .vrp_solver import VRPSolver

logger = logging.getLogger(__name__)
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")

#Standard deviation
std_dev = 3


class RouteGenerationView(View):
    template_name = "routes.html"

    def get(self, request):
        selected_date = request.GET.get("selected_date")
        error = request.GET.get("error")
        summaries = Summary.objects.order_by("-date")
        context = {
            "summaries": summaries,
            "selected_date": selected_date,
            "mapbox_token": MAPBOX_API_KEY,
        }
        if error:
            context["error"] = "⚠️ לא ניתן היה ליצור מסלולים. נסה שוב."
        return render(request, self.template_name, context)

    def post(self, request):
        selected_date = request.POST.get("summary_date")
        logger.info(f"Received date for route generation: {selected_date}")

        try:
            parsed_date = parse_date(selected_date) or datetime.strptime(selected_date, "%B %d, %Y").date()
            summary = Summary.objects.get(date=parsed_date)
            logger.info(f"Summary found: {summary}")

            RouteSolution.objects.filter(summary=summary).delete()

            raw_locations = [
                (dist.city.name, dist.city.latitude, dist.city.longitude, dist.number_of_packages)
                for dist in DailyDistribution.objects.filter(session__date=summary.date)
            ]

            split_locations = LocationSplitter.split(raw_locations, int(summary.std_dev_max))
            solver = VRPSolver(summary, split_locations)
            optimized_routes = solver.solve_vrp()
            logger.info(f"Optimized routes: {optimized_routes}")

            if not optimized_routes:
                return redirect(f"{reverse('routes')}?error=1")

            depot_name = summary.depot.name
            depot_normalized = depot_name.replace("מרלוג", "").strip(" ()")

            for driver_id, route_cities in enumerate(optimized_routes, start=1):
                route_cities = sorted(route_cities, key=lambda x: depot_normalized in x, reverse=True)
                route_string = " ← ".join(route_cities)
                logger.debug(f"Saving route: Driver {driver_id}, Route: {route_string}")
                try:
                    RouteSolution.objects.create(
                        summary=summary,
                        driver_id=driver_id,
                        route=route_string,
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to save RouteSolution for driver {driver_id}: {e}")

            logger.info("Routes saved successfully.")
            return redirect(f"{reverse('routes')}?selected_date={parsed_date.strftime('%Y-%m-%d')}")

        except Exception as e:
            logger.exception("Route generation failed")
            return redirect(f"{reverse('routes')}?error=1")


class RouteDataView(View):
    def get(self, request):
        selected_date = request.GET.get("date")
        if not selected_date:
            return JsonResponse({"error": "No date provided"}, status=400)

        try:
            parsed_date = parse_date(selected_date) or datetime.strptime(selected_date, "%B %d, %Y").date()
            summary = Summary.objects.get(date=parsed_date)
        except (Summary.DoesNotExist, ValueError):
            return JsonResponse({"routes": [], "error": "No data for selected date"}, status=404)

        depot = summary.depot
        routes = RouteSolution.objects.filter(summary=summary)
        route_data = []

        for route in routes:
            cities = route.route.split(" ← ")
            points = [{"lat": depot.latitude, "lon": depot.longitude, "name": depot.name}]

            for city_name in cities:
                clean_name = city_name.strip().replace(" (part)", "")
                city = City.objects.filter(name__iexact=clean_name).first() or Depot.objects.filter(name__iexact=clean_name).first()

                if city:
                    points.append({"lat": city.latitude, "lon": city.longitude, "name": city.name})
                else:
                    logger.warning(f"City not found: {city_name}")

            route_data.append({"driver": f"נהג {route.driver_id}", "points": points})

        return JsonResponse({"depot": {"lat": depot.latitude, "lon": depot.longitude, "name": depot.name}, "routes": route_data})






class SummaryView(View):
    template_name = "summary.html"

    def get(self, request):
        """Display the summary page after form submission."""
        if 'summary_data' not in request.session:
            return redirect('workforce_entry')  # Redirect if no summary data

        summary_data = request.session.pop('summary_data')  # Remove from session after use
        return render(request, self.template_name, {"summary_data": summary_data})

    @classmethod
    def process_summary_data(cls, request, selected_date):
        try:
            selected_date = parse_date(selected_date)  # Ensure correct date format
            workforce = DailyWorkForce.objects.get(date=selected_date)
            number_of_drivers = workforce.number_of_drivers
            depot = workforce.depot  # <- ✅ get the depot from the workforce

            # Retrieve all distributions for that date
            distributions = DailyDistribution.objects.filter(session=workforce)

            cities_data = []
            package_counts = []

            for distribution in distributions:
                city = distribution.city
                package_count = distribution.number_of_packages
                cities_data.append(
                    f"{city.name} (Lat: {city.latitude}, Long: {city.longitude}, Packages: {package_count})")
                package_counts.append(package_count)

            total_packages = sum(package_counts)
            avg_packages_per_driver = round(total_packages / number_of_drivers, 2) if number_of_drivers else 0
            std_dev_min = round(max(0, avg_packages_per_driver - std_dev), 0)
            std_dev_max = round(avg_packages_per_driver + std_dev, 0)

            package_distribution_text = "\n".join(cities_data)
            package_display_list = [f"{distribution.city.name} - {distribution.number_of_packages} חבילות" for
                                    distribution in distributions]

            # ✅ Save to Summary
            summary, created = Summary.objects.update_or_create(
                date=selected_date,
                defaults={
                    "number_of_drivers": number_of_drivers,
                    "total_packages": total_packages,
                    "avg_packages_per_driver": avg_packages_per_driver,
                    "std_dev_min": std_dev_min,
                    "std_dev_max": std_dev_max,
                    "package_distribution": package_distribution_text,
                    "depot": depot,  # ✅ Save depot in Summary model
                }
            )

            # ✅ Save to session
            request.session["summary_data"] = {
                "date": str(selected_date),
                "number_of_drivers": number_of_drivers,
                "depot": depot.name,  # ✅ Or include full location info if needed
                "package_distribution": package_distribution_text,
                "package_display": package_display_list,
                "total_packages": total_packages,
                "avg_packages_per_driver": avg_packages_per_driver,
                "std_dev_min": std_dev_min,
                "std_dev_max": std_dev_max,
            }

            return redirect("summary")

        except DailyWorkForce.DoesNotExist:
            return redirect("workforce_entry")  # Redirect if no data found


class EditDistributionView(View):
    def post(self, request, city_id):
        if 'distribution_data' in request.session:
            new_amount = request.POST.get('new_amount')
            for entry in request.session['distribution_data']:
                if entry['city_id'] == int(city_id):
                    entry['number_of_packages'] = int(new_amount)
                    break
            request.session.modified = True
        return redirect('add_distribution')


class WorkforceEntryView(FormView):
    template_name = "workforce_entry.html"
    form_class = WorkforceForm

    def form_valid(self, form):
        request = self.request
        date = form.cleaned_data['date']
        number_of_drivers = form.cleaned_data['number_of_drivers']
        depot = form.cleaned_data['depot']


        # Try to get existing or create new
        workforce, created = DailyWorkForce.objects.get_or_create(
            date=date,
            defaults={
                'number_of_drivers': number_of_drivers,
                'depot': depot,

            }
        )
        if created:
            # 🚨 New session – wipe any old city entries
            request.session.pop('distribution_data', None)

        # ❗ If it already existed, update its fields manually
        if not created:
            workforce.number_of_drivers = number_of_drivers
            workforce.depot = depot
            workforce.save()
            messages.info(request, "רשומה לתאריך זה כבר קיימת – בחר תאריך שונה או ערוך רשומה.")
            return redirect(f"{reverse('add_distribution')}?session_id={workforce.id}")
        # ✅ Store depot info in session
        self.request.session['workforce_data'] = {
            'date': str(workforce.date),
            'number_of_drivers': workforce.number_of_drivers,
            'workforce_id': workforce.id,
            'depot_id': depot.id,
            'depot_name': depot.name,
            'depot_lat': depot.latitude,
            'depot_lon': depot.longitude
        }
        self.request.session.modified = True

        return redirect('add_distribution')

class DistributionView(View):
    template_name = "distribution_entry.html"

    def get(self, request):
        session_id = request.GET.get('session_id')

        if session_id:
            try:
                workforce_entry = DailyWorkForce.objects.get(id=session_id)
                request.session['workforce_data'] = {
                    'date': str(workforce_entry.date),
                    'number_of_drivers': workforce_entry.number_of_drivers,
                    'workforce_id': workforce_entry.id,
                    'depot_id': workforce_entry.depot.id,
                    'depot_name': workforce_entry.depot.name,
                    'depot_lat': workforce_entry.depot.latitude,
                    'depot_lon': workforce_entry.depot.longitude,
                }

                # Load cities from DB for this session
                distribution_data = []
                for entry in DailyDistribution.objects.filter(session=workforce_entry):
                    distribution_data.append({
                        'session_id': workforce_entry.id,
                        'city_id': entry.city.id,
                        'city_name': entry.city.name,
                        'number_of_packages': entry.number_of_packages
                    })

                request.session['distribution_data'] = distribution_data
                request.session.modified = True

            except DailyWorkForce.DoesNotExist:
                messages.error(request, "⚠️ לא נמצא מידע עבור הסשן שנבחר.")
                return redirect('workforce_entry')

        if 'workforce_data' not in request.session:
            return redirect('workforce_entry')

        session_data = request.session['workforce_data']
        workforce_entry = DailyWorkForce.objects.get(id=session_data['workforce_id'])

        form = DistributionForm(initial={'session': workforce_entry})
        cities = request.session.get('distribution_data', [])

        return render(request, self.template_name, {
            'session_data': session_data,
            'form': form,
            'cities': cities,
            'all_sessions': DailyWorkForce.objects.all().order_by('-date')
        })

    def post(self, request):
        """Handles form submission: Save cities or redirect to summary."""
        if 'save_edits' in request.POST:
            for i, entry in enumerate(request.session.get('distribution_data', [])):
                package_key = f'packages_{i}'
                if package_key in request.POST:
                    try:
                        new_value = int(request.POST[package_key])
                        request.session['distribution_data'][i]['number_of_packages'] = new_value
                    except ValueError:
                        pass  # Optionally flash a message
            request.session.modified = True
            messages.success(request, "✅ הנתונים נשמרו בהצלחה!")
            return redirect('add_distribution')

        if 'workforce_data' not in request.session:
            return redirect('workforce_entry')

        session_data = request.session['workforce_data']
        workforce_entry = DailyWorkForce.objects.get(id=session_data['workforce_id'])
        if 'delete' in request.POST:
            delete_index = int(request.POST.get('delete'))
            if 'distribution_data' in request.session:
                try:
                    del request.session['distribution_data'][delete_index]
                    request.session.modified = True
                    messages.success(request, "✅ העיר הוסרה מהרשימה.")
                except IndexError:
                    messages.error(request, "❌ לא ניתן למחוק את העיר.")
            return redirect('add_distribution')

        # 🛑 If "send" was clicked, SKIP form validation and save directly to DB
        if 'send' in request.POST:
            total_packages = 0
            city_data = []

            for entry in request.session.get('distribution_data', []):
                city_obj = City.objects.get(id=entry['city_id'])

                DailyDistribution.objects.update_or_create(
                    session=workforce_entry,
                    city=city_obj,
                    defaults={'number_of_packages': entry['number_of_packages']}
                )

                city_data.append(f"{city_obj.name} - {entry['number_of_packages']}")
                total_packages += entry['number_of_packages']

            avg_packages = total_packages / workforce_entry.number_of_drivers if workforce_entry.number_of_drivers > 0 else 0

            request.session['summary_data'] = {
                'date': str(workforce_entry.date),
                'number_of_drivers': workforce_entry.number_of_drivers,
                'city_data': city_data,
                'total_packages': total_packages,
                'avg_packages_per_driver': round(avg_packages, 2),
            }

            del request.session['workforce_data']
            del request.session['distribution_data']

            return redirect('process_summary', selected_date=str(workforce_entry.date))

        # ✅ Only validate form for "save" button
        form = DistributionForm(request.POST)
        if form.is_valid():
            if 'distribution_data' not in request.session:
                request.session['distribution_data'] = []

            existing_entries = request.session['distribution_data']
            new_city_id = form.cleaned_data['city'].id

            if any(entry['city_id'] == new_city_id for entry in existing_entries):
                messages.warning(request, f"העיר {form.cleaned_data['city'].name} כבר נוספה לרשימה.")
            else:
                existing_entries.append({
                    'session_id': workforce_entry.id,
                    'city_id': new_city_id,
                    'city_name': form.cleaned_data['city'].name,
                    'number_of_packages': form.cleaned_data['number_of_packages']
                })
                request.session.modified = True
                messages.success(request, f"העיר {form.cleaned_data['city'].name} נוספה בהצלחה.")

            return redirect('add_distribution')

        return self.get(request)  # Reload page on errors



class HomePageView(TemplateView):
    template_name = "home.html"




class CSVUploadView(View):
    template_name = "upload_csv.html"

    def get(self, request):
        form = CSVUploadForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]

            # Read CSV file
            decoded_file = csv_file.read().decode("utf-8").splitlines()
            reader = csv.reader(decoded_file)

            headers = next(reader)  # Extract headers (First row)

            polygons = {}  # Store polygons to avoid duplicate queries

            for row in reader:
                for i, city_name in enumerate(row):
                    city_name = city_name.strip()
                    if not city_name:  # Skip empty values
                        continue

                    polygon_title = headers[i]  # Column header is the polygon title

                    if polygon_title not in polygons:
                        polygon, _ = Polygon.objects.get_or_create(title=polygon_title)
                        polygons[polygon_title] = polygon
                    else:
                        polygon = polygons[polygon_title]

                    # Check if city exists
                    existing_city = City.objects.filter(name=city_name).first()

                    if existing_city:
                        # Update existing city with new polygon and coordinates if needed
                        if existing_city.polygon != polygon:
                            print(f"Updating city '{city_name}' to new polygon '{polygon_title}'")
                            existing_city.polygon = polygon

                        # Get new coordinates
                        latitude, longitude = Coordinates.get_city_coordinates(city_name)

                        # Update only if new coordinates are valid
                        if latitude and longitude:
                            existing_city.latitude = latitude
                            existing_city.longitude = longitude

                        existing_city.save()  # Save updates

                        # CHANGE: Update the many-to-many field by adding the existing city to the polygon.
                        polygon.cities.add(existing_city)
                    else:
                        # New city, get coordinates and insert it
                        latitude, longitude = Coordinates.get_city_coordinates(city_name)
                        new_city = City.objects.create(
                            name=city_name,
                            latitude=latitude,
                            longitude=longitude,
                            polygon=polygon
                        )
                        # CHANGE: Add the newly created city to the polygon's many-to-many field.
                        polygon.cities.add(new_city)

            return render(request, self.template_name, {
                "form": form,
                "success": "CSV data uploaded successfully and updated existing records!"
            })

        return render(request, self.template_name, {"form": form, "error": "Invalid file format"})







