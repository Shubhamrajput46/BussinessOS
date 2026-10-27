from django.urls import path

from apps.ai.views import forecast_generate, forecast_list

urlpatterns = [
    path("forecasts/", forecast_list, name="forecast_list"),
    path("forecasts/generate/", forecast_generate, name="forecast_generate"),
]
