from django.contrib import admin
from .models import Organisation


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "phone",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
    )

    list_filter = (
        "is_active",
        "created_at",
    )