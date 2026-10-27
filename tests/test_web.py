from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.invoices.models import Invoice
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.products.models import Product

R = User.Role


class WebBase(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Acme", email="acme@test.com")
        self.users = {
            r: User.objects.create_user(
                username=r.lower(), email=f"{r.lower()}@t.com", password="Pass@12345", organisation=self.org, role=r
            )
            for r in R.values
        }
        self.customer = Customer.objects.create(organisation=self.org, name="Cust", phone="123")
        self.product = Product.objects.create(
            organisation=self.org, name="Widget", sku="W1", cost_price=10, selling_price=20, stock_quantity=10
        )
        self.order = create_order(
            organisation=self.org, customer=self.customer, items=[(self.product.id, 2)], user=self.users[R.OWNER]
        )
        self.invoice = Invoice.objects.create(
            organisation=self.org, order=self.order, invoice_number="", subtotal=40, total_amount=40, status="ISSUED"
        )
        self.payment = Payment.objects.create(
            organisation=self.org, order=self.order, amount=10, method="UPI", status="PAID"
        )
        self.expense = Expense.objects.create(
            organisation=self.org, title="Rent", category="RENT", amount=5, expense_date="2026-01-01"
        )
        self.notification = Notification.objects.create(
            organisation=self.org, user=self.users[R.OWNER], title="Hi", message="m"
        )

    def login(self, role=R.OWNER):
        self.client.force_login(self.users[role])


class PageRenderTests(WebBase):
    def pages(self):
        pk = lambda o: [o.pk]
        return [
            ("dashboard", []), ("analytics_dashboard", []), ("forecast_list", []), ("profile", []),
            ("product_list", []), ("product_create", []), ("product_edit", pk(self.product)), ("product_delete", pk(self.product)),
            ("customer_list", []), ("customer_create", []), ("customer_edit", pk(self.customer)), ("customer_delete", pk(self.customer)),
            ("inventory_list", []), ("inventory_transaction_create", []),
            ("order_list", []), ("order_create", []), ("order_detail", pk(self.order)), ("order_edit", pk(self.order)),
            ("expense_list", []), ("expense_create", []), ("expense_edit", pk(self.expense)), ("expense_delete", pk(self.expense)),
            ("payment_list", []), ("payment_create", []), ("payment_edit", pk(self.payment)), ("payment_delete", pk(self.payment)),
            ("invoice_list", []), ("invoice_create", []), ("invoice_detail", pk(self.invoice)), ("invoice_edit", pk(self.invoice)), ("invoice_delete", pk(self.invoice)),
            ("notification_list", []), ("notification_detail", pk(self.notification)), ("notification_delete", pk(self.notification)),
            ("user_list", []), ("user_create", []), ("user_edit", [self.users[R.STAFF].pk]), ("user_delete", [self.users[R.STAFF].pk]),
            ("organisation_settings", []),
        ]

    def test_owner_can_open_every_page(self):
        self.login(R.OWNER)
        for name, args in self.pages():
            with self.subTest(page=name):
                res = self.client.get(reverse(name, args=args))
                self.assertEqual(res.status_code, 200, name)
                self.assertContains(res, 'id="openSidebar"')  # hamburger on every page
                self.assertContains(res, "css/master.css")

    def test_public_pages(self):
        for name in ("home", "login", "signup"):
            res = self.client.get(reverse(name))
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, "css/master.css")
        self.assertContains(self.client.get(reverse("home")), 'id="pubToggle"')
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})

    def test_every_role_gets_a_valid_response_everywhere(self):
        for role in R.values:
            self.login(role)
            for name, args in self.pages():
                res = self.client.get(reverse(name, args=args))
                allowed = (200, 302, 404) if name.startswith("notification_") else (200, 302)  # notifications are per-user
                self.assertIn(res.status_code, allowed, f"{role} {name}")

    def test_anonymous_redirected_to_login(self):
        for name in ("dashboard", "product_list", "order_list", "analytics_dashboard"):
            res = self.client.get(reverse(name))
            self.assertEqual(res.status_code, 302)
            self.assertIn("/login/", res.url)

    def test_custom_404(self):
        self.assertEqual(self.client.get("/definitely-missing/").status_code, 404)


class RoleRuleTests(WebBase):
    def test_staff_cannot_create_or_delete_products(self):
        self.login(R.STAFF)
        self.assertEqual(self.client.get(reverse("product_create")).status_code, 302)
        self.assertEqual(self.client.post(reverse("product_delete", args=[self.product.pk])).status_code, 302)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_staff_cannot_see_finance(self):
        self.login(R.STAFF)
        self.assertEqual(self.client.get(reverse("payment_list")).status_code, 302)
        self.assertEqual(self.client.get(reverse("expense_list")).status_code, 302)

    def test_sidebar_hides_finance_for_staff(self):
        self.login(R.STAFF)
        self.assertNotContains(self.client.get(reverse("dashboard")), reverse("payment_list"))


class FlowTests(WebBase):
    def test_product_create_validation_and_duplicate_sku(self):
        self.login(R.MANAGER)
        res = self.client.post(reverse("product_create"), {"name": "X", "sku": "W1", "cost_price": "1", "selling_price": "2"})
        self.assertContains(res, "SKU already exists")
        res = self.client.post(reverse("product_create"), {"name": "X", "sku": "N1", "cost_price": "abc", "selling_price": "2"})
        self.assertContains(res, "valid number")
        res = self.client.post(
            reverse("product_create"),
            {"name": "X", "sku": "N1", "cost_price": "1", "selling_price": "2", "is_active": "on"},
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Product.objects.filter(sku="N1").exists())

    def test_delete_product_in_use_is_blocked_not_500(self):
        self.login(R.OWNER)
        res = self.client.post(reverse("product_delete", args=[self.product.pk]), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "cannot be deleted")
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_order_create_edit_cancel_cycle_keeps_stock_consistent(self):
        self.login(R.OWNER)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

        res = self.client.post(
            reverse("order_create"),
            {"customer": self.customer.pk, "products": [self.product.pk], f"quantity_{self.product.pk}": "3"},
        )
        self.assertEqual(res.status_code, 302)
        order = Order.objects.latest("id")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

        self.client.post(
            reverse("order_edit", args=[order.pk]),
            {"customer": self.customer.pk, "products": [self.product.pk], f"quantity_{self.product.pk}": "1"},
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

        self.client.post(reverse("order_update_status", args=[order.pk]), {"status": "CANCELLED"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_order_rejects_too_much_quantity(self):
        self.login(R.OWNER)
        res = self.client.post(
            reverse("order_create"),
            {"customer": self.customer.pk, "products": [self.product.pk], f"quantity_{self.product.pk}": "999"},
        )
        self.assertContains(res, "Not enough stock")

    def test_payment_marks_invoice_paid(self):
        self.login(R.ACCOUNTANT)
        self.client.post(
            reverse("payment_create"),
            {"order": self.order.pk, "amount": "30", "method": "CASH", "status": "PAID"},
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

    def test_invalid_payment_amount_shows_error(self):
        self.login(R.ACCOUNTANT)
        res = self.client.post(
            reverse("payment_create"), {"order": self.order.pk, "amount": "", "method": "CASH", "status": "PAID"}
        )
        self.assertContains(res, "Amount is required")

    def test_inventory_invalid_type_rejected(self):
        self.login(R.STAFF)
        res = self.client.post(
            reverse("inventory_transaction_create"),
            {"product": self.product.pk, "transaction_type": "HACK", "quantity": "1"},
        )
        self.assertContains(res, "Invalid transaction type")

    def test_forecast_generation_button(self):
        self.login(R.OWNER)
        res = self.client.post(reverse("forecast_generate"), follow=True)
        self.assertContains(res, "Not enough sales history")

    def test_login_by_email_and_username_and_next(self):
        for ident in ("owner@t.com", "owner"):
            self.client.logout()
            res = self.client.post(reverse("login"), {"email": ident, "password": "Pass@12345", "next": "/products/"})
            self.assertRedirects(res, "/products/", fetch_redirect_response=False)
        self.client.logout()
        res = self.client.post(reverse("login"), {"email": "owner", "password": "bad"})
        self.assertContains(res, "Invalid email or password")

    def test_open_redirect_blocked(self):
        res = self.client.post(
            reverse("login"), {"email": "owner", "password": "Pass@12345", "next": "https://evil.example/"}
        )
        self.assertRedirects(res, reverse("dashboard"), fetch_redirect_response=False)

    def test_signup_weak_password_rejected(self):
        res = self.client.post(
            reverse("signup"), {"username": "n", "email": "n@x.com", "password": "123", "organisation_name": "N"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(username="n").exists())

    def test_admin_cannot_delete_owner_and_notifications_post_only(self):
        self.login(R.ADMIN)
        self.client.post(reverse("user_delete", args=[self.users[R.OWNER].pk]))
        self.assertTrue(User.objects.filter(pk=self.users[R.OWNER].pk).exists())
        self.login(R.OWNER)
        self.assertEqual(self.client.get(reverse("notification_mark_all_read")).status_code, 405)

    def test_org_settings_update(self):
        self.login(R.OWNER)
        self.client.post(reverse("organisation_settings"), {"name": "Renamed", "email": "acme@test.com"})
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Renamed")

    def test_inr_filter(self):
        from common.templatetags.ui import inr

        self.assertEqual(inr(1234567.5), "₹12,34,567.50")
        self.assertEqual(inr(0), "₹0.00")
        self.assertEqual(inr(999), "₹999.00")


class PasswordResetTests(WebBase):
    def test_login_page_links_to_reset(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))

    def test_full_reset_flow(self):
        import re

        from django.core import mail

        res = self.client.post(reverse("password_reset"), {"email": "owner@t.com"})
        self.assertRedirects(res, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"https?://testserver(/reset/[^\s]+)", mail.outbox[0].body).group(1)

        res = self.client.get(link, follow=True)  # Django swaps the token into the session URL
        self.assertContains(res, "Create a new password")
        res = self.client.post(res.redirect_chain[-1][0], {"new_password1": "Br@ndNew-Pass-77", "new_password2": "Br@ndNew-Pass-77"})
        self.assertRedirects(res, reverse("password_reset_complete"))

        self.client.logout()
        res = self.client.post(reverse("login"), {"email": "owner", "password": "Br@ndNew-Pass-77"})
        self.assertRedirects(res, reverse("dashboard"), fetch_redirect_response=False)

    def test_unknown_email_gives_same_response_and_sends_nothing(self):
        from django.core import mail

        res = self.client.post(reverse("password_reset"), {"email": "nobody@x.com"})
        self.assertRedirects(res, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_link_shows_expired(self):
        self.assertContains(self.client.get("/reset/abc/set-password/"), "Link expired")

    def test_weak_new_password_rejected(self):
        import re

        from django.core import mail

        self.client.post(reverse("password_reset"), {"email": "owner@t.com"})
        link = re.search(r"https?://testserver(/reset/[^\s]+)", mail.outbox[0].body).group(1)
        url = self.client.get(link, follow=True).redirect_chain[-1][0]
        res = self.client.post(url, {"new_password1": "123", "new_password2": "123"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "alert-error")


class LogoutAndLandingTests(WebBase):
    def test_logout_goes_to_home_not_login(self):
        self.login(R.OWNER)
        res = self.client.get(reverse("logout"))
        self.assertRedirects(res, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_landing_has_all_sections_and_hamburger(self):
        res = self.client.get(reverse("home"))
        for anchor in ("features", "modules", "how", "roles", "developers", "faq"):
            self.assertContains(res, f'id="{anchor}"')
        self.assertContains(res, 'id="pubToggle"')
        self.assertContains(res, "Get started free")
