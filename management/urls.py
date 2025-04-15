from django.urls import path
from .views import HomePageView
from .views import CSVUploadView,DistributionView,WorkforceEntryView,SummaryView,EditDistributionView,RouteGenerationView,RouteDataView

urlpatterns = [

    path('', HomePageView.as_view(), name='home'),
    path('routes/', RouteGenerationView.as_view(), name='routes'),
    path('upload-csv/', CSVUploadView.as_view(), name="upload_csv"),
    path('add_distribution/', DistributionView.as_view(), name='add_distribution'),
    path('workforce_entry/', WorkforceEntryView.as_view(), name='workforce_entry'),
    path('summary/', SummaryView.as_view(), name='summary'),
    path('process_summary/<str:selected_date>/', SummaryView.process_summary_data, name='process_summary'),
    path('edit_distribution/<int:city_id>/', EditDistributionView.as_view(), name='edit_distribution'),
    path("generate_routes/", RouteGenerationView.as_view(), name="generate_routes"),
    path("route_data/", RouteDataView.as_view(), name="route_data"),
]
