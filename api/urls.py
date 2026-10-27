from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .auth import LoginTokenView

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

router = DefaultRouter()

router.register(
    r"Product",
    views.ProductViewSet,
    basename="product"
)

router.register(
    r"Customer",
    views.CustomerViewSet,
    basename="customer"
)

router.register(
    r"Expense",
    views.ExpenseViewSet,
    basename="expense"
)

router.register(
    r"Inventory",
    views.InventoryViewSet,
    basename="inventory"
)

router.register(
    r"Invoice",
    views.InvoiceViewSet,
    basename="invoice"
)

router.register(
    r"Notification",
    views.NotificationViewSet,
    basename="notification"
)

router.register(
    r"Order",
    views.OrderViewSet,
    basename="order"
)

router.register(
    r"Organisation",
    views.OrganisationViewSet,
    basename="organisation"
)

router.register(
    r"Payment",
    views.PaymentViewSet,
    basename="payment"
)

router.register(
    r"Account",
    views.AccountViewSet,
    basename="account"
)


urlpatterns = [
    path("token/", LoginTokenView.as_view(), name="token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("profile/", views.MyProfileView.as_view(), name="api_profile"),
    path("dashboard/", views.DashboardView.as_view(), name="api_dashboard"),
    path("forecasts/", views.ForecastView.as_view(), name="api_forecasts"),
    path("forecasts/generate/", views.ForecastGenerateView.as_view(), name="api_forecast_generate"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/",SpectacularSwaggerView.as_view(url_name="schema"),name="swagger-ui",),
    path("redoc/",SpectacularRedocView.as_view(url_name="schema"),name="redoc"),
]

urlpatterns += router.urls
