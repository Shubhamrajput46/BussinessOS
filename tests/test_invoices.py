from decimal import Decimal

from django.test import TestCase
from django.db import IntegrityError

from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.orders.models import Order
from apps.organizations.models import Organisation


class InvoiceTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="invoice@test.com",
        )

        self.customer = Customer.objects.create(
            organisation=self.organisation,
            name="Test Customer",
        )

        self.order = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("10000.00"),
            discount=Decimal("500.00"),
            tax=Decimal("950.00"),
            total_amount=Decimal("10450.00"),
        )

    def test_invoice_is_created(self):
        invoice = Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            subtotal=Decimal("10000.00"),
            discount=Decimal("500.00"),
            tax=Decimal("950.00"),
            total_amount=Decimal("10450.00"),
        )

        self.assertEqual(
            invoice.organisation,
            self.organisation,
        )

        self.assertEqual(
            invoice.order,
            self.order,
        )

    def test_invoice_number_is_generated_automatically(self):
        invoice = Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            total_amount=Decimal("10450.00"),
        )

        self.assertEqual(
            invoice.invoice_number,
            "INV-0001",
        )

    def test_invoice_number_increments(self):
        invoice1 = Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            total_amount=Decimal("10000.00"),
        )

        order2 = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("20000.00"),
            total_amount=Decimal("20000.00"),
        )

        invoice2 = Invoice.objects.create(
            organisation=self.organisation,
            order=order2,
            total_amount=Decimal("20000.00"),
        )

        self.assertEqual(
            invoice1.invoice_number,
            "INV-0001",
        )

        self.assertEqual(
            invoice2.invoice_number,
            "INV-0002",
        )

    def test_invoice_status_is_draft_by_default(self):
        invoice = Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            total_amount=Decimal("10450.00"),
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.DRAFT,
        )

    def test_invoice_can_be_marked_paid(self):
        invoice = Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            total_amount=Decimal("10450.00"),
            status=Invoice.Status.PAID,
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.PAID,
        )

    def test_same_invoice_number_not_allowed_in_same_organisation(self):
        Invoice.objects.create(
            organisation=self.organisation,
            order=self.order,
            invoice_number="INV-9999",
            total_amount=Decimal("10000.00"),
        )

        order2 = Order.objects.create(
            organisation=self.organisation,
            customer=self.customer,
            subtotal=Decimal("20000.00"),
            total_amount=Decimal("20000.00"),
        )

        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                organisation=self.organisation,
                order=order2,
                invoice_number="INV-9999",
                total_amount=Decimal("20000.00"),
            )