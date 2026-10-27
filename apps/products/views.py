from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import (
    FormError,
    paginate,
    parse_decimal,
    parse_int,
    querystring_without_page,
    require_text,
)

from .models import Product


def _clean(request, instance=None):
    data = request.POST
    organisation = request.user.organisation

    name = require_text(data.get("name"), "Product name", max_length=150)
    sku = require_text(data.get("sku"), "SKU", max_length=50)

    duplicate = Product.objects.filter(organisation=organisation, sku__iexact=sku)
    if instance:
        duplicate = duplicate.exclude(pk=instance.pk)
    if duplicate.exists():
        raise FormError("A product with this SKU already exists.")

    cost_price = parse_decimal(data.get("cost_price"), "Cost price", minimum=0)
    selling_price = parse_decimal(data.get("selling_price"), "Selling price", minimum=0)
    if selling_price < cost_price:
        raise FormError("Selling price cannot be lower than cost price.")

    return {
        "name": name,
        "sku": sku,
        "description": data.get("description", "").strip(),
        "cost_price": cost_price,
        "selling_price": selling_price,
        "stock_quantity": parse_int(data.get("stock_quantity"), "Stock quantity", required=False, default=0),
        "low_stock_threshold": parse_int(
            data.get("low_stock_threshold"), "Low stock threshold", required=False, default=5
        ),
        "is_active": data.get("is_active") == "on",
    }


@login_required
def product_list(request):
    products = Product.objects.filter(organisation=request.user.organisation).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "inactive":
        products = products.filter(is_active=False)
    elif status == "low":
        products = products.filter(is_active=True, stock_quantity__lte=F("low_stock_threshold"))

    page = paginate(request, products)
    return render(
        request,
        "product_list.html",
        {
            "page_obj": page,
            "products": page.object_list,
            "q": q,
            "status": status,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.PRODUCT_WRITE)
def product_create(request):
    context = {}
    if request.method == "POST":
        try:
            Product.objects.create(organisation=request.user.organisation, **_clean(request))
        except FormError as exc:
            context = {"error": str(exc), "posted": request.POST}
        else:
            messages.success(request, "Product created successfully.")
            return redirect("product_list")
    return render(request, "product_form.html", context)


@login_required
@role_required(*roles.PRODUCT_WRITE)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, organisation=request.user.organisation)
    context = {"product": product}
    if request.method == "POST":
        try:
            for field, value in _clean(request, product).items():
                setattr(product, field, value)
            product.save()
        except FormError as exc:
            context.update(error=str(exc), posted=request.POST)
        else:
            messages.success(request, "Product updated successfully.")
            return redirect("product_list")
    return render(request, "product_form.html", context)


@login_required
@role_required(*roles.PRODUCT_DELETE)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, organisation=request.user.organisation)
    if request.method == "POST":
        try:
            product.delete()
        except ProtectedError:
            messages.error(
                request,
                "This product is used in existing orders and cannot be deleted. "
                "Mark it as inactive instead.",
            )
        else:
            messages.success(request, "Product deleted.")
        return redirect("product_list")
    return render(request, "product_delete.html", {"product": product})
