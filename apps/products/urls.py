from django.urls import path

from .views import product_list,product_create,product_delete,product_edit

urlpatterns = [
    path("", product_list, name="product_list"),
    path("add/", product_create, name="product_create"),
    path("<int:pk>/edit/", product_edit, name="product_edit"),
    path("<int:pk>/delete/", product_delete, name="product_delete"),
]