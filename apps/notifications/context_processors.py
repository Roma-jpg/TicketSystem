from .models import Notification


def notification_context(request):
    if not request.user.is_authenticated:
        return {}
    unread_count = Notification.objects.filter(
        recipient=request.user,
        read=False,
    ).count()
    return {
        "unread_count": unread_count,
    }
