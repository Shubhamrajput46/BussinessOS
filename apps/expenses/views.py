from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from common import roles
from common.permissions import role_required
from common.utils import (
    FormError,
    paginate,
    parse_date,
    parse_decimal,
    querystring_without_page,
    require_text,
)

from .models import Expense


def _clean(request):
    data = request.POST
    category = data.get("category", "")
    if category not in Expense.Category.values:
        raise FormError("Please choose a valid category.")
    return {
        "title": require_text(data.get("title"), "Title", max_length=150),
        "category": category,
        "amount": parse_decimal(data.get("amount"), "Amount", minimum=Decimal("0.01")),
        "description": data.get("description", "").strip(),
        "expense_date": parse_date(data.get("expense_date"), "Expense date"),
        "is_active": data.get("is_active") == "on",
    }


def _form_context(**extra):
    return {"categories": Expense.Category.choices, **extra}


@login_required
@role_required(*roles.EXPENSE_VIEW)
def expense_list(request):
    expenses = Expense.objects.filter(organisation=request.user.organisation).order_by(
        "-expense_date", "-created_at"
    )
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if q:
        expenses = expenses.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category in Expense.Category.values:
        expenses = expenses.filter(category=category)

    total = expenses.filter(is_active=True).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    page = paginate(request, expenses)
    return render(
        request,
        "expense_list.html",
        {
            "page_obj": page,
            "expenses": page.object_list,
            "q": q,
            "category": category,
            "categories": Expense.Category.choices,
            "filtered_total": total,
            "qs": querystring_without_page(request),
        },
    )


@login_required
@role_required(*roles.EXPENSE_WRITE)
def expense_create(request):
    context = _form_context()
    if request.method == "POST":
        try:
            Expense.objects.create(organisation=request.user.organisation, **_clean(request))
        except FormError as exc:
            context = _form_context(error=str(exc), posted=request.POST)
        else:
            messages.success(request, "Expense added successfully.")
            return redirect("expense_list")
    return render(request, "expense_form.html", context)


@login_required
@role_required(*roles.EXPENSE_WRITE)
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, organisation=request.user.organisation)
    context = _form_context(expense=expense)
    if request.method == "POST":
        try:
            for field, value in _clean(request).items():
                setattr(expense, field, value)
            expense.save()
        except FormError as exc:
            context = _form_context(expense=expense, error=str(exc), posted=request.POST)
        else:
            messages.success(request, "Expense updated successfully.")
            return redirect("expense_list")
    return render(request, "expense_form.html", context)


@login_required
@role_required(*roles.DELETE)
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, organisation=request.user.organisation)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("expense_list")
    return render(request, "expense_delete.html", {"expense": expense})
