from collections import OrderedDict
from decimal import Decimal

from django.db import transaction

from apps.inventory.models import InventoryTransaction
from apps.notifications.models import Notification
from apps.products.models import Product

from .models import Order, OrderItem

STOCK = InventoryTransaction.TransactionType


class OrderError(ValueError):
    """Raised for any rule violation while creating/updating an order."""


def _merge_items(items):
    """[(product_id, qty), ...] -> OrderedDict(product_id -> qty), duplicates summed."""
    merged = OrderedDict()
    for product_id, quantity in items:
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise OrderError("Invalid product or quantity.")
        if quantity <= 0:
            raise OrderError("Quantity must be greater than 0.")
        merged[product_id] = merged.get(product_id, 0) + quantity
    if not merged:
        raise OrderError("Please select at least one product.")
    return merged


def _notify(organisation, user, title, message, kind):
    if user is not None:
        Notification.objects.create(
            organisation=organisation,
            user=user,
            title=title,
            message=message,
            notification_type=kind,
        )


def _write_items(order, merged, *, available_bonus=None, note_prefix="Stock out for order"):
    """Validate stock, create OrderItems + STOCK_OUT ledger rows, return subtotal."""
    available_bonus = available_bonus or {}
    products = {
        p.id: p
        for p in Product.objects.select_for_update().filter(
            id__in=merged.keys(), organisation=order.organisation, is_active=True
        )
    }
    subtotal = Decimal("0.00")

    for product_id, quantity in merged.items():
        product = products.get(product_id)
        if product is None:
            raise OrderError("One of the selected products is not available.")
        if quantity > product.stock_quantity + available_bonus.get(product_id, 0):
            raise OrderError(f"Not enough stock for {product.name}.")

    for product_id, quantity in merged.items():
        product = products[product_id]
        total_price = product.selling_price * quantity
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.selling_price,
            total_price=total_price,
        )
        product.stock_quantity -= quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
        InventoryTransaction.objects.create(
            organisation=order.organisation,
            product=product,
            transaction_type=STOCK.STOCK_OUT,
            quantity=quantity,
            note=f"{note_prefix} {order.order_number}",
        )
        subtotal += total_price
    return subtotal


def _restore_items(order, note):
    for item in order.items.select_related("product").select_for_update():
        product = item.product
        product.stock_quantity += item.quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
        InventoryTransaction.objects.create(
            organisation=order.organisation,
            product=product,
            transaction_type=STOCK.STOCK_IN,
            quantity=item.quantity,
            note=f"{note} {order.order_number}",
        )


def _totals(subtotal, discount, tax):
    discount = Decimal(discount or 0)
    tax = Decimal(tax or 0)
    if discount < 0 or tax < 0:
        raise OrderError("Discount and tax cannot be negative.")
    total = subtotal - discount + tax
    if total < 0:
        raise OrderError("Discount cannot be greater than the order value.")
    return discount, tax, total


@transaction.atomic
def create_order(*, organisation, customer, items, user=None, discount=0, tax=0):
    merged = _merge_items(items)
    order = Order.objects.create(organisation=organisation, customer=customer, order_number="")
    subtotal = _write_items(order, merged)
    discount, tax, total = _totals(subtotal, discount, tax)
    order.subtotal, order.discount, order.tax, order.total_amount = subtotal, discount, tax, total
    order.save(update_fields=["subtotal", "discount", "tax", "total_amount", "updated_at"])
    _notify(
        organisation, user, "New Order Created",
        f"Order {order.order_number} has been created successfully for {customer.name}.",
        Notification.NotificationType.SUCCESS,
    )
    return order


@transaction.atomic
def update_order(*, order, customer, items, user=None, discount=None, tax=None):
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
        raise OrderError("Completed or cancelled orders cannot be edited.")
    merged = _merge_items(items)

    _restore_items(order, "Stock restored while editing order")
    order.items.all().delete()
    subtotal = _write_items(order, merged, note_prefix="Stock out after editing order")

    discount, tax, total = _totals(
        subtotal,
        order.discount if discount is None else discount,
        order.tax if tax is None else tax,
    )
    order.customer = customer
    order.subtotal, order.discount, order.tax, order.total_amount = subtotal, discount, tax, total
    order.save(update_fields=["customer", "subtotal", "discount", "tax", "total_amount", "updated_at"])

    if hasattr(order, "invoice") and order.invoice.status in ("DRAFT", "ISSUED"):
        invoice = order.invoice
        invoice.subtotal, invoice.discount, invoice.tax, invoice.total_amount = subtotal, discount, tax, total
        invoice.save(update_fields=["subtotal", "discount", "tax", "total_amount", "updated_at"])

    _notify(
        order.organisation, user, "Order Updated",
        f"Order {order.order_number} has been updated successfully.",
        Notification.NotificationType.INFO,
    )
    return order


@transaction.atomic
def set_status(*, order, new_status, user=None):
    """Change an order's status. Cancelling restores stock. Returns True if changed."""
    if new_status not in Order.Status.values:
        raise OrderError("Invalid status.")
    if new_status == order.status:
        return False
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
        raise OrderError(f"A {order.get_status_display().lower()} order cannot be changed.")

    if new_status == Order.Status.CANCELLED:
        _restore_items(order, "Stock restored for cancelled order")
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        _notify(
            order.organisation, user, "Order Cancelled",
            f"Order {order.order_number} has been cancelled successfully. Stock has been restored.",
            Notification.NotificationType.WARNING,
        )
    else:
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
    return True
