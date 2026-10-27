from django.db import models

from apps.organizations.models import Organisation
from apps.orders.models import Order


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="invoice",
    )

    invoice_number = models.CharField(max_length=50)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    issue_date = models.DateField(auto_now_add=True)

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "invoice_number"],
                name="unique_invoice_number_per_organisation",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = (
                Invoice.objects
                .filter(organisation=self.organisation)
                .order_by("-id")
                .first()
            )

            if last_invoice:
                last_number = int(
                    last_invoice.invoice_number.split("-")[1]
                )
                next_number = last_number + 1
            else:
                next_number = 1

            self.invoice_number = f"INV-{next_number:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number 