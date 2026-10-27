"""Small, dependency-free parsing helpers for HTML form input."""
from datetime import date
from decimal import Decimal, InvalidOperation


class FormError(Exception):
    """Raised by the parse_* helpers; the message is shown to the user."""


def parse_decimal(value, label, *, minimum=None, required=True, default=Decimal("0.00")):
    value = (value or "").strip() if isinstance(value, str) else value
    if value in (None, ""):
        if required:
            raise FormError(f"{label} is required.")
        return default
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise FormError(f"{label} must be a valid number.")
    if not number.is_finite():
        raise FormError(f"{label} must be a valid number.")
    if minimum is not None and number < minimum:
        raise FormError(f"{label} must be at least {minimum}.")
    return number.quantize(Decimal("0.01"))


def parse_int(value, label, *, minimum=0, required=True, default=0):
    value = (value or "").strip() if isinstance(value, str) else value
    if value in (None, ""):
        if required:
            raise FormError(f"{label} is required.")
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise FormError(f"{label} must be a whole number.")
    if minimum is not None and number < minimum:
        raise FormError(f"{label} must be at least {minimum}.")
    return number


def parse_date(value, label, *, required=True):
    value = (value or "").strip() if isinstance(value, str) else value
    if not value:
        if required:
            raise FormError(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise FormError(f"{label} must be a valid date (YYYY-MM-DD).")


def require_text(value, label, *, max_length=None):
    value = (value or "").strip()
    if not value:
        raise FormError(f"{label} is required.")
    if max_length and len(value) > max_length:
        raise FormError(f"{label} must be at most {max_length} characters.")
    return value


def paginate(request, queryset, per_page=15):
    """Return a Page for ?page=N (invalid pages fall back to the nearest valid one)."""
    from django.core.paginator import Paginator

    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def querystring_without_page(request):
    """Current GET params minus 'page' – used by the pagination partial."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def monthly_totals(queryset, date_field, amount_field):
    """Sum `amount_field` per calendar month, grouped in Python.

    Returns [{"month": date(YYYY, MM, 1), "total": Decimal}, ...] oldest first.
    Done in Python (not TruncMonth) so it works on SQLite and on MySQL even
    when the database has no time-zone tables loaded (common on Windows).
    """
    from collections import defaultdict
    from datetime import date, datetime

    from django.utils import timezone

    totals = defaultdict(lambda: Decimal("0.00"))
    for value, amount in queryset.values_list(date_field, amount_field):
        if value is None:
            continue
        if isinstance(value, datetime):
            if timezone.is_aware(value):
                value = timezone.localtime(value)
            value = value.date()
        totals[date(value.year, value.month, 1)] += amount or Decimal("0.00")
    return [{"month": m, "total": totals[m]} for m in sorted(totals)]
