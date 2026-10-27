from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import FormError, paginate, parse_decimal, querystring_without_page

from apps.customers.models import Customer
from apps.products.models import Product

from .models import Order
from .services import OrderError, create_order, set_status, update_order


def _form_context(request, order=None, posted=None, error=None):
    organisation = request.user.organisation
    customers = Customer.objects.filter(organisation=organisation, is_active=True).order_by("name")
    products = Product.objects.filter(organisation=organisation, is_active=True).order_by("name")

    # Which products are ticked, and with what quantity?
    selected = {}
    if posted is not None:
        for pid in posted.getlist("products"):
            selected[str(pid)] = posted.get(f"quantity_{pid}", "1") or "1"
    elif order is not None:
        selected = {str(i.product_id): str(i.quantity) for i in order.items.all()}

    rows = [
        {
            "product": p,
            "selected": str(p.id) in selected,
            "quantity": selected.get(str(p.id), "1"),
        }
        for p in products
    ]

    return {
        "order": order,
        "customers": customers,
        "rows": rows,
        "selected_customer": (posted.get("customer") if posted is not None else (order.customer_id if order else "")),
        "discount": posted.get("discount", "") if posted is not None else (order.discount if order else "0"),
        "tax": posted.get("tax", "") if posted is not None else (order.tax if order else "0"),
        "error": error,
    }


def _read_form(request):
    organisation = request.user.organisation
    customer_id = request.POST.get("customer")
    if not customer_id:
        raise FormError("Please select a customer.")
    customer = get_object_or_404(Customer, id=customer_id, organisation=organisation, is_active=True)

    items = []
    for pid in request.POST.getlist("products"):
        items.append((pid, request.POST.get(f"quantity_{pid}", 0) or 0))
    if not items:
        raise FormError("Please select at least one product.")

    discount = parse_decimal(request.POST.get("discount"), "Discount", minimum=0, required=False)
    tax = parse_decimal(request.POST.get("tax"), "Tax", minimum=0, required=False)
    return customer, items, discount, tax


@login_required
@role_required(*roles.ORDER_VIEW)
def order_list(request):
    orders = (
        Order.objects.filter(organisation=request.user.organisation)
        .select_related("customer")
        .order_by("-created_at")
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        orders = orders.filter(Q(order_number__icontains=q) | Q(customer__name__icontains=q))
    if status in Order.Status.values:
        orders = orders.filter(status=status)

    page = paginate(request, orders)
    return render(
        request,
        "order_list.html",
        {
            "page_obj": page,
            "orders": page.object_list,
            "q": q,
            "status": status,
            "statuses": Order.Status.choices,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.ORDER_CREATE)
def order_create(request):
    if request.method == "POST":
        try:
            customer, items, discount, tax = _read_form(request)
            order = create_order(
                organisation=request.user.organisation,
                customer=customer,
                items=items,
                user=request.user,
                discount=discount,
                tax=tax,
            )
        except (FormError, OrderError) as exc:
            return render(request, "order_form.html", _form_context(request, posted=request.POST, error=str(exc)))
        messages.success(request, f"Order {order.order_number} created.")
        return redirect("order_detail", pk=order.pk)

    return render(request, "order_form.html", _form_context(request))


@login_required
@role_required(*roles.ORDER_VIEW)
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("items__product", "payments"),
        pk=pk,
        organisation=request.user.organisation,
    )
    return render(
        request,
        "order_detail.html",
        {
            "order": order,
            "statuses": Order.Status.choices,
            "locked": order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED),
        },
    )


@login_required
@role_required(*roles.ORDER_EDIT)
def order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk, organisation=request.user.organisation)

    if request.method == "POST":
        try:
            if set_status(order=order, new_status=request.POST.get("status"), user=request.user):
                messages.success(request, f"Order marked as {order.get_status_display().lower()}.")
        except OrderError as exc:
            messages.error(request, str(exc))

    return redirect("order_detail", pk=order.pk)


@login_required
@role_required(*roles.ORDER_EDIT)
def order_edit(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        pk=pk,
        organisation=request.user.organisation,
    )
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
        messages.error(request, "Completed or cancelled orders cannot be edited.")
        return redirect("order_detail", pk=order.pk)

    if request.method == "POST":
        try:
            customer, items, discount, tax = _read_form(request)
            update_order(order=order, customer=customer, items=items, user=request.user, discount=discount, tax=tax)
        except (FormError, OrderError) as exc:
            return render(
                request, "order_form.html", _form_context(request, order=order, posted=request.POST, error=str(exc))
            )
        messages.success(request, f"Order {order.order_number} updated.")
        return redirect("order_detail", pk=order.pk)

    return render(request, "order_form.html", _form_context(request, order=order))
