# apps/tickets/signals.py
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import escape

from apps.common.middleware import get_current_user
from apps.notifications.models import Notification
from apps.notifications.utils import create_notification
from apps.notifications.tasks import send_status_change_email

from .models import Ticket, TicketComment, TicketHistory
from .realtime import broadcast_ticket_event


# ---------- Ticket status change ----------
@receiver(pre_save, sender=Ticket)
def cache_old_status(sender, instance, **kwargs):
    """
    Store the current (old) status on the instance so that
    post_save can compare and detect changes.
    """
    if instance.pk:
        instance._old_status = instance.status   # store old status directly
    else:
        instance._old_status = None


@receiver(post_save, sender=Ticket)
def handle_ticket_save(sender, instance, created, **kwargs):
    """
    When a ticket's status changes:
      - Record history with the user who made the change.
      - Notify relevant users (creator, assignee, commenters).
      - Set or clear resolved_at / closed_at timestamps automatically.
    """
    if created:
        return  # creation is handled in the view

    # Prevent recursion when we update timestamps below
    if getattr(instance, "_updating_timestamps", False):
        return

    old_status = getattr(instance, "_old_status", None)
    if old_status and old_status != instance.status:
        # Record history with the actual user (may be None for automated changes)
        TicketHistory.objects.create(
            ticket=instance,
            old_status=old_status,
            new_status=instance.status,
            changed_by=get_current_user(),
            note=f"Статус изменён с {old_status} на {instance.status}",
        )

        # Gather recipients: creator + assignee + all commenters
        recipient_ids = set()
        # Commenters
        commenter_ids = instance.comments.values_list("author_id", flat=True).distinct()
        recipient_ids.update(commenter_ids)
        # Creator (might be None for guest tickets)
        if instance.created_by_id:
            recipient_ids.add(instance.created_by_id)
        # Assignee
        if instance.assigned_to_id:
            recipient_ids.add(instance.assigned_to_id)
        # Remove None (just in case)
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

    # ---- Set resolved_at / closed_at timestamps (Bug #7) ----
    now = timezone.now()
    update_fields = []
    if instance.status == Ticket.Status.RESOLVED and not instance.resolved_at:
        instance.resolved_at = now
        update_fields.append("resolved_at")
    elif instance.status == Ticket.Status.CLOSED and not instance.closed_at:
        instance.closed_at = now
        update_fields.append("closed_at")

    # Clear timestamps if status moves back from resolved/closed
    if instance.status in (Ticket.Status.REOPENED, Ticket.Status.OPEN) and (
        instance.resolved_at or instance.closed_at
    ):
        if instance.resolved_at:
            instance.resolved_at = None
            update_fields.append("resolved_at")
        if instance.closed_at:
            instance.closed_at = None
            update_fields.append("closed_at")

    if update_fields:
        instance._updating_timestamps = True
        instance.save(update_fields=update_fields)


# ---------- Ticket comment created ----------
@receiver(post_save, sender=TicketComment)
def handle_comment_created(sender, instance, created, **kwargs):
    """
    When a comment is added:
      - Notify the ticket creator and assignee (unless they are the author).
      - Broadcast the new comment HTML to the ticket's WebSocket group.
    """
    if not created:
        return

    ticket = instance.ticket

    # Recipients: ticket creator + assigned IT, excluding the comment author
    recipient_ids = set()
    if ticket.created_by_id:
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
    internal_badge = (
        ' <span style="color:var(--warn);">Внутренний</span>'
        if instance.internal
        else ""
    )
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
            data={
                "comment_id": instance.id,
                "author": instance.author.username,
                "comment": instance.comment,
                "created_at": instance.created_at.isoformat(),
                "internal": instance.internal,
            }
        )
    )