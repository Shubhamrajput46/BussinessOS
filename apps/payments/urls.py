from django.urls import path

from .views import (
    payment_create,
    payment_delete,
    payment_edit,
    payment_list,
)


urlpatterns = [
    path("", payment_list, name="payment_list"),

    path(
        "add/",
        payment_create,
        name="payment_create",
    ),

    path(
        "<int:pk>/edit/",
        payment_edit,
        name="payment_edit",
    ),

    path(
        "<int:pk>/delete/",
        payment_delete,
        name="payment_delete",
    ),
]