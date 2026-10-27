from django.urls import path

from .views import (
    invoice_create,
    invoice_delete,
    invoice_detail,
    invoice_edit,
    invoice_list,
)


urlpatterns = [
    path("", invoice_list, name="invoice_list"),

    path(
        "add/",
        invoice_create,
        name="invoice_create",
    ),

    path(
        "<int:pk>/",
        invoice_detail,
        name="invoice_detail",
    ),

    path(
        "<int:pk>/edit/",
        invoice_edit,
        name="invoice_edit",
    ),

    path(
        "<int:pk>/delete/",
        invoice_delete,
        name="invoice_delete",
    ),
]