from django.contrib import admin
from .models import Product

# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=(
        "name",
        "sku",
        "organisation",
        "cost_price",
        "selling_price",
        "stock_quantity",
        "is_active",
        "created_at",
    )

    search_fields=(
        "name",
        "sku",
    )

    list_filter=(
       "organisation",
        "is_active", 
    )