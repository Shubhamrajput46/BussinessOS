from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.expenses.models import Expense
from apps.organizations.models import Organisation


class ExpenseTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="expense@test.com",
        )

    def test_expense_is_created(self):
        expense = Expense.objects.create(
            organisation=self.organisation,
            title="Office Rent",
            category=Expense.Category.RENT,
            amount=Decimal("15000.00"),
            description="Monthly office rent",
            expense_date=date(2026, 9, 14),
        )

        self.assertEqual(
            expense.title,
            "Office Rent",
        )

        self.assertEqual(
            expense.amount,
            Decimal("15000.00"),
        )

        self.assertEqual(
            expense.organisation,
            self.organisation,
        )

    def test_expense_category(self):
        expense = Expense.objects.create(
            organisation=self.organisation,
            title="Electricity Bill",
            category=Expense.Category.ELECTRICITY,
            amount=Decimal("2500.00"),
            expense_date=date(2026, 9, 14),
        )

        self.assertEqual(
            expense.category,
            Expense.Category.ELECTRICITY,
        )

    def test_expense_is_active_by_default(self):
        expense = Expense.objects.create(
            organisation=self.organisation,
            title="Office Supplies",
            category=Expense.Category.OFFICE,
            amount=Decimal("3000.00"),
            expense_date=date(2026, 9, 14),
        )

        self.assertTrue(expense.is_active)

    def test_expense_can_be_deactivated(self):
        expense = Expense.objects.create(
            organisation=self.organisation,
            title="Old Expense",
            category=Expense.Category.OTHER,
            amount=Decimal("1000.00"),
            expense_date=date(2026, 9, 14),
            is_active=False,
        )

        self.assertFalse(expense.is_active)