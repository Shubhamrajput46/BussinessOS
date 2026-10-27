from django.urls import path

from .views import (
    expense_create,
    expense_delete,
    expense_edit,
    expense_list,
)


urlpatterns = [
    path("", expense_list, name="expense_list"),
    path("add/", expense_create, name="expense_create"),
    path("<int:pk>/edit/", expense_edit, name="expense_edit"),
    path("<int:pk>/delete/", expense_delete, name="expense_delete"),
]