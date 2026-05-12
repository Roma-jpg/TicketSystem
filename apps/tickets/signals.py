from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Ticket, TicketHistory
from .realtime import broadcast_ticket_event


@receiver(pre_save, sender=Ticket)
def cache_old_status(sender, instance, **kwargs):
    if instance.pk:
        instance._old_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    else:
        instance._old_status = None


@receiver(post_save, sender=Ticket)
def create_history(sender, instance, created, **kwargs):
    old_status = getattr(instance, "_old_status", None)

    if created:
        TicketHistory.objects.create(
            ticket=instance,
            old_status="",
            new_status=instance.status,
            changed_by=instance.created_by,
            note="Заявка создана",
        )
        transaction.on_commit(
            lambda: broadcast_ticket_event(instance, event_name="created", message="Новая заявка создана")
        )
        return

    if old_status != instance.status:
        TicketHistory.objects.create(
            ticket=instance,
            old_status=old_status or "",
            new_status=instance.status,
            changed_by=None,
            note=f"Статус изменён с {old_status or 'unknown'} на {instance.status}",
        )
        transaction.on_commit(
            lambda: broadcast_ticket_event(instance, event_name="status_changed", message="Статус заявки изменён")
        )