from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class ProductThrottle(UserRateThrottle):
    scope = "product"


class CustomerThrottle(UserRateThrottle):
    scope = "customer"


class ExpenseThrottle(UserRateThrottle):
    scope = "expense"


class InventoryThrottle(UserRateThrottle):
    scope = "inventory"


class InvoiceThrottle(UserRateThrottle):
    scope = "invoice"


class NotificationThrottle(UserRateThrottle):
    scope = "notification"


class OrderThrottle(UserRateThrottle):
    scope = "order"


class OrganisationThrottle(UserRateThrottle):
    scope = "organisation"


class PaymentThrottle(UserRateThrottle):
    scope = "payment"


class AccountThrottle(UserRateThrottle):
    scope = "account"


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class DashboardThrottle(UserRateThrottle):
    scope = "dashboard"


class ForecastThrottle(UserRateThrottle):
    scope = "forecast"