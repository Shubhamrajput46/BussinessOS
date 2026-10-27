import django_filters
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

class ProductFilter(django_filters.FilterSet):
    class Meta:
        model=Product
        fields=['name','sku','is_active']


class CustomerFilter(django_filters.FilterSet):
    class Meta:
        model=Customer
        fields=['name','phone','is_active']

class ExpenseFilter(django_filters.FilterSet):
    class Meta:
        model=Expense
        fields=['category','amount','is_active']


class InventoryFilter(django_filters.FilterSet):
    class Meta:
        model=InventoryTransaction
        fields=['transaction_type','product']


class InvoiceFilter(django_filters.FilterSet):
    class Meta:
        model=Invoice
        fields=['invoice_number','status','order']

class NotificationFilter(django_filters.FilterSet):
    class Meta:
        model=Notification
        fields=['notification_type','user','is_read']


class OrderFilter(django_filters.FilterSet):
    class Meta:
        model=Order
        fields=['order_number','status','customer']


class OrganisationFilter(django_filters.FilterSet):
    class Meta:
        model=Organisation
        fields=[ 'name','email']


class PaymentFilter(django_filters.FilterSet):
    class Meta:
        model=Payment
        fields=[ 'method','status','order']


class AccountFilter(django_filters.FilterSet):
    class Meta:
        model=User
        fields=[ 'role','email']
