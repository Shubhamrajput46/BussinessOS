from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.orders.models import Order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.products.models import Product


class AnalyticsDashboardTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Analytics Company",
            email="analytics@company.com",
        )

        self.user = User.objects.create_user(
            username="analyticsuser",
            email="analyticsuser@company.com",
            password="testpass123",
            organisation=self.organisation,
        )

        self.client.login(
            username="analyticsuser",
            password="testpass123",
        )

        self.customer = Customer.objects.create(
            organisation=self.organisation,
            name="Test Customer",
        )

        self.product = Product.objects.create(
            organisation=self.organisation,
            name="Test Product",
            sku="TEST-001",
            cost_price=Decimal("500.00"),
            selling_price=Decimal("1000.00"),
            stock_quantity=3,
            low_stock_threshold=5,
        )

    def test_analytics_dashboard_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(response.status_code, 302)

    def test_analytics_dashboard_loads(self):
        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(response.status_code, 200)

    def test_total_products(self):
        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_products"],
            1,
        )

    def test_low_stock_products(self):
        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["low_stock_products"],
            1,
        )

    def test_total_orders_and_sales(self):
        Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("2000.00"),
            discount=Decimal("100.00"),
            tax=Decimal("100.00"),
            total_amount=Decimal("2000.00"),
            status=Order.Status.COMPLETED,
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_orders"],
            1,
        )

        self.assertEqual(
            response.context["total_sales"],
            Decimal("2000.00"),
        )

    def test_cancelled_orders_are_excluded(self):
        Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("5000.00"),
            status=Order.Status.CANCELLED,
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_orders"],
            0,
        )

        self.assertEqual(
            response.context["total_sales"],
            Decimal("0.00"),
        )

    def test_total_expenses(self):
        Expense.objects.create(
            organisation=self.organisation,
            title="Office Rent",
            category=Expense.Category.RENT,
            amount=Decimal("1000.00"),
            expense_date="2026-09-01",
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_expenses"],
            Decimal("1000.00"),
        )

    def test_profit_calculation(self):
        Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("5000.00"),
            status=Order.Status.COMPLETED,
        )

        Expense.objects.create(
            organisation=self.organisation,
            title="Transport",
            category=Expense.Category.TRANSPORT,
            amount=Decimal("1500.00"),
            expense_date="2026-09-01",
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["profit"],
            Decimal("3500.00"),
        )

    def test_average_order_value(self):
        Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("1000.00"),
            status=Order.Status.COMPLETED,
        )

        Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("3000.00"),
            status=Order.Status.COMPLETED,
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["average_order_value"],
            Decimal("2000.00"),
        )

    def test_total_paid_payments(self):
        order = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("2000.00"),
            status=Order.Status.COMPLETED,
        )

        Payment.objects.create(
            organisation=self.organisation,
            order=order,
            amount=Decimal("1500.00"),
            method=Payment.Method.UPI,
            status=Payment.Status.PAID,
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_payments"],
            Decimal("1500.00"),
        )

    def test_unpaid_payments_are_excluded(self):
        order = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            total_amount=Decimal("2000.00"),
            status=Order.Status.COMPLETED,
        )

        Payment.objects.create(
            organisation=self.organisation,
            order=order,
            amount=Decimal("1500.00"),
            method=Payment.Method.CASH,
            status=Payment.Status.PENDING,
        )

        response = self.client.get(
            reverse("analytics_dashboard")
        )

        self.assertEqual(
            response.context["total_payments"],
            Decimal("0.00"),
        )