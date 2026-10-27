from django.urls import path

from .views import (
    order_create,
    order_detail,
    order_edit,
    order_list,
    order_update_status,
)


urlpatterns = [
    path("", order_list, name="order_list"),
    path("add/", order_create, name="order_create"),
    path("<int:pk>/", order_detail, name="order_detail"),
    path("<int:pk>/edit/", order_edit, name="order_edit"),
    path(
        "<int:pk>/status/",
        order_update_status,
        name="order_update_status",
    ),
]