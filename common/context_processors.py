from django.db.models import F


def sidebar_counts(request):
    """Counters shown in the shared sidebar on every authenticated page."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not getattr(user, "organisation_id", None):
        return {}

    from apps.products.models import Product

    from common import roles

    role = user.role
    return {
        "nav": {
            "orders": role in roles.ORDER_VIEW,
            "products": True,
            "inventory": role in roles.INVENTORY,
            "customers": True,
            "finance": role in roles.FINANCE_VIEW,
            "team": role in roles.OWNER_ADMIN,
            "settings": role in roles.OWNER_ADMIN,
        },
        "unread_notifications": user.notifications.filter(is_read=False).count(),
        "low_stock_count": Product.objects.filter(
            organisation_id=user.organisation_id,
            is_active=True,
            stock_quantity__lte=F("low_stock_threshold"),
        ).count(),
    }
