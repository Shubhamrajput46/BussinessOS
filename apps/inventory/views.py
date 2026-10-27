from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import FormError, paginate, parse_int, querystring_without_page

from apps.products.models import Product

from .models import InventoryTransaction
from .services import StockError, apply_transaction


@login_required
@role_required(*roles.INVENTORY)
def inventory_list(request):
    transactions = (
        InventoryTransaction.objects.filter(organisation=request.user.organisation)
        .select_related("product")
        .order_by("-created_at")
    )
    q = request.GET.get("q", "").strip()
    kind = request.GET.get("type", "")
    if q:
        transactions = transactions.filter(
            Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(note__icontains=q)
        )
    if kind in InventoryTransaction.TransactionType.values:
        transactions = transactions.filter(transaction_type=kind)

    page = paginate(request, transactions)
    return render(
        request,
        "inventory_list.html",
        {
            "page_obj": page,
            "transactions": page.object_list,
            "q": q,
            "type": kind,
            "types": InventoryTransaction.TransactionType.choices,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.INVENTORY)
def inventory_transaction_create(request):
    organisation = request.user.organisation
    products = Product.objects.filter(organisation=organisation, is_active=True).order_by("name")
    context = {
        "products": products,
        "types": InventoryTransaction.TransactionType.choices,
        "selected_product": request.GET.get("product", ""),
    }

    if request.method == "POST":
        try:
            product = get_object_or_404(
                Product, id=request.POST.get("product") or 0, organisation=organisation, is_active=True
            )
            quantity = parse_int(request.POST.get("quantity"), "Quantity", minimum=1)
            apply_transaction(
                organisation=organisation,
                product=product,
                transaction_type=request.POST.get("transaction_type"),
                quantity=quantity,
                note=request.POST.get("note", "").strip(),
                user=request.user,
            )
        except (FormError, StockError) as exc:
            context.update(error=str(exc), posted=request.POST)
        else:
            messages.success(request, "Inventory updated successfully.")
            return redirect("inventory_list")

    return render(request, "inventory_form.html", context)
