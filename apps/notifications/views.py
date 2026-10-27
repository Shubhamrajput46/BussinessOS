from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from common.utils import paginate, querystring_without_page

from .models import Notification


def _mine(request):
    return Notification.objects.filter(organisation=request.user.organisation, user=request.user)


@login_required
def notification_list(request):
    notifications = _mine(request).order_by("-created_at")
    show = request.GET.get("show", "")
    if show == "unread":
        notifications = notifications.filter(is_read=False)

    page = paginate(request, notifications)
    return render(
        request,
        "notification_list.html",
        {
            "page_obj": page,
            "notifications": page.object_list,
            "show": show,
            "unread_total": _mine(request).filter(is_read=False).count(),
            "qs": querystring_without_page(request),
        },
    )


@login_required
def notification_detail(request, pk):
    notification = get_object_or_404(_mine(request), pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return render(request, "notification_detail.html", {"notification": notification})


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(_mine(request), pk=pk)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect("notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    _mine(request).filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notification_list")


@login_required
def notification_delete(request, pk):
    notification = get_object_or_404(_mine(request), pk=pk)
    if request.method == "POST":
        notification.delete()
        messages.success(request, "Notification deleted.")
        return redirect("notification_list")
    return render(request, "notification_delete.html", {"notification": notification})
