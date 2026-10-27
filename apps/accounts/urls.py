from django.urls import path

from .views import (
    home,
    profile_view,
    user_create,
    user_delete,
    user_edit,
    user_list,
    user_toggle_status,
)

urlpatterns = [
    path("", home, name="home"),
    path("profile/", profile_view, name="profile"),
    path("users/", user_list, name="user_list"),
    path("users/create/", user_create, name="user_create"),
    path("users/<int:pk>/edit/", user_edit, name="user_edit"),
    path("users/<int:pk>/toggle-status/", user_toggle_status, name="user_toggle_status"),
    path("users/<int:pk>/delete/", user_delete, name="user_delete"),
]
