from django.db import IntegrityError
from django.test import TestCase

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.organizations.models import Organisation


class OrderTest(TestCase):

    def setUp(self):
        self.org1 = Organisation.objects.create(
            name="Company One",
            email="company1@test.com",
        )

        self.org2 = Organisation.objects.create(
            name="Company Two",
            email="company2@test.com",
        )

        self.customer1 = Customer.objects.create(
            organisation=self.org1,
            name="Customer One",
        )

        self.customer2 = Customer.objects.create(
            organisation=self.org2,
            name="Customer Two",
        )

    def test_order_belongs_to_correct_organisation(self):
        order = Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            subtotal=1000,
            discount=100,
            tax=90,
            total_amount=990,
        )

        self.assertEqual(
            order.organisation,
            self.org1,
        )

        self.assertEqual(
            order.customer,
            self.customer1,
        )

    def test_order_number_is_generated_automatically(self):
        order = Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            subtotal=1000,
            total_amount=1000,
        )

        self.assertEqual(
            order.order_number,
            "ORD-0001",
        )

    def test_order_number_increments(self):
        order1 = Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            subtotal=1000,
            total_amount=1000,
        )

        order2 = Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            subtotal=2000,
            total_amount=2000,
        )

        self.assertEqual(
            order1.order_number,
            "ORD-0001",
        )

        self.assertEqual(
            order2.order_number,
            "ORD-0002",
        )

    def test_same_order_number_not_allowed_in_same_organisation(self):
        Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            order_number="ORD-9999",
            subtotal=1000,
            total_amount=1000,
        )

        with self.assertRaises(IntegrityError):
            Order.objects.create(
                organisation=self.org1,
                customer=self.customer1,
                order_number="ORD-9999",
                subtotal=2000,
                total_amount=2000,
            )

    def test_same_order_number_allowed_for_different_organisations(self):
        order1 = Order.objects.create(
            organisation=self.org1,
            customer=self.customer1,
            order_number="ORD-1000",
            subtotal=1000,
            total_amount=1000,
        )

        order2 = Order.objects.create(
            organisation=self.org2,
            customer=self.customer2,
            order_number="ORD-1000",
            subtotal=2000,
            total_amount=2000,
        )

        self.assertEqual(
            order1.order_number,
            order2.order_number,
        )

        self.assertNotEqual(
            order1.organisation,
            order2.organisation,
        )