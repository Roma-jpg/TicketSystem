# apps/tickets/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Ticket

OVERDUE_HOURS = 48  # SLA

@shared_task
def mark_overdue_tickets():
    """Find open tickets older than OVERDUE_HOURS and set is_overdue=True."""
    cutoff = timezone.now() - timedelta(hours=OVERDUE_HOURS)
    open_statuses = [
        'open', 'acknowledged', 'assigned', 'in_progress',
        'waiting_parts', 'waiting_user', 'reopened'
    ]
    updated = Ticket.objects.filter(
        status__in=open_statuses,
        is_overdue=False,
        created_at__lte=cutoff
    ).update(is_overdue=True)
    return f"Marked {updated} tickets as overdue."