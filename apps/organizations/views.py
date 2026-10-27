from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render

from common import roles
from common.permissions import role_required

from .models import Organisation


@login_required
@role_required(*roles.OWNER_ADMIN)
def organisation_settings(request):
    organisation = request.user.organisation
    context = {"organisation": organisation}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        try:
            if not name:
                raise ValidationError("Organisation name is required.")
            validate_email(email)
            if Organisation.objects.filter(email=email).exclude(pk=organisation.pk).exists():
                raise ValidationError("Another organisation already uses this email.")
        except ValidationError as exc:
            context.update(error=" ".join(exc.messages), posted=request.POST)
        else:
            organisation.name = name
            organisation.email = email
            organisation.phone = request.POST.get("phone", "").strip()
            organisation.address = request.POST.get("address", "").strip()
            organisation.save()
            messages.success(request, "Organisation settings saved.")
            return redirect("organisation_settings")

    return render(request, "organisation_settings.html", context)
