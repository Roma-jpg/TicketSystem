# apps/notifications/context_processors.py
from .models import Notification


def notification_context(request):
    if not request.user.is_authenticated:
        return {}
    notifications = Notification.objects.filter(
        recipient=request.user,
        read=False,
    )
    recent = notifications.select_related("ticket", "triggered_by").order_by("-created_at")[:5]
    return {
        "unread_count": notifications.count(),
        "recent_notifications": recent,
    }