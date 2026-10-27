from django.db import models

from apps.organizations.models import Organisation


class SalesForecast(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="sales_forecasts",
    )

    forecast_date = models.DateField()

    predicted_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["forecast_date"]
        indexes = [
            models.Index(
                fields=["organisation", "forecast_date"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.organisation.name} - "
            f"{self.forecast_date}"
        )