from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.organizations.models import Organisation
from apps.products.models import Product

R = User.Role


class ApiBase(APITestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Acme", email="acme@test.com")
        self.other_org = Organisation.objects.create(name="Other", email="other@test.com")
        self.users = {
            role: User.objects.create_user(
                username=role.lower(), email=f"{role.lower()}@test.com", password="Pass@12345",
                organisation=self.org, role=role,
            )
            for role in R.values
        }
        self.customer = Customer.objects.create(organisation=self.org, name="Cust", phone="9999999999")
        self.product = Product.objects.create(
            organisation=self.org, name="Widget", sku="W-1", cost_price=10, selling_price=25,
            stock_quantity=10, low_stock_threshold=2,
        )

    def as_role(self, role):
        client = APIClient()
        client.force_authenticate(self.users[role])
        return client


class AuthTests(ApiBase):
    def test_token_with_username_and_email(self):
        for ident in ("owner", "owner@test.com"):
            res = APIClient().post(reverse("token"), {"username": ident, "password": "Pass@12345"}, format="json")
            self.assertEqual(res.status_code, 200, res.content)
            self.assertIn("access", res.data)
            self.assertEqual(res.data["user"]["role"], "OWNER")

    def test_bad_password_rejected(self):
        res = APIClient().post(reverse("token"), {"username": "owner", "password": "nope"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_bearer_token_works_end_to_end(self):
        token = APIClient().post(
            reverse("token"), {"username": "owner", "password": "Pass@12345"}, format="json"
        ).data["access"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get("/api/v1/Product/").status_code, 200)
        self.assertEqual(client.get(reverse("api_profile")).data["role"], "OWNER")

    def test_anonymous_is_blocked(self):
        self.assertIn(APIClient().get("/api/v1/Product/").status_code, (401, 403))

    def test_swagger_and_schema_available(self):
        self.assertEqual(APIClient().get(reverse("schema")).status_code, 200)
        self.assertEqual(APIClient().get(reverse("swagger-ui")).status_code, 200)


class ProductApiTests(ApiBase):
    def test_crud_and_duplicate_sku(self):
        client = self.as_role(R.MANAGER)
        payload = {"name": "Gadget", "sku": "G-1", "cost_price": "5", "selling_price": "9"}
        res = client.post("/api/v1/Product/", payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(client.post("/api/v1/Product/", payload, format="json").status_code, 400)

    def test_staff_cannot_create_or_delete(self):
        client = self.as_role(R.STAFF)
        self.assertEqual(client.get("/api/v1/Product/").status_code, 200)
        self.assertEqual(client.post("/api/v1/Product/", {}, format="json").status_code, 403)
        self.assertEqual(client.delete(f"/api/v1/Product/{self.product.pk}/").status_code, 403)

    def test_other_org_data_is_invisible(self):
        Product.objects.create(
            organisation=self.other_org, name="Secret", sku="S", cost_price=1, selling_price=2
        )
        res = self.as_role(R.OWNER).get("/api/v1/Product/")
        self.assertEqual(res.data["count"], 1)

    def test_delete_product_used_in_order_is_conflict_not_500(self):
        client = self.as_role(R.OWNER)
        client.post(
            "/api/v1/Order/",
            {"customer": self.customer.pk, "items_input": [{"product": self.product.pk, "quantity": 1}]},
            format="json",
        )
        res = client.delete(f"/api/v1/Product/{self.product.pk}/")
        self.assertEqual(res.status_code, 409)


class OrderFlowApiTests(ApiBase):
    def create_order(self, qty=3, role=R.STAFF, **extra):
        return self.as_role(role).post(
            "/api/v1/Order/",
            {"customer": self.customer.pk, "items_input": [{"product": self.product.pk, "quantity": qty}], **extra},
            format="json",
        )

    def test_create_order_deducts_stock_and_totals(self):
        res = self.create_order(3, discount="5", tax="2")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["subtotal"]), Decimal("75.00"))
        self.assertEqual(Decimal(res.data["total_amount"]), Decimal("72.00"))
        self.assertEqual(len(res.data["items"]), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    def test_not_enough_stock(self):
        res = self.create_order(99)
        self.assertEqual(res.status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_order_requires_items(self):
        res = self.as_role(R.OWNER).post("/api/v1/Order/", {"customer": self.customer.pk}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cancel_restores_stock_and_is_final(self):
        order_id = self.create_order(4).data["id"]
        res = self.as_role(R.MANAGER).post(f"/api/v1/Order/{order_id}/status/", {"status": "CANCELLED"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        again = self.as_role(R.MANAGER).post(f"/api/v1/Order/{order_id}/status/", {"status": "PENDING"}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_staff_cannot_change_status(self):
        order_id = self.create_order(1).data["id"]
        res = self.as_role(R.STAFF).post(f"/api/v1/Order/{order_id}/status/", {"status": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_edit_items_rebalances_stock(self):
        order_id = self.create_order(4).data["id"]
        res = self.as_role(R.MANAGER).patch(
            f"/api/v1/Order/{order_id}/",
            {"items_input": [{"product": self.product.pk, "quantity": 2}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_cannot_order_for_foreign_customer(self):
        foreign = Customer.objects.create(organisation=self.other_org, name="X", phone="1")
        res = self.as_role(R.OWNER).post(
            "/api/v1/Order/",
            {"customer": foreign.pk, "items_input": [{"product": self.product.pk, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_invoice_and_payment_flow_marks_invoice_paid(self):
        order = self.create_order(2).data
        accountant = self.as_role(R.ACCOUNTANT)

        inv = accountant.post("/api/v1/Invoice/", {"order": order["id"]}, format="json")
        self.assertEqual(inv.status_code, 201, inv.content)
        self.assertEqual(inv.data["status"], "ISSUED")
        self.assertEqual(Decimal(inv.data["total_amount"]), Decimal("50.00"))
        self.assertEqual(accountant.post("/api/v1/Invoice/", {"order": order["id"]}, format="json").status_code, 400)

        pay = accountant.post(
            "/api/v1/Payment/", {"order": order["id"], "amount": "50", "method": "UPI", "status": "PAID"}, format="json"
        )
        self.assertEqual(pay.status_code, 201, pay.content)
        self.assertEqual(accountant.get(f"/api/v1/Invoice/{inv.data['id']}/").data["status"], "PAID")

        accountant_delete = self.as_role(R.OWNER).delete(f"/api/v1/Payment/{pay.data['id']}/")
        self.assertEqual(accountant_delete.status_code, 204)
        self.assertEqual(self.as_role(R.OWNER).get(f"/api/v1/Invoice/{inv.data['id']}/").data["status"], "ISSUED")


class InventoryApiTests(ApiBase):
    def test_ledger_entry_moves_stock(self):
        client = self.as_role(R.STAFF)
        res = client.post(
            "/api/v1/Inventory/",
            {"product": self.product.pk, "transaction_type": "STOCK_IN", "quantity": 5}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 15)

        res = client.post(
            "/api/v1/Inventory/",
            {"product": self.product.pk, "transaction_type": "STOCK_OUT", "quantity": 100}, format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_ledger_is_append_only(self):
        self.assertEqual(self.as_role(R.OWNER).delete("/api/v1/Inventory/1/").status_code, 405)


class AccountApiTests(ApiBase):
    def test_admin_cannot_create_owner(self):
        res = self.as_role(R.ADMIN).post(
            "/api/v1/Account/",
            {"username": "evil", "email": "evil@test.com", "password": "Str0ng!Pass99", "role": "OWNER"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_admin_creates_staff_in_own_org_with_hashed_password(self):
        res = self.as_role(R.ADMIN).post(
            "/api/v1/Account/",
            {"username": "newbie", "email": "newbie@test.com", "password": "Str0ng!Pass99", "role": "STAFF"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        user = User.objects.get(username="newbie")
        self.assertEqual(user.organisation_id, self.org.pk)
        self.assertTrue(user.check_password("Str0ng!Pass99"))

    def test_weak_password_rejected(self):
        res = self.as_role(R.OWNER).post(
            "/api/v1/Account/", {"username": "w", "email": "w@test.com", "password": "123"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_cannot_change_own_role(self):
        res = self.as_role(R.ADMIN).patch(f"/api/v1/Account/{self.users[R.ADMIN].pk}/", {"role": "STAFF"}, format="json")
        self.assertEqual(res.status_code, 400)


class DashboardAndForecastApiTests(ApiBase):
    def test_dashboard_summary(self):
        OrderClient = self.as_role(R.OWNER)
        OrderClient.post(
            "/api/v1/Order/",
            {"customer": self.customer.pk, "items_input": [{"product": self.product.pk, "quantity": 9}]},
            format="json",
        )
        data = OrderClient.get(reverse("api_dashboard")).data
        self.assertEqual(data["total_orders"], 1)
        self.assertEqual(Decimal(str(data["total_sales"])), Decimal("225.00"))
        self.assertEqual(data["low_stock_count"], 1)  # 1 left <= threshold 2

    def test_forecast_needs_history_then_generates(self):
        owner = self.as_role(R.OWNER)
        self.assertEqual(owner.post(reverse("api_forecast_generate"), {}, format="json").status_code, 400)

        for days_ago, qty in ((3, 1), (2, 2), (1, 3)):
            order_id = owner.post(
                "/api/v1/Order/",
                {"customer": self.customer.pk, "items_input": [{"product": self.product.pk, "quantity": qty}]},
                format="json",
            ).data["id"]
            Order.objects.filter(pk=order_id).update(created_at=timezone.now() - timedelta(days=days_ago))

        res = owner.post(reverse("api_forecast_generate"), {"days": 5}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(len(res.data), 5)
        self.assertEqual(len(owner.get(reverse("api_forecasts")).data), 5)

    def test_staff_cannot_generate_forecast(self):
        self.assertEqual(self.as_role(R.STAFF).post(reverse("api_forecast_generate"), {}, format="json").status_code, 403)


class NotificationApiTests(ApiBase):
    def test_staff_can_mark_own_notifications_read(self):
        client = self.as_role(R.STAFF)
        client.post(
            "/api/v1/Order/",
            {"customer": self.customer.pk, "items_input": [{"product": self.product.pk, "quantity": 9}]},
            format="json",
        )
        # order + low-stock notifications were addressed to the staff user
        self.assertTrue(self.users[R.STAFF].notifications.filter(is_read=False).exists())
        res = client.post("/api/v1/Notification/mark-all-read/")
        self.assertEqual(res.status_code, 200, getattr(res, "content", ""))
        self.assertFalse(self.users[R.STAFF].notifications.filter(is_read=False).exists())
