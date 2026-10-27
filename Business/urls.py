from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path


from apps.accounts.views import (
    dashboard_view,
    login_view,
    logout_view,
    signup_view,
)

def health(request):
    from django.db import connection

    connection.ensure_connection()
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Forgot / reset password
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"), name="password_reset_complete"),

    # Admin
    path("admin/", admin.site.urls),
    
    
    # Authentication
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    # Dashboard
    path("dashboard/", dashboard_view, name="dashboard"),

    # Accounts / User Management
    path("", include("apps.accounts.urls")),

    # Products
    path("products/", include("apps.products.urls")),

    # Inventory
    path("inventory/", include("apps.inventory.urls")),

    # Customers
    path("customers/", include("apps.customers.urls")),

    # Orders
    path("orders/", include("apps.orders.urls")),

    # Expenses
    path("expenses/", include("apps.expenses.urls")),

    # Payments
    path("payments/", include("apps.payments.urls")),

    # Invoices
    path("invoices/", include("apps.invoices.urls")),

    # Notifications
    path("notifications/", include("apps.notifications.urls")),

    # Analytics
    path("analytics/", include("apps.analytics.urls")),
    
    # AI forecasts
    path("ai/", include("apps.ai.urls")),

    # Organisation settings
    path("", include("apps.organizations.urls")),

    # Health check (used by Docker / load balancers)
    path("health/", health, name="health"),

    path("api/v1/", include("api.urls")),
]