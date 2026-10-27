from django.urls import path

from .views import inventory_list, inventory_transaction_create

urlpatterns = [
    path("", inventory_list, name="inventory_list"),
    path(
        "transaction/add/",
        inventory_transaction_create,
        name="inventory_transaction_create",
    ),
]