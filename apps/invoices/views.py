from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import FormError, paginate, parse_date, querystring_without_page

from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.payments.services import paid_total, sync_invoice_status

from .models import Invoice

N = Notification.NotificationType


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
def invoice_list(request):
    invoices = (
        Invoice.objects.filter(organisation=request.user.organisation)
        .select_related("order", "order__customer")
        .order_by("-created_at")
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        invoices = invoices.filter(
            Q(invoice_number__icontains=q)
            | Q(order__order_number__icontains=q)
            | Q(order__customer__name__icontains=q)
        )
    if status in Invoice.Status.values:
        invoices = invoices.filter(status=status)

    page = paginate(request, invoices)
    return render(
        request,
        "invoice_list.html",
        {
            "page_obj": page,
            "invoices": page.object_list,
            "q": q,
            "status": status,
            "statuses": Invoice.Status.choices,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.FINANCE_VIEW)
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("order", "order__customer").prefetch_related(
            "order__items__product", "order__payments"
        ),
        pk=pk,
        organisation=request.user.organisation,
    )
    paid = paid_total(invoice.order)
    return render(
        request,
        "invoice_detail.html",
        {"invoice": invoice, "paid_amount": paid, "balance_due": max(invoice.total_amount - paid, 0)},
    )


@login_required
@role_required(*roles.FINANCE_WRITE)
def invoice_create(request):
    organisation = request.user.organisation
    # Only orders that do not have an invoice yet
    orders = (
        Order.objects.filter(organisation=organisation, invoice__isnull=True)
        .exclude(status=Order.Status.CANCELLED)
        .select_related("customer")
        .order_by("-created_at")
    )
    context = {"orders": orders, "selected_order": request.GET.get("order", "")}

    if request.method == "POST":
        order = get_object_or_404(
            Order.objects.exclude(status=Order.Status.CANCELLED),
            id=request.POST.get("order") or 0,
            organisation=organisation,
        )
        if hasattr(order, "invoice"):
            return redirect("invoice_detail", pk=order.invoice.pk)

        try:
            due_date = parse_date(request.POST.get("due_date"), "Due date", required=False)
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
            return render(request, "invoice_form.html", context)

        invoice = Invoice.objects.create(
            organisation=organisation,
            order=order,
            invoice_number="",
            status=Invoice.Status.ISSUED,
            subtotal=order.subtotal,
            discount=order.discount,
            tax=order.tax,
            total_amount=order.total_amount,
            due_date=due_date,
            notes=request.POST.get("notes", "").strip(),
        )
        sync_invoice_status(order)
        _notify(
            request, "Invoice Created",
            f"Invoice {invoice.invoice_number} has been created successfully for Order {order.order_number}.",
            N.SUCCESS,
        )
        messages.success(request, f"Invoice {invoice.invoice_number} created.")
        return redirect("invoice_detail", pk=invoice.pk)

    return render(request, "invoice_form.html", context)


@login_required
@role_required(*roles.FINANCE_WRITE)
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, organisation=request.user.organisation)
    context = {"invoice": invoice, "statuses": Invoice.Status.choices}

    if request.method == "POST":
        status = request.POST.get("status")
        try:
            if status not in Invoice.Status.values:
                raise FormError("Please choose a valid status.")
            invoice.due_date = parse_date(request.POST.get("due_date"), "Due date", required=False)
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
            return render(request, "invoice_form.html", context)

        invoice.status = status
        invoice.notes = request.POST.get("notes", "").strip()
        invoice.save()
        _notify(
            request, "Invoice Updated",
            f"Invoice {invoice.invoice_number} has been updated successfully.",
            N.INFO,
        )
        messages.success(request, "Invoice updated.")
        return redirect("invoice_detail", pk=invoice.pk)

    return render(request, "invoice_form.html", context)


@login_required
@role_required(*roles.DELETE)
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, organisation=request.user.organisation)
    if request.method == "POST":
        number = invoice.invoice_number
        invoice.delete()
        _notify(request, "Invoice Deleted", f"Invoice {number} has been deleted.", N.WARNING)
        messages.success(request, f"Invoice {number} deleted.")
        return redirect("invoice_list")
    return render(request, "invoice_delete.html", {"invoice": invoice})
