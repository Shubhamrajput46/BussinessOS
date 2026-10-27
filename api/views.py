from decimal import Decimal

from django.db import transaction
from django.db.models import F, ProtectedError, Sum
from rest_framework import filters, status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from django_filters.rest_framework import DjangoFilterBackend

from .serilizer import (
    OrderStatusSerializer,
    ProductSerialiser,
    CustomerSerialiser,
    ExpenseSerialiser,
    inventorySerialiser,
    invoiceSerilisation,
    NotificationSerilisation,
    OrderSerilisation,
    OrganisationSerilisation,
    PaymentSerilisation,
    AccountSeriliser,
)

from .pagination import CustomPagination

from .filter import (
    ProductFilter,
    CustomerFilter,
    ExpenseFilter,
    InventoryFilter,
    InvoiceFilter,
    NotificationFilter,
    OrderFilter,
    OrganisationFilter,
    PaymentFilter,
    AccountFilter,
)

from .permissions import HasRolePermission
from common import roles as web_roles
from common.utils import monthly_totals
from apps.ai.models import SalesForecast
from apps.ai.services import generate_forecast
from apps.orders.services import OrderError, set_status
from apps.payments.services import sync_invoice_status

from apps.products.models import Product
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.inventory.models import InventoryTransaction
from apps.invoices.models import Invoice
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.accounts.models import User
from .throttles import (
    ProductThrottle,
    CustomerThrottle,
    ExpenseThrottle,
    InventoryThrottle,
    InvoiceThrottle,
    NotificationThrottle,
    OrderThrottle,
    OrganisationThrottle,
    PaymentThrottle,
    AccountThrottle,
    DashboardThrottle,
    ForecastThrottle,
)

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
# =========================================================
# PRODUCT
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Products",
        description="Returns products belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(
        summary="Get Product",
        description="Returns a single product from the user's organisation.",
    ),
    create=extend_schema(
        summary="Create Product",
        description="Creates a new product for the logged-in user's organisation.",
    ),
    update=extend_schema(
        summary="Update Product",
        description="Updates an existing product.",
    ),
    partial_update=extend_schema(
        summary="Partially Update Product",
        description="Updates selected fields of a product.",
    ),
    destroy=extend_schema(
        summary="Delete Product",
        description="Deletes a product from the user's organisation.",
    ),
)
class ProductViewSet(ModelViewSet):

    serializer_class = ProductSerialiser
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [ProductThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter
    ordering = ["-id"]
    search_fields = ["name", "sku"]
    ordering_fields = [
        "id",
        "name",
        "selling_price",
        "stock_quantity",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        return Product.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# CUSTOMER
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Customers",
        description="Returns customers belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(
        summary="Get Customer",
        description="Returns a single customer.",
    ),
    create=extend_schema(
        summary="Create Customer",
        description="Creates a customer for the logged-in user's organisation.",
    ),
    update=extend_schema(
        summary="Update Customer",
        description="Updates an existing customer.",
    ),
    partial_update=extend_schema(
        summary="Partially Update Customer",
        description="Updates selected customer fields.",
    ),
    destroy=extend_schema(
        summary="Delete Customer",
        description="Deletes a customer.",
    ),
)
class CustomerViewSet(ModelViewSet):

    serializer_class = CustomerSerialiser
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [CustomerThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = CustomerFilter
    ordering = ["-id"]
    search_fields = ["name", "phone"]
    ordering_fields = ["id", "name", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Customer.objects.none()
        return Customer.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# EXPENSE
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Expenses",
        description="Returns expenses belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Expense"),
    create=extend_schema(summary="Create Expense"),
    update=extend_schema(summary="Update Expense"),
    partial_update=extend_schema(summary="Partially Update Expense"),
    destroy=extend_schema(summary="Delete Expense"),
)
class ExpenseViewSet(ModelViewSet):

    serializer_class = ExpenseSerialiser
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [ExpenseThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.ACCOUNTANT,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ExpenseFilter
    ordering = ["-id"]
    search_fields = ["title", "category"]
    ordering_fields = [
        "amount",
        "expense_date",
        "created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Expense.objects.none()
        return Expense.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# INVENTORY
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Inventory Transactions",
        description="Returns inventory transactions for the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Inventory Transaction"),
    create=extend_schema(summary="Create Inventory Transaction"),
    update=extend_schema(summary="Update Inventory Transaction"),
    partial_update=extend_schema(
        summary="Partially Update Inventory Transaction"
    ),
    destroy=extend_schema(summary="Delete Inventory Transaction"),
)
class InventoryViewSet(ModelViewSet):

    serializer_class = inventorySerialiser
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [InventoryThrottle]
    # The stock ledger is append-only: rows are created (which moves stock) and read, never edited.
    http_method_names = ["get", "post", "head", "options"]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = InventoryFilter
    ordering = ["-id"]
    search_fields = [
        "transaction_type",
        "product__name",
    ]

    ordering_fields = [
        "quantity",
        "created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InventoryTransaction.objects.none()
        return InventoryTransaction.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# INVOICE
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Invoices",
        description="Returns invoices belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Invoice"),
    create=extend_schema(summary="Create Invoice"),
    update=extend_schema(summary="Update Invoice"),
    partial_update=extend_schema(summary="Partially Update Invoice"),
    destroy=extend_schema(summary="Delete Invoice"),
)
class InvoiceViewSet(ModelViewSet):

    serializer_class = invoiceSerilisation
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [InvoiceThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.ACCOUNTANT,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = InvoiceFilter
    ordering = ["-id"]
    search_fields = [
        "invoice_number",
        "status",
    ]

    ordering_fields = [
        "invoice_number",
        "status",
        "created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Invoice.objects.none()
        return Invoice.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# NOTIFICATION
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Notifications",
        description="Returns notifications belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Notification"),
    create=extend_schema(summary="Create Notification"),
    update=extend_schema(summary="Update Notification"),
    partial_update=extend_schema(summary="Partially Update Notification"),
    destroy=extend_schema(summary="Delete Notification"),
)
class NotificationViewSet(ModelViewSet):

    serializer_class = NotificationSerilisation
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [NotificationThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
            User.Role.ACCOUNTANT,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = NotificationFilter
    ordering = ["-id"]

    search_fields = [
        "notification_type",
        "user__username",
        "user__email",
    ]

    ordering_fields = [
        "created_at",
        "is_read",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )

    @extend_schema(summary="Mark Notification As Read", request=None, responses=NotificationSerilisation)
    @action(detail=True, methods=["post"], url_path="read", permission_classes=[IsAuthenticated])
    def mark_read(self, request, pk=None):
        notification = Notification.objects.filter(
            organisation=request.user.organisation, user=request.user, pk=pk
        ).first()
        if notification is None:
            raise ValidationError({"detail": "Notification not found."})
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerilisation(notification, context={"request": request}).data)

    @extend_schema(summary="Mark All My Notifications As Read", request=None, responses=None)
    @action(detail=False, methods=["post"], url_path="mark-all-read", permission_classes=[IsAuthenticated])
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            organisation=request.user.organisation, user=request.user, is_read=False
        ).update(is_read=True)
        return Response({"updated": updated})

# =========================================================
# ORDER
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Notifications",
        description="Returns notifications belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Notification"),
    create=extend_schema(summary="Create Notification"),
    update=extend_schema(summary="Update Notification"),
    partial_update=extend_schema(summary="Partially Update Notification"),
    destroy=extend_schema(summary="Delete Notification"),
)
class OrderViewSet(ModelViewSet):

    serializer_class = OrderSerilisation
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [OrderThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.STAFF,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = OrderFilter
    ordering = ["-id"]

    search_fields = [
        "order_number",
        "customer__name",
    ]

    ordering_fields = [
        "order_number",
        "status",
        "total_amount",
        "created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(
            organisation=self.request.user.organisation
        ).select_related("customer").prefetch_related("items__product")

    def perform_destroy(self, instance):
        if instance.status == Order.Status.COMPLETED:
            raise ValidationError({"detail": "Completed orders cannot be deleted."})
        try:
            with transaction.atomic():
                if instance.status != Order.Status.CANCELLED:
                    set_status(order=instance, new_status=Order.Status.CANCELLED, user=self.request.user)
                instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "This order has payments or an invoice and cannot be deleted."})
        except OrderError as exc:
            raise ValidationError({"detail": str(exc)})

    @extend_schema(
        request=OrderStatusSerializer,
        responses=OrderSerilisation,
        summary="Change Order Status",
        description="Moves an order through PENDING / CONFIRMED / COMPLETED / CANCELLED. Cancelling restores stock.",
    )
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, pk=None):
        if request.user.role not in web_roles.ORDER_EDIT:
            raise PermissionDenied("Your role is not allowed to change order status.")
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            set_status(order=order, new_status=serializer.validated_data["status"], user=request.user)
        except OrderError as exc:
            raise ValidationError({"detail": str(exc)})
        order.refresh_from_db()
        return Response(self.get_serializer(order).data)


# =========================================================
# ORGANISATION
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Organisation",
        description="Returns the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Organisation"),
    create=extend_schema(summary="Create Organisation"),
    update=extend_schema(summary="Update Organisation"),
    partial_update=extend_schema(summary="Partially Update Organisation"),
    destroy=extend_schema(summary="Delete Organisation"),
)
class OrganisationViewSet(ModelViewSet):

    serializer_class = OrganisationSerilisation
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [OrganisationThrottle]
    http_method_names = ["get", "put", "patch", "head", "options"]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
        "POST": [
            User.Role.OWNER,
        ],
        "PUT": [
            User.Role.OWNER,
        ],
        "PATCH": [
            User.Role.OWNER,
        ],
        "DELETE": [
            User.Role.OWNER,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = OrganisationFilter
    ordering = ["-id"]
    search_fields = ["name", "email"]
    ordering_fields = [
        "id",
        "name",
        "created_at",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organisation.objects.none()
        return Organisation.objects.filter(
            id=self.request.user.organisation_id
        )


# =========================================================
# PAYMENT
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Payments",
        description="Returns payments belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get Payment"),
    create=extend_schema(summary="Create Payment"),
    update=extend_schema(summary="Update Payment"),
    partial_update=extend_schema(summary="Partially Update Payment"),
    destroy=extend_schema(summary="Delete Payment"),
)
class PaymentViewSet(ModelViewSet):

    serializer_class = PaymentSerilisation
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [PaymentThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.ACCOUNTANT,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.ACCOUNTANT,
        ],
        "DELETE": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = PaymentFilter
    ordering = ["-id"]
    search_fields = ["method", "status"]

    ordering_fields = [
        "amount",
        "status",
        "payment_date",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        return Payment.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        payment = serializer.save(organisation=self.request.user.organisation)
        sync_invoice_status(payment.order)

    def perform_update(self, serializer):
        previous_order = serializer.instance.order
        payment = serializer.save()
        sync_invoice_status(payment.order)
        if previous_order.pk != payment.order_id:
            sync_invoice_status(previous_order)

    def perform_destroy(self, instance):
        order = instance.order
        instance.delete()
        sync_invoice_status(order)

# =========================================================
# ACCOUNT
# =========================================================
@extend_schema_view(
    list=extend_schema(
        summary="List Users",
        description="Returns users belonging to the logged-in user's organisation.",
    ),
    retrieve=extend_schema(summary="Get User"),
    create=extend_schema(summary="Create User"),
    update=extend_schema(summary="Update User"),
    partial_update=extend_schema(summary="Partially Update User"),
    destroy=extend_schema(summary="Delete User"),
)
class AccountViewSet(ModelViewSet):

    serializer_class = AccountSeriliser
    pagination_class = CustomPagination
    permission_classes = [HasRolePermission]
    throttle_classes = [AccountThrottle]

    role_permissions = {
        "GET": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
        "POST": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
        "PUT": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
        "PATCH": [
            User.Role.OWNER,
            User.Role.ADMIN,
        ],
        "DELETE": [
            User.Role.OWNER,
        ],
    }

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = AccountFilter
    ordering = ["-id"]

    search_fields = [
        "username",
        "email",
        "role",
    ]

    ordering_fields = [
        "id",
        "username",
        "role",
    ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return User.objects.filter(
            organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        serializer.save(
            organisation=self.request.user.organisation
        )


# =========================================================
# MY PROFILE
# =========================================================
class MyProfileView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="My Profile",
        description="Returns the profile of the currently authenticated user.",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):

        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "phone": request.user.phone,
            "role": request.user.role,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "organisation": request.user.organisation_id,
            "organisation_name": request.user.organisation.name if request.user.organisation else None,
        })

# class LoginTokenView(TokenObtainPairView):
#     throttle_classes = [LoginThrottle]

# =========================================================
# DASHBOARD SUMMARY
# =========================================================
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [DashboardThrottle]

    @extend_schema(
        summary="Dashboard Summary",
        description="KPI totals and monthly revenue for the user's organisation.",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        org = request.user.organisation
        if org is None:
            raise PermissionDenied("This account is not attached to an organisation.")

        valid_orders = Order.objects.filter(organisation=org).exclude(status=Order.Status.CANCELLED)
        total_sales = valid_orders.aggregate(t=Sum("total_amount"))["t"] or Decimal("0.00")
        total_expenses = (
            Expense.objects.filter(organisation=org, is_active=True).aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        )
        total_payments = (
            Payment.objects.filter(organisation=org, status=Payment.Status.PAID).aggregate(t=Sum("amount"))["t"]
            or Decimal("0.00")
        )
        low_stock = Product.objects.filter(
            organisation=org, is_active=True, stock_quantity__lte=F("low_stock_threshold")
        )
        monthly = monthly_totals(valid_orders, "created_at", "total_amount")

        return Response(
            {
                "organisation": org.name,
                "total_sales": total_sales,
                "total_orders": valid_orders.count(),
                "total_customers": Customer.objects.filter(organisation=org, is_active=True).count(),
                "total_products": Product.objects.filter(organisation=org, is_active=True).count(),
                "total_expenses": total_expenses,
                "total_payments_received": total_payments,
                "profit": total_sales - total_expenses,
                "low_stock_count": low_stock.count(),
                "low_stock_products": list(
                    low_stock.order_by("stock_quantity").values("id", "name", "sku", "stock_quantity", "low_stock_threshold")[:10]
                ),
                "unread_notifications": request.user.notifications.filter(is_read=False).count(),
                "monthly_sales": [
                    {"month": m["month"].strftime("%Y-%m"), "total": m["total"]} for m in monthly
                ],
            }
        )


# =========================================================
# AI SALES FORECAST
# =========================================================
class ForecastView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ForecastThrottle]

    @extend_schema(summary="List Sales Forecasts", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        rows = SalesForecast.objects.filter(organisation=request.user.organisation).order_by("forecast_date")
        return Response(
            [{"forecast_date": r.forecast_date, "predicted_sales": r.predicted_sales} for r in rows[:90]]
        )


class ForecastGenerateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ForecastThrottle]

    @extend_schema(
        summary="Generate Sales Forecast",
        description="Runs the linear-regression forecast for the next N days (default 7, max 30).",
        request={"application/json": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}},
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request):
        if request.user.role not in web_roles.OWNER_ADMIN_MANAGER:
            raise PermissionDenied("Your role is not allowed to generate forecasts.")
        try:
            days = int(request.data.get("days", 7))
        except (TypeError, ValueError):
            raise ValidationError({"days": "Must be a whole number."})
        created = generate_forecast(request.user.organisation, days=days)
        if not created:
            raise ValidationError({"detail": "Not enough sales history yet (need orders on at least two days)."})
        return Response(
            [{"forecast_date": r.forecast_date, "predicted_sales": r.predicted_sales} for r in created],
            status=http_status.HTTP_201_CREATED,
        )
