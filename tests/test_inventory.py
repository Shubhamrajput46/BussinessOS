from django.test import TestCase

from apps.inventory.models import InventoryTransaction
from apps.organizations.models import Organisation
from apps.products.models import Product


class InventoryTransactionTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="inventory@test.com",
        )

        self.product = Product.objects.create(
            organisation=self.organisation,
            name="Laptop",
            sku="LAP-001",
            cost_price=40000,
            selling_price=50000,
            stock_quantity=10,
        )

    def test_stock_in_transaction(self):
        transaction = InventoryTransaction.objects.create(
            organisation=self.organisation,
            product=self.product,
            transaction_type=InventoryTransaction.TransactionType.STOCK_IN,
            quantity=5,
            note="New stock received",
        )

        self.assertEqual(
            transaction.transaction_type,
            InventoryTransaction.TransactionType.STOCK_IN,
        )

        self.assertEqual(
            transaction.quantity,
            5,
        )

    def test_stock_out_transaction(self):
        transaction = InventoryTransaction.objects.create(
            organisation=self.organisation,
            product=self.product,
            transaction_type=InventoryTransaction.TransactionType.STOCK_OUT,
            quantity=2,
            note="Sold product",
        )

        self.assertEqual(
            transaction.transaction_type,
            InventoryTransaction.TransactionType.STOCK_OUT,
        )

        self.assertEqual(
            transaction.quantity,
            2,
        )

    def test_adjustment_transaction(self):
        transaction = InventoryTransaction.objects.create(
            organisation=self.organisation,
            product=self.product,
            transaction_type=InventoryTransaction.TransactionType.ADJUSTMENT,
            quantity=3,
            note="Stock correction",
        )

        self.assertEqual(
            transaction.transaction_type,
            InventoryTransaction.TransactionType.ADJUSTMENT,
        )

        self.assertEqual(
            transaction.quantity,
            3,
        )

    def test_transaction_belongs_to_correct_organisation(self):
        transaction = InventoryTransaction.objects.create(
            organisation=self.organisation,
            product=self.product,
            transaction_type=InventoryTransaction.TransactionType.STOCK_IN,
            quantity=5,
        )

        self.assertEqual(
            transaction.organisation,
            self.organisation,
        )

        self.assertEqual(
            transaction.product,
            self.product,
        )