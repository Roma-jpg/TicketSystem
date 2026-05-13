# apps/tickets/signals.py
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.utils import create_notification
from apps.notifications.tasks import send_status_change_email

from .models import Ticket, TicketComment, TicketHistory
from .realtime import broadcast_ticket_event


# ---------- Ticket status change ----------
@receiver(pre_save, sender=Ticket)
def cache_old_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = sender.objects.filter(pk=instance.pk).values_list(
            "status", flat=True
        ).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Ticket)
def handle_ticket_save(sender, instance, created, **kwargs):
    if created:
        return  # creation is handled in the view

    old_status = getattr(instance, "_old_status", None)
    if old_status and old_status != instance.status:
        # Record history
        TicketHistory.objects.create(
            ticket=instance,
            old_status=old_status,
            new_status=instance.status,
            changed_by=None,
            note=f"Статус изменён с {old_status} на {instance.status}",
        )

        # Gather all recipients: creator + assigned + all commenters
        commenter_ids = instance.comments.values_list("author_id", flat=True).distinct()
        recipient_ids = set(commenter_ids)
        recipient_ids.add(instance.created_by_id)
        if instance.assigned_to_id:
            recipient_ids.add(instance.assigned_to_id)
        recipient_ids.discard(None)

        # Create in‑app notifications
        for uid in recipient_ids:
            create_notification(
                recipient_id=uid,
                ticket=instance,
                notif_type=Notification.Type.STATUS_CHANGE,
                message=f"Статус заявки {instance.ticket_number} изменён: {old_status} → {instance.status}",
            )

        # Send email to all recipients (async)
        transaction.on_commit(
            lambda: send_status_change_email.delay(
                recipient_ids=list(recipient_ids),
                ticket_number=instance.ticket_number,
                old_status=old_status,
                new_status=instance.status,
            )
        )

        # Broadcast real‑time update to the ticket's WebSocket group
        transaction.on_commit(
            lambda: broadcast_ticket_event(
                instance,
                event_name="status_changed",
                data={"old_status": old_status, "new_status": instance.status},
            )
        )


# ---------- Ticket comment created ----------
@receiver(post_save, sender=TicketComment)
def handle_comment_created(sender, instance, created, **kwargs):
    if not created:
        return

    ticket = instance.ticket

    # Recipients: ticket creator + assigned IT, excluding the comment author
    recipient_ids = set()
    recipient_ids.add(ticket.created_by_id)
    if ticket.assigned_to_id:
        recipient_ids.add(ticket.assigned_to_id)
    recipient_ids.discard(instance.author_id)

    for uid in recipient_ids:
        # Build a meaningful message
        if ticket.created_by_id == uid and instance.author_id != ticket.created_by_id:
            msg = f"Новый комментарий к заявке {ticket.ticket_number} от {instance.author.username}"
        else:
            msg = f"Новый комментарий к заявке {ticket.ticket_number}"
        create_notification(
            recipient_id=uid,
            ticket=ticket,
            notif_type=Notification.Type.COMMENT,
            message=msg,
            triggered_by=instance.author,
        )

    # Build HTML snippet for the new comment so the ticket page can append it instantly
    from django.utils.html import escape
    internal_badge = ' <span style="color:var(--warn);">Внутренний</span>' if instance.internal else ''
    comment_html = (
        f'<div class="comment-item" id="comment-{instance.id}">'
        f'<div class="comment-meta"><strong>{escape(instance.author.username)}</strong>'
        f' <span>{instance.created_at.strftime("%d.%m.%Y %H:%M")}</span>'
        f'{internal_badge}'
        f'</div>'
        f'<div class="comment-body">{escape(instance.comment)}</div>'
        f'</div>'
    )
    transaction.on_commit(
        lambda: broadcast_ticket_event(
            ticket,
            event_name="comment_added",
            data={"html": comment_html, "comment_id": instance.id},
        )
    )