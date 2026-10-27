from decimal import Decimal

from django.test import TestCase

from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from apps.organizations.models import Organisation
from apps.products.models import Product


class OrderItemTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="orderitem@test.com",
        )

        self.customer = Customer.objects.create(
            organisation=self.organisation,
            name="Test Customer",
        )

        self.product = Product.objects.create(
            organisation=self.organisation,
            name="Laptop",
            sku="LAP-001",
            cost_price=Decimal("40000.00"),
            selling_price=Decimal("50000.00"),
            stock_quantity=10,
        )

        self.order = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("100000.00"),
            total_amount=Decimal("100000.00"),
        )

    def test_order_item_belongs_to_correct_order(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("50000.00"),
            total_price=Decimal("100000.00"),
        )

        self.assertEqual(item.order, self.order)
        self.assertEqual(item.product, self.product)

    def test_order_item_quantity_is_saved(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=3,
            unit_price=Decimal("50000.00"),
            total_price=Decimal("150000.00"),
        )

        self.assertEqual(item.quantity, 3)

    def test_order_item_total_price_is_saved(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("50000.00"),
            total_price=Decimal("100000.00"),
        )

        expected_total = item.quantity * item.unit_price

        self.assertEqual(
            item.total_price,
            expected_total,
        )