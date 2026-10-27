from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.inventory.models import InventoryTransaction
from apps.inventory.services import StockError, apply_transaction
from apps.invoices.models import Invoice
from apps.notifications.models import Notification
from apps.orders.models import Order, OrderItem
from apps.orders.services import OrderError, create_order, update_order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.products.models import Product


def _request_org_id(serializer):
    request = serializer.context.get("request")
    return request.user.organisation_id if request and request.user.is_authenticated else None


# =========================================================
# PRODUCT
# =========================================================
class ProductSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["id", "organisation", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Product name cannot be empty.")
        return value.strip()

    def validate_sku(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("SKU cannot be empty.")
        organisation_id = _request_org_id(self)
        duplicate = Product.objects.filter(organisation_id=organisation_id, sku__iexact=value)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate_cost_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Cost price cannot be negative.")
        return value

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Selling price cannot be negative.")
        return value

    def validate(self, data):
        cost = data.get("cost_price", getattr(self.instance, "cost_price", None))
        selling = data.get("selling_price", getattr(self.instance, "selling_price", None))
        if cost is not None and selling is not None and selling < cost:
            raise serializers.ValidationError("Selling price cannot be lower than cost price.")
        return data


# =========================================================
# CUSTOMER
# =========================================================
class CustomerSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["id", "organisation", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Customer name cannot be empty.")
        return value.strip()

    def validate_email(self, value):
        return value.lower().strip()

    def validate_phone(self, value):
        value = value.strip()
        if value and not value.replace("+", "").isdigit():
            raise serializers.ValidationError("Phone number must contain only numbers.")
        return value


# =========================================================
# EXPENSE
# =========================================================
class ExpenseSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ["id", "organisation", "created_at", "updated_at"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Expense title cannot be empty.")
        return value.strip()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value


# =========================================================
# INVENTORY  (ledger: create + read only; creating moves real stock)
# =========================================================
class inventorySerialiser(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = InventoryTransaction
        fields = "__all__"
        read_only_fields = ["id", "organisation", "created_at"]

    def validate_product(self, product):
        if product.organisation_id != _request_org_id(self):
            raise serializers.ValidationError("You cannot use a product from another organisation.")
        return product

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Inventory quantity must be greater than zero.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return apply_transaction(
                organisation=request.user.organisation,
                product=validated_data["product"],
                transaction_type=validated_data["transaction_type"],
                quantity=validated_data["quantity"],
                note=validated_data.get("note", ""),
                user=request.user,
            )
        except StockError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


# =========================================================
# ORDER ITEM / ORDER
# =========================================================
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "unit_price", "total_price"]
        read_only_fields = fields


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerilisation(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    items = OrderItemSerializer(many=True, read_only=True)
    items_input = OrderItemInputSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text='[{"product": 1, "quantity": 2}] - stock is reserved automatically.',
    )

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = [
            "id", "organisation", "order_number", "status",
            "subtotal", "total_amount", "created_at", "updated_at",
        ]

    def validate_customer(self, customer):
        if customer.organisation_id != _request_org_id(self):
            raise serializers.ValidationError("You cannot use a customer from another organisation.")
        return customer

    def validate(self, data):
        for field in ("discount", "tax"):
            if data.get(field) is not None and data[field] < 0:
                raise serializers.ValidationError(f"{field.capitalize()} cannot be negative.")
        if self.instance is None and not data.get("items_input"):
            raise serializers.ValidationError({"items_input": "At least one item is required."})
        return data

    @staticmethod
    def _pairs(items):
        return [(i["product"], i["quantity"]) for i in items]

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return create_order(
                organisation=request.user.organisation,
                customer=validated_data["customer"],
                items=self._pairs(validated_data["items_input"]),
                user=request.user,
                discount=validated_data.get("discount", 0),
                tax=validated_data.get("tax", 0),
            )
        except OrderError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def update(self, instance, validated_data):
        request = self.context["request"]
        items = validated_data.get("items_input")
        try:
            if items is None:
                items = [(i.product_id, i.quantity) for i in instance.items.all()]
            else:
                items = self._pairs(items)
            return update_order(
                order=instance,
                customer=validated_data.get("customer", instance.customer),
                items=items,
                user=request.user,
                discount=validated_data.get("discount"),
                tax=validated_data.get("tax"),
            )
        except OrderError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


# =========================================================
# INVOICE
# =========================================================
class invoiceSerilisation(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = [
            "id", "organisation", "invoice_number", "issue_date", "created_at", "updated_at",
            "subtotal", "discount", "tax", "total_amount",
        ]

    def validate_order(self, order):
        if order.organisation_id != _request_org_id(self):
            raise serializers.ValidationError("You cannot create an invoice for another organisation's order.")
        if order.status == Order.Status.CANCELLED:
            raise serializers.ValidationError("Cannot invoice a cancelled order.")
        existing = Invoice.objects.filter(order=order)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("This order already has an invoice.")
        return order

    def create(self, validated_data):
        order = validated_data["order"]
        validated_data.update(
            subtotal=order.subtotal, discount=order.discount, tax=order.tax, total_amount=order.total_amount
        )
        validated_data.setdefault("status", Invoice.Status.ISSUED)
        return super().create(validated_data)


# =========================================================
# NOTIFICATION
# =========================================================
class NotificationSerilisation(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "organisation", "created_at"]

    def validate_user(self, user):
        if user.organisation_id != _request_org_id(self):
            raise serializers.ValidationError("You cannot create a notification for another organisation's user.")
        return user


# =========================================================
# ORGANISATION
# =========================================================
class OrganisationSerilisation(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Organisation name cannot be empty.")
        return value.strip()

    def validate_email(self, value):
        return value.lower().strip()


# =========================================================
# PAYMENT
# =========================================================
class PaymentSerilisation(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "organisation", "payment_date", "created_at", "updated_at"]

    def validate_order(self, order):
        if order.organisation_id != _request_org_id(self):
            raise serializers.ValidationError("You cannot create a payment for another organisation's order.")
        if order.status == Order.Status.CANCELLED:
            raise serializers.ValidationError("Cannot take a payment for a cancelled order.")
        return order

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value


# =========================================================
# ACCOUNT / USER
# =========================================================
class AccountSeriliser(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "password", "phone", "role",
            "organisation", "first_name", "last_name", "is_active",
        ]
        read_only_fields = ["id", "organisation"]

    def validate_email(self, value):
        value = value.lower().strip()
        duplicate = User.objects.filter(email=value)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_role(self, value):
        actor = self.context["request"].user
        if value == User.Role.OWNER and actor.role != User.Role.OWNER:
            raise serializers.ValidationError("Only an Owner can assign the Owner role.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, data):
        actor = self.context["request"].user
        if self.instance is not None:
            if self.instance.role == User.Role.OWNER and actor.role != User.Role.OWNER:
                raise serializers.ValidationError("Only an Owner can modify an Owner account.")
            if self.instance.pk == actor.pk and "role" in data and data["role"] != actor.role:
                raise serializers.ValidationError("You cannot change your own role.")
            if self.instance.pk == actor.pk and data.get("is_active") is False:
                raise serializers.ValidationError("You cannot deactivate yourself.")
        elif not data.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
