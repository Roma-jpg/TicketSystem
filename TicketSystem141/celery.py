import os
from celery import Celery
from datetime import timedelta

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "TicketSystem141.settings"
)

app = Celery("TicketSystem141")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.autodiscover_tasks()

# Beat schedule must come AFTER app is created
app.conf.beat_schedule = {
    'mark-overdue-every-48-hours': {
        'task': 'apps.tickets.tasks.mark_overdue_tickets',
        'schedule': timedelta(hours=48),
    },
}
