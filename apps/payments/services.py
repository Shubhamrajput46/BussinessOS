from decimal import Decimal

from django.db.models import Sum

from .models import Payment


def paid_total(order):
    return (
        Payment.objects.filter(order=order, status=Payment.Status.PAID)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


def sync_invoice_status(order):
    """Mark the order's invoice as PAID once fully paid (and back to ISSUED if not)."""
    invoice = getattr(order, "invoice", None)
    if invoice is None or invoice.status in ("CANCELLED", "DRAFT"):
        return
    fully_paid = order.total_amount > 0 and paid_total(order) >= order.total_amount
    new_status = "PAID" if fully_paid else "ISSUED"
    if invoice.status != new_status:
        invoice.status = new_status
        invoice.save(update_fields=["status", "updated_at"])
