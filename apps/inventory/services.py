from django.db import transaction

from apps.notifications.models import Notification
from apps.products.models import Product

from .models import InventoryTransaction

T = InventoryTransaction.TransactionType


class StockError(ValueError):
    """Raised when a stock movement is not allowed."""


@transaction.atomic
def apply_transaction(*, organisation, product, transaction_type, quantity, note="", user=None):
    """Apply a stock movement to a product and record it in the ledger.

    STOCK_IN adds, STOCK_OUT subtracts and ADJUSTMENT sets the stock to
    the given quantity. A low-stock notification is raised when the stock
    crosses the product's threshold.
    """
    if transaction_type not in T.values:
        raise StockError("Invalid transaction type.")
    if quantity is None or quantity <= 0:
        raise StockError("Quantity must be greater than 0.")

    product = Product.objects.select_for_update().get(pk=product.pk, organisation=organisation)
    old_stock = product.stock_quantity

    if transaction_type == T.STOCK_IN:
        product.stock_quantity += quantity
    elif transaction_type == T.STOCK_OUT:
        if quantity > product.stock_quantity:
            raise StockError("Not enough stock available.")
        product.stock_quantity -= quantity
    else:
        product.stock_quantity = quantity

    product.save(update_fields=["stock_quantity", "updated_at"])

    entry = InventoryTransaction.objects.create(
        organisation=organisation,
        product=product,
        transaction_type=transaction_type,
        quantity=quantity,
        note=note,
    )

    if (
        user is not None
        and old_stock > product.low_stock_threshold
        and product.stock_quantity <= product.low_stock_threshold
    ):
        Notification.objects.create(
            organisation=organisation,
            user=user,
            title="Low Stock Alert",
            message=(
                f"Product {product.name} is running low on stock. "
                f"Current stock: {product.stock_quantity}. "
                f"Low stock threshold: {product.low_stock_threshold}."
            ),
            notification_type=Notification.NotificationType.WARNING,
        )

    return entry
