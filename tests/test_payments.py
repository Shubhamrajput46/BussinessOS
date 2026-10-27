from decimal import Decimal

from django.test import TestCase

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.organizations.models import Organisation
from apps.payments.models import Payment


class PaymentTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="payment@test.com",
        )

        self.customer = Customer.objects.create(
            organisation=self.organisation,
            name="Test Customer",
        )

        self.order = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("10000.00"),
            total_amount=Decimal("10000.00"),
        )

    def test_payment_is_created(self):
        payment = Payment.objects.create(
            organisation=self.organisation,
            order=self.order,
            amount=Decimal("5000.00"),
            method=Payment.Method.UPI,
        )

        self.assertEqual(
            payment.amount,
            Decimal("5000.00"),
        )

        self.assertEqual(
            payment.order,
            self.order,
        )

        self.assertEqual(
            payment.organisation,
            self.organisation,
        )

    def test_payment_method(self):
        payment = Payment.objects.create(
            organisation=self.organisation,
            order=self.order,
            amount=Decimal("5000.00"),
            method=Payment.Method.CARD,
        )

        self.assertEqual(
            payment.method,
            Payment.Method.CARD,
        )

    def test_payment_status_is_pending_by_default(self):
        payment = Payment.objects.create(
            organisation=self.organisation,
            order=self.order,
            amount=Decimal("5000.00"),
            method=Payment.Method.CASH,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    def test_payment_status_can_be_paid(self):
        payment = Payment.objects.create(
            organisation=self.organisation,
            order=self.order,
            amount=Decimal("10000.00"),
            method=Payment.Method.UPI,
            status=Payment.Status.PAID,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PAID,
        )

    def test_payment_reference_is_saved(self):
        payment = Payment.objects.create(
            organisation=self.organisation,
            order=self.order,
            amount=Decimal("5000.00"),
            method=Payment.Method.UPI,
            transaction_reference="UPI-TXN-12345",
        )

        self.assertEqual(
            payment.transaction_reference,
            "UPI-TXN-12345",
        )