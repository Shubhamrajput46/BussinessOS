from django.urls import path

from .views import (
    notification_delete,
    notification_detail,
    notification_list,
    notification_mark_all_read,
    notification_mark_read,
)


urlpatterns = [
    path("", notification_list, name="notification_list"),

    path(
        "<int:pk>/",
        notification_detail,
        name="notification_detail",
    ),

    path(
        "<int:pk>/read/",
        notification_mark_read,
        name="notification_mark_read",
    ),

    path(
        "mark-all-read/",
        notification_mark_all_read,
        name="notification_mark_all_read",
    ),

    path(
        "<int:pk>/delete/",
        notification_delete,
        name="notification_delete",
    ),
]