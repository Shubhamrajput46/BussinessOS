from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import FormError, paginate, parse_decimal, querystring_without_page

from apps.notifications.models import Notification
from apps.orders.models import Order

from .models import Payment
from .services import sync_invoice_status

N = Notification.NotificationType


def _orders(request):
    return (
        Order.objects.filter(organisation=request.user.organisation)
        .exclude(status=Order.Status.CANCELLED)
        .select_related("customer")
        .order_by("-created_at")
    )


def _form_context(request, **extra):
    return {
        "orders": _orders(request),
        "methods": Payment.Method.choices,
        "statuses": Payment.Status.choices,
        **extra,
    }


def _clean(request):
    data = request.POST
    order = get_object_or_404(_orders(request), id=data.get("order") or 0)
    method, status = data.get("method"), data.get("status")
    if method not in Payment.Method.values:
        raise FormError("Please choose a valid payment method.")
    if status not in Payment.Status.values:
        raise FormError("Please choose a valid payment status.")
    return order, {
        "amount": parse_decimal(data.get("amount"), "Amount", minimum=Decimal("0.01")),
        "method": method,
        "status": status,
        "transaction_reference": data.get("transaction_reference", "").strip(),
        "notes": data.get("notes", "").strip(),
    }


def _notify(request, title, message, kind):
    Notification.objects.create(
        organisation=request.user.organisation,
        user=request.user,
        title=title,
        message=message,
        notification_type=kind,
    )


@login_required
@role_required(*roles.FINANCE_VIEW)
def payment_list(request):
    payments = (
        Payment.objects.filter(organisation=request.user.organisation)
        .select_related("order", "order__customer")
        .order_by("-payment_date")
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        payments = payments.filter(
            Q(order__order_number__icontains=q)
            | Q(order__customer__name__icontains=q)
            | Q(transaction_reference__icontains=q)
        )
    if status in Payment.Status.values:
        payments = payments.filter(status=status)

    paid_total = payments.filter(status=Payment.Status.PAID).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    page = paginate(request, payments)
    return render(
        request,
        "payment_list.html",
        {
            "page_obj": page,
            "payments": page.object_list,
            "q": q,
            "status": status,
            "statuses": Payment.Status.choices,
            "paid_total": paid_total,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.FINANCE_WRITE)
def payment_create(request):
    context = _form_context(request, selected_order=request.GET.get("order", ""))
    if request.method == "POST":
        try:
            order, fields = _clean(request)
            payment = Payment.objects.create(organisation=request.user.organisation, order=order, **fields)
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
        else:
            sync_invoice_status(order)
            _notify(
                request, "Payment Added",
                f"Payment of ₹{payment.amount} has been added successfully for Order {order.order_number}.",
                N.SUCCESS,
            )
            messages.success(request, "Payment recorded.")
            return redirect("payment_list")
    return render(request, "payment_form.html", context)


@login_required
@role_required(*roles.FINANCE_WRITE)
def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk, organisation=request.user.organisation)
    context = _form_context(request, payment=payment)
    if request.method == "POST":
        try:
            order, fields = _clean(request)
            old_order = payment.order
            payment.order = order
            for field, value in fields.items():
                setattr(payment, field, value)
            payment.save()
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
        else:
            sync_invoice_status(order)
            if old_order.pk != order.pk:
                sync_invoice_status(old_order)
            _notify(
                request, "Payment Updated",
                f"Payment of ₹{payment.amount} for Order {order.order_number} has been updated successfully.",
                N.INFO,
            )
            messages.success(request, "Payment updated.")
            return redirect("payment_list")
    return render(request, "payment_form.html", context)


@login_required
@role_required(*roles.DELETE)
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk, organisation=request.user.organisation)
    if request.method == "POST":
        order, amount = payment.order, payment.amount
        payment.delete()
        sync_invoice_status(order)
        _notify(
            request, "Payment Deleted",
            f"Payment of ₹{amount} for Order {order.order_number} has been deleted.",
            N.WARNING,
        )
        messages.success(request, "Payment deleted.")
        return redirect("payment_list")
    return render(request, "payment_delete.html", {"payment": payment})
