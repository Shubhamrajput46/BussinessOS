from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum
from django.shortcuts import render

from common.utils import monthly_totals

from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.products.models import Product


@login_required
def analytics_dashboard(request):

    organisation = request.user.organisation

    # ==========================================
    # DATE FILTER
    # ==========================================

    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    # ==========================================
    # ORDERS
    # ==========================================

    orders = Order.objects.filter(
        organisation=organisation
    )

    # Apply date filter to orders
    if start_date:
        orders = orders.filter(
            created_at__date__gte=start_date
        )

    if end_date:
        orders = orders.filter(
            created_at__date__lte=end_date
        )

    valid_orders = orders.exclude(
        status=Order.Status.CANCELLED
    )

    total_orders = valid_orders.count()

    total_sales = (
        valid_orders.aggregate(
            total=Sum("total_amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==========================================
    # CUSTOMERS
    # ==========================================

    total_customers = Customer.objects.filter(
        organisation=organisation,
        is_active=True
    ).count()

    # ==========================================
    # PRODUCTS
    # ==========================================

    total_products = Product.objects.filter(
        organisation=organisation,
        is_active=True
    ).count()

    low_stock_products = Product.objects.filter(
        organisation=organisation,
        is_active=True,
        stock_quantity__lte=models.F(
            "low_stock_threshold"
        )
    ).count()

    # ==========================================
    # EXPENSES
    # ==========================================

    expenses = Expense.objects.filter(
        organisation=organisation,
        is_active=True
    )

    # Apply date filter to expenses
    if start_date:
        expenses = expenses.filter(
            expense_date__gte=start_date
        )

    if end_date:
        expenses = expenses.filter(
            expense_date__lte=end_date
        )

    total_expenses = (
        expenses.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==========================================
    # PAYMENT
    # ==========================================
    payments = Payment.objects.filter(
        organisation=organisation,
        status=Payment.Status.PAID
    )

    # Apply date filter to payments
    if start_date:
        payments = payments.filter(
            payment_date__date__gte=start_date
        )

    if end_date:
        payments = payments.filter(
            payment_date__date__lte=end_date
        )

    total_payments = (
        payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    # ==========================================
    # PROFIT
    # ==========================================

    profit = total_sales - total_expenses

    # ==========================================
    # AVERAGE ORDER VALUE
    # ==========================================

    valid_order_count = valid_orders.count()

    if valid_order_count > 0:

        average_order_value = (
            total_sales / valid_order_count
        )

    else:

        average_order_value = Decimal("0.00")

    # ==========================================
    # MONTHLY SALES
    # ==========================================

    monthly_sales = monthly_totals(valid_orders, "created_at", "total_amount")

    # ==========================================
    # MONTHLY EXPENSES
    # ==========================================

    monthly_expenses = monthly_totals(expenses, "expense_date", "amount")

    # ==========================================
    # COMBINE MONTHLY DATA
    # ==========================================

    monthly_data = {}

    # ------------------------------------------
    # SALES
    # ------------------------------------------

    for item in monthly_sales:

        month = item["month"]

        month_key = month.strftime("%Y-%m")

        monthly_data[month_key] = {
            "month": month,
            "sales": (
                item["total"]
                or Decimal("0.00")
            ),
            "expenses": Decimal("0.00"),
            "profit": Decimal("0.00"),
        }

    # ------------------------------------------
    # EXPENSES
    # ------------------------------------------

    for item in monthly_expenses:

        month = item["month"]

        month_key = month.strftime("%Y-%m")

        if month_key not in monthly_data:

            monthly_data[month_key] = {
                "month": month,
                "sales": Decimal("0.00"),
                "expenses": Decimal("0.00"),
                "profit": Decimal("0.00"),
            }

        monthly_data[month_key]["expenses"] = (
            item["total"]
            or Decimal("0.00")
        )

    # ==========================================
    # MONTHLY PROFIT
    # ==========================================

    for data in monthly_data.values():

        data["profit"] = (
            data["sales"]
            - data["expenses"]
        )

    # ==========================================
    # SORT MONTHLY DATA
    # ==========================================

    monthly_analytics = [
        data
        for key, data
        in sorted(monthly_data.items())
    ]

    # ==========================================
    # CONTEXT
    # ==========================================

    context = {

        "total_orders": total_orders,

        "total_sales": total_sales,

        "total_customers": total_customers,

        "total_products": total_products,

        "low_stock_products": low_stock_products,

        "total_expenses": total_expenses,

        "total_payments": total_payments,

        "profit": profit,

        "average_order_value": average_order_value,

        "monthly_analytics": monthly_analytics,

        "chart_json": {
                "labels": [d["month"].strftime("%b %Y") for d in monthly_analytics],
                "sales": [float(d["sales"]) for d in monthly_analytics],
                "expenses": [float(d["expenses"]) for d in monthly_analytics],
                "profit": [float(d["profit"]) for d in monthly_analytics],
            },

        # Date filter values
        "start_date": start_date,

        "end_date": end_date,
    }

    ## ==========================================
    ## RENDER
    ## ==========================================

    return render(
        request,
        "analytics.html",
        context
    )