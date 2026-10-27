from django.urls import path

from .views import (
    customer_create,
    customer_delete,
    customer_edit,
    customer_list,
)

urlpatterns = [
    path("", customer_list, name="customer_list"),
    path("add/", customer_create, name="customer_create"),
    path("<int:pk>/edit/", customer_edit, name="customer_edit"),
    path("<int:pk>/delete/", customer_delete, name="customer_delete"),
]