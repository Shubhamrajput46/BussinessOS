from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import FormError, paginate, querystring_without_page, require_text

from .models import Customer


def _clean(request):
    data = request.POST
    email = data.get("email", "").strip().lower()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            raise FormError("Enter a valid email address.")
    phone = require_text(data.get("phone"), "Phone", max_length=20)
    return {
        "name": require_text(data.get("name"), "Customer name", max_length=150),
        "email": email,
        "phone": phone,
        "address": data.get("address", "").strip(),
        "is_active": data.get("is_active") == "on",
    }


@login_required
def customer_list(request):
    customers = Customer.objects.filter(organisation=request.user.organisation).order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    if status == "active":
        customers = customers.filter(is_active=True)
    elif status == "inactive":
        customers = customers.filter(is_active=False)

    page = paginate(request, customers)
    return render(
        request,
        "customer_list.html",
        {
            "page_obj": page,
            "customers": page.object_list,
            "q": q,
            "status": status,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.CUSTOMER_CREATE)
def customer_create(request):
    context = {}
    if request.method == "POST":
        try:
            Customer.objects.create(organisation=request.user.organisation, **_clean(request))
        except FormError as exc:
            context = {"error": str(exc), "posted": request.POST}
        else:
            messages.success(request, "Customer created successfully.")
            return redirect("customer_list")
    return render(request, "customer_form.html", context)


@login_required
@role_required(*roles.CUSTOMER_WRITE)
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk, organisation=request.user.organisation)
    context = {"customer": customer}
    if request.method == "POST":
        try:
            for field, value in _clean(request).items():
                setattr(customer, field, value)
            customer.save()
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
        else:
            messages.success(request, "Customer updated successfully.")
            return redirect("customer_list")
    return render(request, "customer_form.html", context)


@login_required
@role_required(*roles.CUSTOMER_WRITE)
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, organisation=request.user.organisation)
    if request.method == "POST":
        try:
            customer.delete()
        except ProtectedError:
            messages.error(
                request,
                "This customer has orders and cannot be deleted. Mark them as inactive instead.",
            )
        else:
            messages.success(request, "Customer deleted.")
        return redirect("customer_list")
    return render(request, "customer_delete.html", {"customer": customer})
