import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.invoices.models import Invoice
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.payments.services import sync_invoice_status
from apps.products.models import Product

DEMO_USERS = [
    ("owner", "Owner@12345", User.Role.OWNER),
    ("admin", "Admin@12345", User.Role.ADMIN),
    ("manager", "Manager@12345", User.Role.MANAGER),
    ("staff", "Staff@12345", User.Role.STAFF),
    ("accountant", "Accountant@12345", User.Role.ACCOUNTANT),
]

PRODUCTS = [
    ("Basmati Rice 5kg", "RICE-5KG", 380, 450, 120),
    ("Sunflower Oil 1L", "OIL-1L", 110, 140, 200),
    ("Tea Powder 500g", "TEA-500", 150, 190, 90),
    ("Sugar 1kg", "SUG-1KG", 38, 48, 300),
    ("Wheat Flour 10kg", "ATA-10KG", 360, 420, 60),
    ("Toor Dal 1kg", "DAL-1KG", 120, 155, 8),
]

CUSTOMERS = [
    ("Sharma General Store", "9876500001"),
    ("Patel Kirana", "9876500002"),
    ("Gupta Traders", "9876500003"),
    ("Verma Mart", "9876500004"),
]


class Command(BaseCommand):
    help = "Create a demo organisation with users for every role plus sample business data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete the demo organisation first.")

    def handle(self, *args, **options):
        email = "demo@businessos.local"
        if options["reset"]:
            User.objects.filter(email__endswith="@demo.businessos.local").delete()
            Organisation.objects.filter(email=email).delete()

        organisation, created = Organisation.objects.get_or_create(
            email=email, defaults={"name": "Demo Traders", "phone": "9876500000", "address": "Raipur, Chhattisgarh"}
        )

        owner = None
        for username, password, role in DEMO_USERS:
            user, new = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@demo.businessos.local",
                    "organisation": organisation,
                    "role": role,
                },
            )
            if new:
                user.set_password(password)
                user.save()
            if role == User.Role.OWNER:
                owner = user

        if not created and Order.objects.filter(organisation=organisation).exists():
            self.stdout.write(self.style.WARNING("Demo data already exists (use --reset to rebuild)."))
            return

        rng = random.Random(42)
        products = [
            Product.objects.create(
                organisation=organisation, name=n, sku=sku, cost_price=cost, selling_price=price,
                stock_quantity=stock, low_stock_threshold=10,
            )
            for n, sku, cost, price, stock in PRODUCTS
        ]
        customers = [
            Customer.objects.create(organisation=organisation, name=n, phone=p, email=f"{p}@example.com")
            for n, p in CUSTOMERS
        ]

        now = timezone.now()
        for day in range(30, -1, -1):
            for _ in range(rng.randint(0, 2)):
                picks = rng.sample(products[:5], rng.randint(1, 3))
                order = create_order(
                    organisation=organisation,
                    customer=rng.choice(customers),
                    items=[(p.id, rng.randint(1, 4)) for p in picks],
                    user=owner,
                )
                when = now - timedelta(days=day, hours=rng.randint(0, 8))
                Order.objects.filter(pk=order.pk).update(created_at=when)
                if day > 3:
                    order.status = Order.Status.COMPLETED if rng.random() > 0.15 else Order.Status.CONFIRMED
                    order.save(update_fields=["status"])
                if rng.random() > 0.4:
                    invoice = Invoice.objects.create(
                        organisation=organisation, order=order, invoice_number="", status=Invoice.Status.ISSUED,
                        subtotal=order.subtotal, discount=order.discount, tax=order.tax,
                        total_amount=order.total_amount, due_date=(when + timedelta(days=15)).date(),
                    )
                    if rng.random() > 0.3:
                        Payment.objects.create(
                            organisation=organisation, order=order, amount=order.total_amount,
                            method=rng.choice(Payment.Method.values), status=Payment.Status.PAID,
                            transaction_reference=f"TXN{order.pk:05d}",
                        )
                        sync_invoice_status(order)

        for title, category, amount in [
            ("Shop rent", Expense.Category.RENT, 18000),
            ("Staff salaries", Expense.Category.SALARY, 42000),
            ("Electricity bill", Expense.Category.ELECTRICITY, 5200),
            ("Delivery van fuel", Expense.Category.TRANSPORT, 6400),
        ]:
            Expense.objects.create(
                organisation=organisation, title=title, category=category,
                amount=Decimal(amount), expense_date=(now - timedelta(days=rng.randint(0, 25))).date(),
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready. Log in with owner / Owner@12345"))
