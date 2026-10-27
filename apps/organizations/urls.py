from django.urls import path

from .views import organisation_settings

urlpatterns = [
    path("settings/", organisation_settings, name="organisation_settings"),
]
