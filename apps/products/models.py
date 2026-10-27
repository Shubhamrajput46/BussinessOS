from django.db import models
from apps.organizations.models import Organisation


class Product(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="products",
    )

    name = models.CharField(max_length=150)

    sku = models.CharField(max_length=50)

    description = models.TextField(blank=True)

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    stock_quantity = models.PositiveIntegerField(default=0)

    low_stock_threshold = models.PositiveIntegerField(default=5)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "sku"],
                name="unique_product_sku_per_organisation",
            )
        ]

    def __str__(self):
        return self.name