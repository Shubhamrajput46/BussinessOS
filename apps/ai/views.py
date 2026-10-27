from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from common import roles
from common.permissions import role_required

from apps.ai.models import SalesForecast
from apps.ai.services import generate_forecast


@login_required
def forecast_list(request):
    forecasts = SalesForecast.objects.filter(organisation=request.user.organisation).order_by("-forecast_date")
    return render(
        request,
        "forecast_list.html",
        {
            "forecasts": forecasts[:60],
            "can_generate": request.user.role in roles.OWNER_ADMIN_MANAGER,
        },
    )


@login_required
@role_required(*roles.OWNER_ADMIN_MANAGER)
@require_POST
def forecast_generate(request):
    try:
        days = int(request.POST.get("days", 7))
    except ValueError:
        days = 7
    created = generate_forecast(request.user.organisation, days=days)
    if created:
        messages.success(request, f"Generated a {len(created)}-day sales forecast.")
    else:
        messages.error(request, "Not enough sales history yet. Create orders on at least two different days.")
    return redirect("forecast_list")
