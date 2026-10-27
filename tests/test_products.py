from django.db import IntegrityError
from django.test import TestCase

from apps.organizations.models import Organisation
from apps.products.models import Product


class ProductTest(TestCase):

    def setUp(self):
        self.org1 = Organisation.objects.create(
            name="Company One",
            email="company1@test.com",
        )

        self.org2 = Organisation.objects.create(
            name="Company Two",
            email="company2@test.com",
        )

    def test_product_belongs_to_correct_organisation(self):
        product = Product.objects.create(
            organisation=self.org1,
            name="Laptop",
            sku="LAP-001",
            description="Business Laptop",
            selling_price=50000,
            cost_price=40000,
            stock_quantity=10,
            low_stock_threshold=5,
        )

        self.assertEqual(
            product.organisation,
            self.org1,
        )

    def test_duplicate_sku_not_allowed_in_same_organisation(self):
        Product.objects.create(
            organisation=self.org1,
            name="Laptop",
            sku="LAP-001",
            selling_price=50000,
            cost_price=40000,
            stock_quantity=10,
        )

        with self.assertRaises(IntegrityError):
            Product.objects.create(
                organisation=self.org1,
                name="Another Laptop",
                sku="LAP-001",
                selling_price=60000,
                cost_price=45000,
                stock_quantity=5,
            )

    def test_same_sku_allowed_for_different_organisations(self):
        product1 = Product.objects.create(
            organisation=self.org1,
            name="Laptop",
            sku="LAP-001",
            selling_price=50000,
            cost_price=40000,
            stock_quantity=10,
        )

        product2 = Product.objects.create(
            organisation=self.org2,
            name="Laptop",
            sku="LAP-001",
            selling_price=50000,
            cost_price=40000,
            stock_quantity=10,
        )

        self.assertEqual(product1.sku, product2.sku)
        self.assertNotEqual(
            product1.organisation,
            product2.organisation,
        )