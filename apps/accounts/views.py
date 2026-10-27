from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from common import roles
from common.permissions import role_required
from common.utils import monthly_totals

from apps.accounts.models import User
from apps.ai.models import SalesForecast
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.orders.models import Order
from apps.organizations.models import Organisation
from apps.payments.models import Payment
from apps.products.models import Product


def home(request):
    return render(request, "index.html")


def _password_error(password, user=None):
    try:
        validate_password(password, user)
    except ValidationError as exc:
        return " ".join(exc.messages)
    return None


# ==========================================
# SIGNUP / LOGIN / LOGOUT
# ==========================================
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    context = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        organisation_name = request.POST.get("organisation_name", "").strip()
        context["posted"] = request.POST

        error = None
        if not (username and email and password and organisation_name):
            error = "All fields are required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = "Enter a valid email address."
        if not error and User.objects.filter(username__iexact=username).exists():
            error = "Username already exists."
        if not error and (
            User.objects.filter(email=email).exists() or Organisation.objects.filter(email=email).exists()
        ):
            error = "Email already exists."
        if not error:
            error = _password_error(password, User(username=username, email=email))

        if error:
            context["error"] = error
        else:
            organisation = Organisation.objects.create(name=organisation_name, email=email)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                organisation=organisation,
                role=User.Role.OWNER,
            )
            login(request, user)
            return redirect("dashboard")

    return render(request, "signup.html", context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    context = {"next": next_url}

    if request.method == "POST":
        identifier = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        account = User.objects.filter(Q(email=identifier) | Q(username__iexact=identifier)).first()
        user = authenticate(request, username=account.username, password=password) if account else None

        if user is not None:
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")

        context["error"] = "Invalid email or password."
        context["posted"] = request.POST

    return render(request, "login.html", context)


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


# ==========================================
# DASHBOARD
# ==========================================
@login_required
def dashboard_view(request):
    organisation = request.user.organisation

    orders = Order.objects.filter(organisation=organisation)
    valid_orders = orders.exclude(status=Order.Status.CANCELLED)

    total_orders = valid_orders.count()
    total_sales = valid_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_customers = Customer.objects.filter(organisation=organisation, is_active=True).count()
    total_products = Product.objects.filter(organisation=organisation, is_active=True).count()

    low_stock_products = Product.objects.filter(
        organisation=organisation, is_active=True, stock_quantity__lte=F("low_stock_threshold")
    ).order_by("stock_quantity")

    total_expenses = (
        Expense.objects.filter(organisation=organisation, is_active=True).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    total_payments = (
        Payment.objects.filter(organisation=organisation, status=Payment.Status.PAID).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    recent_payments = (
        Payment.objects.filter(organisation=organisation)
        .select_related("order", "order__customer")
        .order_by("-payment_date")[:5]
    )
    recent_orders = valid_orders.select_related("customer").order_by("-created_at")[:5]

    latest_forecast = (
        SalesForecast.objects.filter(organisation=organisation, forecast_date__gte=date.today())
        .order_by("forecast_date")
        .first()
    )

    # Real monthly revenue for the chart (last 6 months that have data)
    monthly = monthly_totals(valid_orders, "created_at", "total_amount")[-6:]
    chart = {
        "labels": [m["month"].strftime("%b %Y") for m in monthly],
        "values": [float(m["total"] or 0) for m in monthly],
    }

    context = {
        "organisation": organisation,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "total_expenses": total_expenses,
        "total_payments": total_payments,
        "profit": total_sales - total_expenses,
        "low_stock_count": low_stock_products.count(),
        "low_stock_products": low_stock_products[:6],
        "recent_orders": recent_orders,
        "recent_payments": recent_payments,
        "latest_forecast": latest_forecast,
        "chart_json": chart,
        "has_chart": bool(chart["labels"]),
        "unread_notifications": request.user.notifications.filter(is_read=False).count(),
    }
    return render(request, "dashboard.html", context)


# ==========================================
# PROFILE (any logged-in user)
# ==========================================
@login_required
def profile_view(request):
    user = request.user
    password_form = PasswordChangeForm(user)
    context = {}

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "details":
            email = request.POST.get("email", "").strip().lower()
            try:
                validate_email(email)
            except ValidationError:
                context["error"] = "Enter a valid email address."
            else:
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    context["error"] = "Email already exists."
                else:
                    user.email = email
                    user.first_name = request.POST.get("first_name", "").strip()
                    user.last_name = request.POST.get("last_name", "").strip()
                    user.phone = request.POST.get("phone", "").strip()
                    user.save(update_fields=["email", "first_name", "last_name", "phone"])
                    messages.success(request, "Profile updated.")
                    return redirect("profile")

        elif action == "password":
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed.")
                return redirect("profile")
            context["password_errors"] = [
                msg for errors in password_form.errors.values() for msg in errors
            ]

    context["password_form"] = password_form
    return render(request, "profile.html", context)


# ==========================================
# TEAM MANAGEMENT (OWNER / ADMIN)
# ==========================================
def _team_member(request, pk):
    return get_object_or_404(User, pk=pk, organisation=request.user.organisation)


def _admin_blocked(request, target):
    """ADMIN users can never touch OWNER accounts."""
    return request.user.role == User.Role.ADMIN and target.role == User.Role.OWNER


@login_required
@role_required(*roles.OWNER_ADMIN)
def user_list(request):
    users = User.objects.filter(organisation=request.user.organisation).order_by("-date_joined")
    return render(request, "user_list.html", {"users": users})


@login_required
@role_required(*roles.OWNER_ADMIN)
def user_create(request):
    context = {"roles": User.Role.choices}

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", User.Role.STAFF)
        context["posted"] = request.POST

        error = None
        if not (username and email and password):
            error = "Username, email and password are required."
        elif User.objects.filter(username__iexact=username).exists():
            error = "Username already exists."
        elif User.objects.filter(email=email).exists():
            error = "Email already exists."
        elif role not in User.Role.values:
            error = "Invalid role selected."
        elif request.user.role == User.Role.ADMIN and role == User.Role.OWNER:
            error = "Admin cannot create an Owner."
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = "Enter a valid email address."
        if not error:
            error = _password_error(password, User(username=username, email=email))

        if error:
            context["error"] = error
        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                phone=phone,
                organisation=request.user.organisation,
                role=role,
            )
            messages.success(request, f"User {username} created successfully.")
            return redirect("user_list")

    return render(request, "user_form.html", context)


@login_required
@role_required(*roles.OWNER_ADMIN)
def user_edit(request, pk):
    user = _team_member(request, pk)
    if _admin_blocked(request, user):
        messages.error(request, "Admins cannot edit the Owner.")
        return redirect("user_list")

    context = {"user_obj": user, "roles": User.Role.choices}

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", User.Role.STAFF)
        context["posted"] = request.POST

        error = None
        if role not in User.Role.values:
            error = "Invalid role selected."
        elif request.user.role == User.Role.ADMIN and role == User.Role.OWNER:
            error = "Admin cannot assign the Owner role."
        elif user.pk == request.user.pk and role != user.role:
            error = "You cannot change your own role."
        elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
            error = "Email already exists."
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = "Enter a valid email address."

        if error:
            context["error"] = error
        else:
            user.email, user.phone, user.role = email, phone, role
            user.save(update_fields=["email", "phone", "role"])
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect("user_list")

    return render(request, "user_form.html", context)


@login_required
@role_required(*roles.OWNER_ADMIN)
def user_toggle_status(request, pk):
    user = _team_member(request, pk)

    if request.method != "POST":
        return redirect("user_list")
    if user.pk == request.user.pk:
        messages.error(request, "You cannot deactivate yourself.")
    elif _admin_blocked(request, user):
        messages.error(request, "Admins cannot deactivate the Owner.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"User {user.username} status updated.")
    return redirect("user_list")


@login_required
@role_required(*roles.OWNER_ADMIN)
def user_delete(request, pk):
    user = _team_member(request, pk)

    if user.pk == request.user.pk:
        messages.error(request, "You cannot delete yourself.")
        return redirect("user_list")
    if _admin_blocked(request, user):
        messages.error(request, "Admins cannot delete the Owner.")
        return redirect("user_list")

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully.")
        return redirect("user_list")

    return render(request, "user_delete.html", {"user_obj": user})
