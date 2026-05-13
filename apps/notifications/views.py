import json
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import Notification


@require_GET
@login_required
def notification_list_api(request):
    """
    Returns two lists:
      - unread:  sorted by -created_at
      - read:    sorted by -read_at (i.e., most recently read first)
    Pagination is applied to the combined set, but we return all unread plus the requested page of read.
    Simpler: we return all unread (they are usually few) and paginate the read list.
    """
    unread_qs = (
        Notification.objects
        .filter(recipient=request.user, read=False)
        .select_related("ticket", "triggered_by")
        .order_by("-created_at")
    )
    read_qs = (
        Notification.objects
        .filter(recipient=request.user, read=True)
        .select_related("ticket", "triggered_by")
        .order_by("-read_at")
    )

    # Paginate only the read ones (the user may have many)
    page_number = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 5)
    paginator = Paginator(read_qs, page_size)
    read_page = paginator.get_page(page_number)

    data = {
        "unread": [
            {
                "id": n.id,
                "message": n.message,
                "ticket_pk": str(n.ticket.pk),
                "created_at": n.created_at.isoformat(),
                "read": False,
            }
            for n in unread_qs
        ],
        "read": [
            {
                "id": n.id,
                "message": n.message,
                "ticket_pk": str(n.ticket.pk),
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "read": True,
            }
            for n in read_page
        ],
        "has_next": read_page.has_next(),
        "page": read_page.number,
        "unread_count": unread_qs.count(),
    }
    return JsonResponse(data)


@require_POST
@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.read:
        notif.read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["read", "read_at"])

    unread_count = Notification.objects.filter(
        recipient=request.user, read=False
    ).count()
    return JsonResponse({"success": True, "unread_count": unread_count})