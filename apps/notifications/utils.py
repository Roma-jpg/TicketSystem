# apps/notifications/utils.py
import logging
import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(settings.REDIS_URL)


def create_notification(recipient_id, ticket, notif_type, message, triggered_by=None):
    """
    Create a Notification and handle real‑time logic gracefully.
    If Redis is down, the notification is still saved – the user will see it
    on the next page load or bell open.
    """
    if triggered_by and recipient_id == triggered_by.pk:
        return None

    notif = Notification.objects.create(
        recipient_id=recipient_id,
        ticket=ticket,
        notification_type=notif_type,
        message=message,
        triggered_by=triggered_by,
    )

    # ---- Presence check (graceful fallback) ----
    is_viewing = False
    try:
        presence_key = f"viewing_ticket:{ticket.pk}"
        is_viewing = redis_client.sismember(presence_key, recipient_id)
    except redis.ConnectionError:
        logger.warning("Redis unavailable – treating user as offline.")
    except Exception:
        logger.exception("Unexpected error during Redis presence check.")

    if is_viewing:
        notif.read = True
        notif.read_at = timezone.now()  # ← add
        notif.save(update_fields=["read", "read_at"])
    else:
        # Push bell update via channel layer (also guarded)
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                user_group = f"notifications_user_{recipient_id}"
                unread_count = Notification.objects.filter(
                    recipient_id=recipient_id, read=False
                ).count()
                new_notif_data = {
                    "id": notif.pk,
                    "message": notif.message,
                    "ticket_number": ticket.ticket_number,
                    "ticket_pk": str(ticket.pk),
                    "created_at": notif.created_at.isoformat(),
                }
                async_to_sync(channel_layer.group_send)(
                    user_group,
                    {
                        "type": "notification_update",
                        "unread_count": unread_count,
                        "new_notification": new_notif_data,
                    },
                )
        except Exception:
            logger.exception("Could not send real‑time bell update.")
    return notif