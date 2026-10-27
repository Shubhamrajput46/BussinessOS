from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.simple_tag
def fv(posted, obj, name, default=""):
    """Form value: posted data wins, then the object's attribute, then the default."""
    if posted:
        return posted.get(name, "")
    if obj is not None:
        value = getattr(obj, name, default)
        return default if value is None else value
    return default


@register.simple_tag
def fchk(posted, obj, name, default=True):
    """'checked' for a checkbox, honouring posted data, then the object, then the default."""
    if posted:
        return "checked" if posted.get(name) == "on" else ""
    if obj is not None:
        return "checked" if getattr(obj, name, default) else ""
    return "checked" if default else ""


@register.simple_tag
def fsel(posted, obj, name, option, default=""):
    """'selected' for the <option> whose value equals the current value."""
    current = fv(posted, obj, name, default)
    return "selected" if str(current) == str(option) else ""


@register.filter
def inr(value):
    """Format as Indian rupees with lakh/crore grouping: 1234567.5 -> ₹12,34,567.50"""
    try:
        number = Decimal(str(value if value not in (None, "") else 0))
    except InvalidOperation:
        return value
    negative = number < 0
    whole, _, frac = f"{abs(number):.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    if head:
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        tail = ",".join(groups) + "," + tail
    return f"{'-' if negative else ''}₹{tail}.{frac}"


BADGES = {
    "COMPLETED": "success", "PAID": "success", "SUCCESS": "success", "ACTIVE": "success",
    "STOCK_IN": "success", "OWNER": "info",
    "CONFIRMED": "info", "ISSUED": "info", "INFO": "info", "ADMIN": "info", "MANAGER": "info",
    "PENDING": "warning", "PARTIAL": "warning", "WARNING": "warning", "ADJUSTMENT": "warning",
    "CANCELLED": "danger", "FAILED": "danger", "ERROR": "danger", "STOCK_OUT": "danger", "INACTIVE": "danger",
}


@register.filter
def badge(value):
    """CSS class for a status/role value: {{ order.status|badge }} -> 'badge badge-success'"""
    kind = BADGES.get(str(value).upper(), "")
    return f"badge badge-{kind}" if kind else "badge"


@register.filter
def initial(value):
    value = str(value or "?").strip()
    return value[:1].upper() or "?"
